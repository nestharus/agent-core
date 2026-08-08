"""Focused regression tests for production-writer scope detection."""

from __future__ import annotations

import check_writer_links


def test_anti_scope_adapter_reference_is_allowed() -> None:
    document = {
        "text": "## Do Not Use When\n\nDo not use prototype-validation-evidence-bundle-adapter.md here.\n",
        "sections": {
            "Do Not Use When": "\nDo not use prototype-validation-evidence-bundle-adapter.md here.\n",
        },
    }

    assert not check_writer_links._has_active_adapter_reference(document)


def test_active_adapter_reference_is_rejected() -> None:
    document = {
        "text": "Use prototype-validation-evidence-bundle-adapter.md for this handoff.\n",
        "sections": {},
    }

    assert check_writer_links._has_active_adapter_reference(document)
