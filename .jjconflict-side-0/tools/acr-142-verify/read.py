"""File accessors for the ACR-142 structural verifier."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable


def read_files(paths: Iterable[str]) -> dict[str, str]:
    """Return text for the requested files that exist."""

    loaded: dict[str, str] = {}
    for path in paths:
        file_path = Path(path)
        if file_path.exists():
            loaded[path] = file_path.read_text(encoding="utf-8")
    return loaded
