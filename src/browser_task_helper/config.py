"""Portable configuration. No account or course identifiers are bundled."""
import math
import tomllib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Config:
    url: str
    expected_videos: int
    state_dir: Path
    speed: float = 1.5
    headless: bool = False
    executable_path: str | None = None
    ocr_python: str | None = None
    exercise_action: str = "close"
    poll_seconds: float = 2
    load_timeout: float = 90
    stall_timeout: float = 120
    max_reloads: int = 3

    @classmethod
    def load(cls, path):
        path = Path(path).resolve()
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        base = path.parent
        data["state_dir"] = (base / data.get("state_dir", ".browser-task-helper")).resolve()
        for key in ("executable_path", "ocr_python"):
            if data.get(key):
                data[key] = str((base / Path(data[key]).expanduser()).resolve())
        config = cls(**data)
        config.validate()
        return config

    def validate(self):
        url = urlsplit(self.url)
        if url.username or url.password or not url.hostname:
            raise ValueError("URL must have a hostname and no embedded credentials")
        local = url.hostname in {"127.0.0.1", "localhost", "::1"}
        if url.scheme != "https" and not (url.scheme == "http" and local):
            raise ValueError("Use HTTPS, or HTTP on loopback for the demo")
        if "REPLACE_ME" in self.url:
            raise ValueError("Set your own course URL")
        if type(self.expected_videos) is not int or self.expected_videos < 1:
            raise ValueError("expected_videos must be the actual positive catalog count")
        if self.exercise_action not in {"close", "first_option", "manual"}:
            raise ValueError("Unknown exercise_action")
        if type(self.headless) is not bool:
            raise ValueError("headless must be true or false")
        for key in ("speed", "poll_seconds", "load_timeout", "stall_timeout"):
            value = getattr(self, key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"{key} must be a finite positive number")
        if not 0.5 <= self.speed <= 2:
            raise ValueError("speed must be between 0.5 and 2")
        if type(self.max_reloads) is not int or self.max_reloads < 0:
            raise ValueError("max_reloads must be a nonnegative integer")
