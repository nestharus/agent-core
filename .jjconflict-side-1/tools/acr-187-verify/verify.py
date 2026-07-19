#!/usr/bin/env python3
"""Static verifier for ACR-187 PR writer plain-terms anchors.

This module installs check_<anchor_name> functions from anchors.json at import
time so tests can call the same checks that the CLI runs.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable


SPEC_PATH = Path(__file__).resolve().parent / "anchors.json"
REPO_ROOT = Path(__file__).resolve().parents[2]


class CheckFailed(AssertionError):
    """Raised when a verifier check finds a missing prompt anchor."""


def _read_text_unchecked(path: Path) -> str:
    """accessor"""

    return path.read_text(encoding="utf-8")


def _read_spec_text(path: Path) -> str:
    """accessor"""

    return _read_text_unchecked(path)


def _parse_json_text(text: str) -> object:
    """parser"""

    return json.loads(text)


def _require_dict_root(value: object, context: str) -> dict[str, Any]:
    """validator"""

    if not isinstance(value, dict):
        raise CheckFailed(f"{context} must be an object")
    return value


def _load_spec(path: Path) -> dict[str, Any]:
    """orchestration"""

    _require_path_exists(path)
    return _require_dict_root(_parse_json_text(_read_spec_text(path)), "anchor spec root")


def _require_path_exists(path: Path) -> None:
    """validator"""

    if not path.exists():
        raise CheckFailed(f"missing required file: {path}")


def _get_operator_path_raw(spec: dict[str, Any]) -> object:
    """accessor"""

    return spec.get("operator_path", "agents/pr-writer.md")


def _require_string(value: object, field: str) -> str:
    """validator"""

    if not isinstance(value, str):
        raise CheckFailed(field)
    return value


def _get_regions_raw(spec: dict[str, Any]) -> object:
    """accessor"""

    return spec.get("regions")


def _require_dict(value: object, field: str) -> dict[str, Any]:
    """validator"""

    if not isinstance(value, dict):
        raise CheckFailed(field)
    return value


def _get_checks_raw(spec: dict[str, Any]) -> object:
    """accessor"""

    return spec.get("checks")


def _require_list(value: object, field: str) -> list[object]:
    """validator"""

    if not isinstance(value, list):
        raise CheckFailed(field)
    return value


def _get_region_config_raw(spec: dict[str, Any], name: str) -> object | None:
    """accessor"""

    return _get_regions_raw(spec).get(name)  # type: ignore[attr-defined]


def _require_optional_dict(value: object | None, field: str) -> dict[str, Any] | None:
    """validator"""

    if value is None:
        return None
    return _require_dict(value, field)


def _require_region_config(cfg: dict[str, Any] | None, name: str) -> None:
    """validator"""

    if cfg is None:
        raise CheckFailed(f"missing region config: {name}")


def _get_check_name_raw(entry: dict[str, Any]) -> object:
    """accessor"""

    return entry.get("name")


def _get_check_region_raw(entry: dict[str, Any]) -> object:
    """accessor"""

    return entry.get("region")


def _get_check_operator_raw(entry: dict[str, Any]) -> object:
    """accessor"""

    return entry.get("operator")


def _get_check_entry(
    checks: list[dict[str, Any]], name: str
) -> dict[str, Any] | None:
    """accessor"""

    for entry in checks:
        if _get_check_name_raw(entry) == name:
            return entry
    return None


def _require_check_entry(entry: dict[str, Any] | None, name: str) -> None:
    """validator"""

    if entry is None:
        raise CheckFailed(f"missing check entry: {name}")


def _get_list_raw(entry: dict[str, Any], key: str) -> object:
    """accessor"""

    return entry.get(key, [])


def _require_list_of_strings(values: object, field: str) -> list[str]:
    """validator"""

    if not isinstance(values, list):
        raise CheckFailed(f"{field} must be a list")
    strings: list[str] = []
    for item in values:
        if not isinstance(item, str):
            raise CheckFailed(f"{field} entries must be strings")
        strings.append(item)
    return strings


def _get_field_raw(entry: dict[str, Any], key: str) -> object:
    """accessor"""

    return entry.get(key)


def _get_field_raw_with_default(entry: dict[str, Any], key: str, default: bool) -> object:
    """accessor"""

    return entry.get(key, default)


def _require_bool(value: object, field: str) -> bool:
    """validator"""

    if not isinstance(value, bool):
        raise CheckFailed(field)
    return value


def _find_region_span(
    text: str, start_pattern: str, end_pattern: str
) -> tuple[int, int] | None:
    """parser"""

    start_match = re.search(start_pattern, text, flags=re.MULTILINE)
    if start_match is None:
        return None
    end_match = re.search(end_pattern, text[start_match.end() :], flags=re.MULTILINE)
    if end_match is None:
        return (start_match.start(), len(text))
    return (start_match.start(), start_match.end() + end_match.start())


def _require_region_span(span: tuple[int, int] | None, name: str) -> None:
    """validator"""

    if span is None:
        raise CheckFailed(f"missing region: {name}")


def _slice(text: str, span: tuple[int, int]) -> str:
    """mapper"""

    return text[span[0] : span[1]]


def _region_text(spec: dict[str, Any], operator_text: str, name: str) -> str:
    """orchestration"""

    _require_dict(_get_regions_raw(spec), "regions must be an object")
    cfg = _require_optional_dict(
        _get_region_config_raw(spec, name), f"region config must be an object: {name}"
    )
    _require_region_config(cfg, name)
    assert cfg is not None
    parent_name = _get_field_raw(cfg, "within")
    search_text = operator_text
    if isinstance(parent_name, str):
        search_text = _region_text(spec, operator_text, parent_name)
    start_pattern = _require_string(
        _get_field_raw(cfg, "start_pattern"), f"{name} start_pattern must be a string"
    )
    end_pattern = _require_string(
        _get_field_raw(cfg, "end_pattern"), f"{name} end_pattern must be a string"
    )
    span = _find_region_span(search_text, start_pattern, end_pattern)
    _require_region_span(span, name)
    assert span is not None
    return _slice(search_text, span)


def _case_text(text: str, ci: bool) -> str:
    """formatter"""

    if ci:
        return text.lower()
    return text


def _missing_needles(text: str, needles: list[str], ci: bool) -> list[str]:
    """filter"""

    haystack = _case_text(text, ci)
    missing: list[str] = []
    for needle in needles:
        if _case_text(needle, ci) not in haystack:
            missing.append(needle)
    return missing


def _present_needles(text: str, needles: list[str], ci: bool) -> list[str]:
    """filter"""

    haystack = _case_text(text, ci)
    present: list[str] = []
    for needle in needles:
        if _case_text(needle, ci) in haystack:
            present.append(needle)
    return present


def _check_contains_all(text: str, needles: list[str], ci: bool) -> None:
    """validator"""

    missing = _missing_needles(text, needles, ci)
    if missing:
        raise CheckFailed(f"missing required substrings: {missing}")


def _check_contains_any(text: str, needles: list[str], ci: bool) -> None:
    """validator"""

    if len(_missing_needles(text, needles, ci)) == len(needles):
        raise CheckFailed(f"missing any required substring from: {needles}")


def _check_not_contains_all(
    text: str, forbidden_needles: list[str], forbidden_patterns: list[str], ci: bool
) -> None:
    """validator"""

    present = _present_needles(text, forbidden_needles, ci)
    matched = _matched_patterns(text, forbidden_patterns, ci)
    if present or matched:
        raise CheckFailed(f"forbidden content present: {present + matched}")


def _matched_patterns(text: str, patterns: list[str], ci: bool) -> list[str]:
    """filter"""

    flags = re.MULTILINE | re.DOTALL
    if ci:
        flags |= re.IGNORECASE
    matched: list[str] = []
    for pattern in patterns:
        if re.search(pattern, text, flags=flags) is not None:
            matched.append(pattern)
    return matched


def _check_regex(text: str, pattern: str, ci: bool) -> None:
    """validator"""

    flags = re.MULTILINE | re.DOTALL
    if ci:
        flags |= re.IGNORECASE
    if re.search(pattern, text, flags=flags) is None:
        raise CheckFailed(f"missing regex match: {pattern}")


def _extract_first_h2(text: str) -> str | None:
    """parser"""

    match = re.search(r"^##\s+.+$", text, flags=re.MULTILINE)
    if match is None:
        return None
    return match.group(0)


def _require_h2(h2: str | None, name: str) -> None:
    """validator"""

    if h2 is None:
        raise CheckFailed(f"{name}: missing H2 heading")


def _normalize_h2(h2: str) -> str:
    """formatter"""

    return " ".join(h2.strip().split())


def _extract_first_fenced_block(text: str) -> str | None:
    """parser"""

    match = re.search(r"```(?:[A-Za-z0-9_-]+)?\s*\n([\s\S]*?)\n```", text)
    if match is None:
        return None
    return match.group(1)


def _require_fenced_block(block: str | None, name: str) -> None:
    """validator"""

    if block is None:
        raise CheckFailed(f"{name}: missing fenced block")


def _check_heading_equals(h2: str, heading: str) -> None:
    """validator"""

    if _normalize_h2(h2) != _normalize_h2(heading):
        raise CheckFailed(f"first H2 is {_normalize_h2(h2)!r}, expected {heading!r}")


def _format_pass(name: str) -> str:
    """formatter"""

    return f"PASS {name}"


def _format_fail(name: str, msg: str) -> str:
    """formatter"""

    return f"FAIL {name}: {msg}"


def _dispatch_check(spec_entry: dict[str, Any], region_text: str) -> None:
    """orchestration"""

    name = _require_string(_get_check_name_raw(spec_entry), "check entry missing string name")
    operator = _require_string(
        _get_check_operator_raw(spec_entry), f"{name} missing string operator"
    )
    ci = _require_bool(
        _get_field_raw_with_default(spec_entry, "case_insensitive", True),
        f"{name} case_insensitive must be a boolean",
    )
    if operator == "contains_all":
        _check_contains_all(
            region_text,
            _require_list_of_strings(_get_list_raw(spec_entry, "needles"), f"{name} needles"),
            ci,
        )
        return
    if operator == "contains_any":
        _check_contains_any(
            region_text,
            _require_list_of_strings(_get_list_raw(spec_entry, "needles"), f"{name} needles"),
            ci,
        )
        return
    if operator == "not_contains_all":
        _check_not_contains_all(
            region_text,
            _require_list_of_strings(
                _get_list_raw(spec_entry, "forbidden_needles"),
                f"{name} forbidden_needles",
            ),
            _require_list_of_strings(
                _get_list_raw(spec_entry, "forbidden_patterns"),
                f"{name} forbidden_patterns",
            ),
            ci,
        )
        return
    if operator == "regex":
        _check_regex(
            region_text,
            _require_string(
                _get_field_raw(spec_entry, "pattern"), f"{name} pattern must be a string"
            ),
            ci,
        )
        return
    if operator == "first_fenced_block_starts_with":
        block = _extract_first_fenced_block(region_text)
        _require_fenced_block(block, name)
        assert block is not None
        h2 = _extract_first_h2(block)
        _require_h2(h2, name)
        assert h2 is not None
        _check_heading_equals(
            h2,
            _require_string(
                _get_field_raw(spec_entry, "heading"), f"{name} heading must be a string"
            ),
        )
        return
    raise CheckFailed(f"unknown operator: {operator}")


def _run_named_check(spec: dict[str, Any], operator_text: str, name: str) -> None:
    """orchestration"""

    checks: list[dict[str, Any]] = []
    for value in _require_list(_get_checks_raw(spec), "checks must be a list"):
        checks.append(_require_dict(value, "each check must be an object"))
    entry = _get_check_entry(checks, name)
    _require_check_entry(entry, name)
    assert entry is not None
    entry_name = _require_string(_get_check_name_raw(entry), "check entry missing string name")
    region_name = _require_string(
        _get_check_region_raw(entry), f"{entry_name} missing string region"
    )
    region = _region_text(spec, operator_text, region_name)
    _dispatch_check(entry, region)


def _run_all_checks(spec: dict[str, Any], text: str) -> bool:
    """orchestration"""

    failed = False
    for value in _require_list(_get_checks_raw(spec), "checks must be a list"):
        entry = _require_dict(value, "each check must be an object")
        name = _require_string(_get_check_name_raw(entry), "check entry missing string name")
        try:
            _run_named_check(spec, text, name)
        except CheckFailed as exc:
            failed = True
            print(_format_fail(name, str(exc)))
        else:
            print(_format_pass(name))
    return not failed


def _parse_argv(argv: list[str]) -> argparse.Namespace:
    """parser"""

    parser = argparse.ArgumentParser()
    parser.add_argument("--operator-path", default=None)
    return parser.parse_args(argv)


def _make_check_function(name: str) -> Callable[[str], None]:
    """mapper"""

    def _check(operator_text: str) -> None:
        """validator"""

        _run_named_check(SPEC, operator_text, name)

    _check.__name__ = f"check_{name}"
    return _check


def _install_check_functions(spec: dict[str, Any]) -> None:
    """orchestration"""

    for value in _require_list(_get_checks_raw(spec), "checks must be a list"):
        entry = _require_dict(value, "each check must be an object")
        name = _require_string(_get_check_name_raw(entry), "check entry missing string name")
        globals()[f"check_{name}"] = _make_check_function(name)


def main(argv: list[str]) -> int:
    """orchestration"""

    spec = _load_spec(SPEC_PATH)
    args = _parse_argv(argv)
    if args.operator_path is None:
        operator_path = REPO_ROOT / _require_string(
            _get_operator_path_raw(spec), "operator_path must be a string"
        )
    else:
        operator_path = Path(args.operator_path)
    _require_path_exists(operator_path)
    text = _read_text_unchecked(operator_path)
    return 0 if _run_all_checks(spec, text) else 1


SPEC = _load_spec(SPEC_PATH)
_install_check_functions(SPEC)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
