import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from .config import Config
from .runtime import write_json


def main():
    parser = argparse.ArgumentParser(description="YanamiPilot · 续航 — local browser task helper")
    parser.add_argument("--config", default="config.toml")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("run", help="Start one browser session; log in in its own window")
    commands.add_parser("status", help="Show local status and freshness")
    commands.add_parser("stop", help="Request graceful stop")
    approve = commands.add_parser("approve", help="Approve exactly the displayed current challenge")
    approve.add_argument("challenge_id")
    commands.add_parser("demo", help="Run two local sample videos without accounts or remote pages")
    args = parser.parse_args()
    try:
        if args.command == "demo":
            from .demo import main as demo
            return asyncio.run(demo())
        config = Config.load(args.config)
        state = config.state_dir
        if args.command == "run":
            from .runner import run
            return asyncio.run(run(config))
        if args.command == "status":
            result = json.loads((state / "status.json").read_text(encoding="utf-8"))
            result["age_seconds"] = round(time.time() - result["time"], 1)
            result["state_age_seconds"] = round(time.time() - result["state_since"], 1)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.command == "stop":
            if not state.exists():
                raise ValueError("No state directory exists yet")
            (state / "stop").touch()
            print("Stop requested")
        elif args.command == "approve":
            challenge = json.loads((state / "challenge.json").read_text(encoding="utf-8"))
            status = json.loads((state / "status.json").read_text(encoding="utf-8"))
            if status["status"] != "verification_required" or time.time() - status["time"] > 10:
                raise ValueError("No fresh active challenge; check the browser")
            if challenge["id"] != args.challenge_id or challenge.get("attempted"):
                raise ValueError("Challenge changed or already attempted")
            if not config.ocr_python or not challenge["supported"]:
                raise ValueError("This challenge requires manual completion in the browser")
            print("Inspect the current browser and", state / "challenge-screen.png")
            print("Prompt:", challenge["prompt"])
            if input("Approve one local recognition/click attempt? Type yes: ").strip() != "yes":
                print("No approval issued")
                return 1
            latest = json.loads((state / "challenge.json").read_text(encoding="utf-8"))
            if latest["id"] != args.challenge_id:
                raise ValueError("Challenge changed while confirming")
            write_json(state / "approve-verification.json", dict(id=args.challenge_id, approved_at=time.time()))
            print("One-use approval issued; verify the result in status")
        return 0
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print(f"Configuration/state error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
