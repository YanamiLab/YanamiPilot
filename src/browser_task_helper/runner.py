import asyncio
import time
from urllib.parse import urlsplit

from filelock import FileLock
from playwright.async_api import async_playwright

from .adapters import zhihuishu as adapter
from .runtime import Recovery, Reporter, write_json
from .verification import VerificationBridge


async def run(config):
    config.validate()
    state = config.state_dir
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    with FileLock(str(state / "runner.lock"), timeout=0):
        (state / "stop").unlink(missing_ok=True)
        report = Reporter(state)
        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                str(state / "profile"), executable_path=config.executable_path,
                headless=config.headless, viewport={"width": 1440, "height": 1000},
                args=["--autoplay-policy=no-user-gesture-required", "--restore-last-session"])
            page = context.pages[0] if context.pages else await context.new_page()
            page.set_default_timeout(5000)
            page.set_default_navigation_timeout(30000)
            recovery = Recovery(config.load_timeout, config.max_reloads)
            bridge = VerificationBridge(state, report, config.ocr_python)
            current, last_time = None, None
            last_motion = time.monotonic()
            failures = 0
            catalog = {}

            async def recover(reason):
                nonlocal current, last_time, last_motion
                result = await recovery.check(page, state / "recovery.png")
                if result == "failed":
                    report("error", reason=reason, attempts=recovery.attempts)
                    return False
                if result == "reloaded":
                    current, last_time = None, None
                    last_motion = time.monotonic()
                    report("recovering", reason=reason, attempt=recovery.attempts)
                return True

            try:
                await page.goto(config.url, wait_until="domcontentloaded")
                while not (state / "stop").exists():
                    try:
                        for other in list(context.pages):
                            if other != page and other.url == config.url:
                                await other.locator("video").evaluate_all("es=>es.forEach(e=>e.pause())")
                                await other.close()
                        if await adapter.visible_captcha(page):
                            recovery.ready()
                            await page.locator("video").evaluate_all("es=>es.forEach(e=>e.pause())")
                            await bridge.handle(page, current)
                            last_motion = time.monotonic()
                            await asyncio.sleep(config.poll_seconds)
                            continue
                        await bridge.cleared(page)
                        rows = page.locator(".item-box").filter(has=page.locator(".item-num"))
                        if not await rows.count():
                            is_login = "login" in (urlsplit(page.url).hostname or "").lower()
                            report("login_required" if is_login else "loading")
                            if is_login:
                                recovery.ready()
                            elif not await recover("catalog_loading"):
                                break
                            await asyncio.sleep(config.poll_seconds)
                            continue
                        dialog = page.locator(".ai-class-exercise-dialog:visible")
                        if await dialog.count():
                            if config.exercise_action == "first_option":
                                await adapter.exercise(page)
                                report("exercise_handled", lesson=current)
                            elif config.exercise_action == "close":
                                await dialog.locator(".header-icon").click()
                                report("exercise_closed", lesson=current)
                            else:
                                await page.locator("video").evaluate_all("es=>es.forEach(e=>e.pause())")
                                report("exercise_required", lesson=current)
                            last_motion = time.monotonic()
                            await asyncio.sleep(config.poll_seconds)
                            continue
                        if current is None:
                            observed, pending = [], []
                            for row in await rows.all():
                                number = (await row.locator(".item-num").text_content()).strip()
                                finished = bool(await row.locator(".finish-icon").count())
                                observed.append(dict(lesson=number, completed=finished))
                                if not finished:
                                    pending.append(row)
                            total = len(observed)
                            if total != config.expected_videos or len({v["lesson"] for v in observed}) != total:
                                report("catalog_incomplete", observed=total, expected=config.expected_videos)
                                if not await recover("catalog_count_mismatch"):
                                    break
                                await asyncio.sleep(config.poll_seconds)
                                continue
                            catalog = dict(completed=sum(v["completed"] for v in observed), total=total)
                            write_json(state / "catalog.json", dict(checked_at=time.time(), videos=observed))
                            if not pending:
                                report("completed", confirmed=total)
                                await page.screenshot(path=str(state / "completed.png"))
                                break
                            current = await adapter.select_lesson(page, pending[0])
                            last_time = None
                            last_motion = time.monotonic()
                            await asyncio.sleep(config.poll_seconds)
                            continue
                        video = page.locator("video").first
                        if not await video.count():
                            report("player_loading", lesson=current)
                            if not await recover("player_loading"):
                                break
                            await asyncio.sleep(config.poll_seconds)
                            continue
                        media = await video.evaluate("e=>({time:e.currentTime,duration:e.duration,ended:e.ended,paused:e.paused,error:e.error?.code})")
                        if media["ended"]:
                            await page.reload(wait_until="domcontentloaded")
                            current, last_time = None, None
                            await asyncio.sleep(config.poll_seconds)
                            continue
                        if last_time is not None and media["time"] > last_time:
                            last_motion = time.monotonic()
                            recovery.progressed()
                        last_time = media["time"]
                        if time.monotonic() - last_motion > config.stall_timeout:
                            report("stalled", lesson=current, media=media)
                            # Stall threshold already elapsed; recovery should act now.
                            if recovery.since is None:
                                recovery.since = time.monotonic() - recovery.timeout
                            if not await recover("media_not_advancing"):
                                break
                            await asyncio.sleep(config.poll_seconds)
                            continue
                        rate = await adapter.ensure_rate(page, video, config.speed)
                        playing = await video.evaluate("e=>{e.muted=true;return e.play().then(()=>true).catch(()=>false)}")
                        media = await video.evaluate("e=>({time:e.currentTime,duration:e.duration,ended:e.ended,paused:e.paused,error:e.error?.code})")
                        await bridge.check_resumed(page, current, media)
                        report("playing" if playing and not media["paused"] else "player_waiting",
                               lesson=current, speed=rate["actual"], speed_label=rate["label"],
                               media=media, catalog=catalog)
                        failures = 0
                    except Exception as exc:
                        failures += 1
                        # Avoid serializing Playwright errors containing private URLs.
                        report("error" if failures >= 3 else "retrying", error_type=type(exc).__name__)
                        if failures >= 3:
                            await page.screenshot(path=str(state / "error.png"))
                            break
                        current = None
                    await asyncio.sleep(config.poll_seconds)
                if (state / "stop").exists():
                    report("stopped")
            except Exception as exc:
                report("error", error_type=type(exc).__name__)
                raise
            finally:
                await context.close()
            return 1 if report.latest and report.latest["status"] == "error" else 0
