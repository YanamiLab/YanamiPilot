import json
import math
import os
import time
import uuid
from pathlib import Path


def clean(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: clean(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(item) for item in value]
    return value


def write_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            os.chmod(temporary, 0o600)
            json.dump(clean(value), stream, ensure_ascii=False, indent=2, allow_nan=False)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


class Reporter:
    def __init__(self, directory):
        self.directory = directory
        self.event = None
        self.since = time.time()
        self.latest = None

    def __call__(self, kind, **extra):
        now = time.time()
        event = (kind, extra.get("lesson"), extra.get("stage"))
        changed = event != self.event
        if changed:
            self.since = now
        self.latest = clean(dict(status=kind, time=now, state_since=self.since, **extra))
        write_json(self.directory / "status.json", self.latest)
        if changed:
            line = json.dumps(self.latest, ensure_ascii=False, allow_nan=False)
            with (self.directory / "events.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(line + "\n")
            print(line, flush=True)
        self.event = event


class Recovery:
    """Bounded retries reset only after actual media progress."""
    def __init__(self, timeout, limit):
        self.timeout, self.limit = timeout, limit
        self.since = None
        self.attempts = 0

    def ready(self):
        self.since = None

    def progressed(self):
        self.ready()
        self.attempts = 0

    async def check(self, page, screenshot, now=None):
        now = time.monotonic() if now is None else now
        if self.since is None:
            self.since = now
        if now - self.since < self.timeout:
            return "waiting"
        await page.screenshot(path=str(screenshot))
        if self.attempts >= self.limit:
            return "failed"
        self.attempts += 1
        self.since = now
        await page.reload(wait_until="domcontentloaded")
        return "reloaded"
