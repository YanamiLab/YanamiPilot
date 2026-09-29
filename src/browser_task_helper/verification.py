"""Current-challenge handoff with a one-use approval and an optional local provider."""
import asyncio
import hashlib
import json
import math
import re
import time
import uuid
from pathlib import Path

from .runtime import write_json


class VerificationBridge:
    def __init__(self, state, report, ocr_python=None):
        self.state, self.report, self.ocr_python = state, report, ocr_python
        self.current = None
        self.resume = None

    def save(self):
        write_json(self.state / "challenge.json", self.current)

    async def handle(self, page, lesson):
        image = page.get_by_alt_text("验证码背景", exact=True)
        prompt_button = page.get_by_role("button", name=re.compile("请点击"))
        supported = await image.count() == 1 and await image.is_visible() and await prompt_button.count() == 1
        prompt = await prompt_button.inner_text() if supported else "Manual handoff required"
        data = await image.screenshot() if supported else prompt.encode()
        digest = hashlib.sha256(data + prompt.encode()).hexdigest()
        if not self.current or self.current["fingerprint"] != digest:
            await page.screenshot(path=str(self.state / "challenge-screen.png"))
            if supported:
                (self.state / "challenge.png").write_bytes(data)
            self.current = dict(id=uuid.uuid4().hex, fingerprint=digest, prompt=prompt,
                                supported=supported, lesson=lesson, created_at=time.time(),
                                stage="awaiting_confirmation", attempted=False)
            self.save()
        approval = self.state / "approve-verification.json"
        if approval.exists():
            # Consume even malformed or expired grants. No automatic grants or retries.
            try:
                grant = json.loads(approval.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                grant = {}
            finally:
                approval.unlink(missing_ok=True)
            approved_at = grant.get("approved_at")
            valid_time = type(approved_at) in (int, float) and math.isfinite(approved_at) and 0 <= time.time() - approved_at <= 120
            if grant.get("id") != self.current["id"] or not valid_time:
                self.current["stage"] = "approval_expired"
            elif self.current["attempted"]:
                self.current["stage"] = "manual_required"
            elif not supported or not self.ocr_python:
                self.current["stage"] = "manual_required"
            else:
                self.current["attempted"] = True
                try:
                    await self.solve_once(page, image, prompt_button, digest, prompt)
                except (OSError, ValueError, asyncio.TimeoutError, RuntimeError):
                    self.current["stage"] = "provider_error"
        self.save()
        self.report("verification_required", lesson=lesson,
                    challenge_id=self.current["id"], stage=self.current["stage"])

    async def solve_once(self, page, image, prompt_button, digest, prompt):
        output = self.state / "prediction.json"
        output.unlink(missing_ok=True)
        process = await asyncio.create_subprocess_exec(
            self.ocr_python, str(Path(__file__).with_name("ocr.py")),
            str(self.state / "challenge.png"), prompt, str(output),
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        try:
            await asyncio.wait_for(process.wait(), timeout=20)
        finally:
            if process.returncode is None:
                process.kill()
                await process.wait()
        if process.returncode:
            raise RuntimeError("Local provider failed")
        result = json.loads(output.read_text(encoding="utf-8"))
        if result.get("status") != "ready":
            self.current["stage"] = "recognition_uncertain"
            return
        latest_prompt = await prompt_button.inner_text()
        latest_image = await image.screenshot()
        if hashlib.sha256(latest_image + latest_prompt.encode()).hexdigest() != digest:
            self.current["stage"] = "challenge_changed"
            return
        w, h = result["size"]
        x, y = result["point"]
        if not all(type(n) in (float, int) and math.isfinite(n) for n in (w, h, x, y)) or not (w > 0 and h > 0 and 0 <= x < w and 0 <= y < h):
            raise ValueError("Invalid provider coordinates")
        box = await image.bounding_box()
        if not box:
            self.current["stage"] = "challenge_changed"
            return
        await page.mouse.click(box["x"] + x * box["width"] / w, box["y"] + y * box["height"] / h)
        self.current.update(stage="clicked_waiting_for_acceptance", clicked_at=time.time())

    async def cleared(self, page):
        if self.current:
            self.current["stage"] = "dialog_cleared"
            self.save()
            self.resume = dict(lesson=self.current["lesson"], baseline=None,
                               method="model" if "clicked_at" in self.current else "manual")
            self.current = None

    async def check_resumed(self, page, lesson, media):
        if not self.resume:
            return
        # A different video or a seek backwards cannot prove recovery of this video.
        if lesson != self.resume["lesson"]:
            self.resume = None
            return
        if self.resume["baseline"] is None:
            self.resume["baseline"] = media["time"]
            return
        if not media["paused"] and media["time"] > self.resume["baseline"] + 2:
            await page.screenshot(path=str(self.state / "verification-resumed.png"))
            write_json(self.state / "verification-result.json", dict(
                self.resume, status="playback_resumed", media=media, verified_at=time.time()))
            self.report("verification_passed_and_resumed", lesson=lesson, method=self.resume["method"])
            self.resume = None
