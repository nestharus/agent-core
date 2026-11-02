"""Reject native runtime stores before maintenance touches filesystem metadata."""

import os
from pathlib import Path


def reject_native_path(path):
    # Normalize lexically; resolving a symlink would itself enter its target.
    path = Path(os.path.abspath(path))
    home = Path.home()
    for prefix in (home / ".local/state/agent-bash",
                   home / ".local/share/oulipoly-agent-runner"):
        if path == prefix or prefix in path.parents:
            raise RuntimeError("protected native store is outside session maintenance")
