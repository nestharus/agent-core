from pathlib import Path

import pytest


@pytest.fixture
def repo_root():
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "AGENTS.md").exists():
            return candidate
    raise AssertionError("could not locate repo root containing AGENTS.md")
