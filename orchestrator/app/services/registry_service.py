from pathlib import Path

from ..config import settings


def registry_path(name: str) -> Path:
    return settings.registry_dir / name
