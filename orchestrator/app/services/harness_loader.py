from pathlib import Path

from ..config import settings


def active_harness_path() -> Path:
    return settings.harness_dir
