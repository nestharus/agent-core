"""Focused regression tests for Markdown phase-section detection."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify  # noqa: E402


def test_require_phase_ignores_heading_inside_fence() -> None:
    text = """## Example

```markdown
## Phase 6

Step 6b output index with inherited pending production tests.
```
"""

    with pytest.raises(verify.CheckFailed, match="missing Phase 6 section"):
        verify._require_phase(text, 6, "A9")


def test_require_phase_rejects_duplicate_headings() -> None:
    text = """## Phase 6

First section.

## Phase 6

Second section.
"""

    with pytest.raises(verify.CheckFailed, match="duplicate Phase 6 sections"):
        verify._require_phase(text, 6, "A9")
