"""Parsers for the ACR-142 structural verifier."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass


CHECK_CHOICES = (
    "workflow",
    "operator",
    "child_operators",
    "workflow_links",
    "writer_links",
)


@dataclass(frozen=True)
class ParsedArgs:
    checks: list[str]


@dataclass(frozen=True)
class Heading:
    level: int
    text: str
    line: int


@dataclass(frozen=True)
class Anchor:
    name: str
    columns: list[str]
    line: int


UPLOADER_DISPATCH = "prototype-validation-screenshot-uploader.md"
PACKAGER_DISPATCH = "prototype-validation-packager.md"
RESPONSIBILITY_SECTIONS = ("Role", "Inputs", "Outputs", "Procedure")


def parse_cli_flags(argv: list[str]) -> ParsedArgs:
    parser = argparse.ArgumentParser(
        description="Verify ACR-142 workflow/operator structural anchors."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="run every check")
    group.add_argument("--check", choices=CHECK_CHOICES, help="run one check group")
    args = parser.parse_args(argv)
    if args.all:
        return ParsedArgs(checks=list(CHECK_CHOICES))
    return ParsedArgs(checks=[args.check])


def parse_document(path: str, loaded: dict[str, str]) -> dict[str, object]:
    text = loaded.get(path, "")
    headings = parse_heading_index(text)
    sections = parse_sections(text, headings)
    procedure = sections.get("Procedure", "")
    responsibility_prose = parse_responsibility_prose(text, headings, sections)

    return {
        "path": path,
        "exists": path in loaded,
        "text": text,
        "normalized_text": normalize_text(text, colon_spacing=True),
        "frontmatter": parse_frontmatter(text),
        "headings": headings,
        "sections": sections,
        "phase_labels": parse_phase_labels(text),
        "numbered_phase_labels": parse_numbered_phase_labels(text),
        "anchors": parse_anchor_table(text),
        "procedure": procedure,
        "procedure_phase_blocks": parse_numbered_phase_blocks(procedure),
        "procedure_uploader_dispatch_positions": parse_token_positions(procedure, UPLOADER_DISPATCH),
        "procedure_walkthrough_positions": parse_token_positions(procedure.lower(), "walkthrough"),
        "procedure_packager_proof_bundle_anchor": parse_packager_proof_bundle_anchor(procedure),
        "responsibility_prose": responsibility_prose,
        "normalized_responsibility_prose": normalize_text(responsibility_prose, colon_spacing=True),
    }


def parse_frontmatter(text: str) -> dict | None:
    if not text.startswith("---\n"):
        return None

    lines = text.splitlines()
    end_index: int | None = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_index = index
            break
    if end_index is None:
        return None

    result: dict = {}
    current_key: str | None = None
    for raw_line in lines[1:end_index]:
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()

        if line.startswith("- "):
            if current_key is not None and isinstance(result.get(current_key), list):
                result[current_key].append(_parse_scalar(line[2:].strip()))
            continue

        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if indent == 0:
            current_key = key
            if value:
                result[key] = _parse_scalar(value)
            else:
                result[key] = []
        elif current_key is not None:
            if not isinstance(result.get(current_key), dict):
                result[current_key] = {}
            result[current_key][key] = _parse_scalar(value)

    return result


def parse_heading_index(text: str) -> list[Heading]:
    headings: list[Heading] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if match:
            headings.append(
                Heading(
                    level=len(match.group(1)),
                    text=match.group(2).strip(),
                    line=line_number,
                )
            )
    return headings


def parse_phase_labels(text: str) -> list[str]:
    pattern = re.compile(r"\bPhase\s+(?:2b|4b|8b|0|1|2|3|4|5|6|7|8)\b")
    labels: list[str] = []
    seen: set[str] = set()
    for match in pattern.finditer(text):
        label = match.group(0)
        if label not in seen:
            labels.append(label)
            seen.add(label)
    return labels


def parse_numbered_phase_labels(text: str) -> list[str]:
    pattern = re.compile(r"(?m)^\s*\d+[\.)]\s+.*\b(Phase\s+(?:2b|4b|8b|0|1|2|3|4|5|6|7|8))\b")
    labels: list[str] = []
    seen: set[str] = set()
    for match in pattern.finditer(text):
        label = match.group(1)
        if label not in seen:
            labels.append(label)
            seen.add(label)
    return labels


def parse_anchor_table(text: str) -> list[Anchor]:
    anchors: list[Anchor] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        if re.fullmatch(r"\|[\s:\-|]+\|", stripped):
            continue
        columns = [column.strip() for column in stripped.strip("|").split("|")]
        if not columns:
            continue
        first = columns[0]
        if first.lower() in {"anchor", "anchor id", "contract", "name"}:
            continue
        if first:
            anchors.append(Anchor(name=first, columns=columns, line=line_number))
    return anchors


def parse_sections(text: str, headings: list[Heading]) -> dict[str, str]:
    return {
        heading.text: parse_section_text(text, headings, index)
        for index, heading in enumerate(headings)
    }


def parse_section_text(text: str, headings: list[Heading], index: int) -> str:
    lines = text.splitlines(keepends=True)
    offsets: list[int] = []
    offset = 0
    for line in lines:
        offsets.append(offset)
        offset += len(line)

    heading = headings[index]
    line_index = max(heading.line - 1, 0)
    if line_index >= len(lines):
        return ""

    start = offsets[line_index] + len(lines[line_index])
    end = len(text)
    for next_heading in headings[index + 1:]:
        if next_heading.level <= heading.level:
            next_line_index = max(next_heading.line - 1, 0)
            if next_line_index < len(offsets):
                end = offsets[next_line_index]
            break
    return text[start:end]


def parse_numbered_phase_blocks(text: str) -> dict[str, tuple[int, int]]:
    pattern = re.compile(r"(?m)^\s*\d+[\.)]\s+.*\b(Phase\s+(?:2b|4b|8b|0|1|2|3|4|5|6|7|8))\b.*$")
    matches = list(pattern.finditer(text))
    blocks: dict[str, tuple[int, int]] = {}
    for index, match in enumerate(matches):
        phase = match.group(1)
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        blocks[phase] = (match.start(), end)
    return blocks


def parse_token_positions(text: str, token: str) -> list[int]:
    return [match.start() for match in re.finditer(re.escape(token), text)]


def parse_packager_proof_bundle_anchor(text: str) -> int | None:
    paragraph_pattern = re.compile(r"(?ms)(?:^|\n)([^\n].*?)(?=\n\s*\n|\Z)")
    for match in paragraph_pattern.finditer(text):
        paragraph = match.group(1)
        normalized = normalize_text(paragraph)
        if PACKAGER_DISPATCH not in paragraph:
            continue
        if "proof bundle" not in normalized and "proof_bundle_path" not in paragraph:
            continue
        if not any(token in normalized for token in ("assembl", "build", "create", "produce", "write")):
            continue
        return match.start(1)
    return None


def parse_responsibility_prose(
    text: str,
    headings: list[Heading],
    sections: dict[str, str] | None = None,
) -> str:
    section_map = sections if sections is not None else parse_sections(text, headings)
    parts = [
        section_map[section]
        for section in RESPONSIBILITY_SECTIONS
        if section in section_map
    ]
    return "\n".join(parts) if parts else text


def normalize_text(text: str, colon_spacing: bool = False) -> str:
    replaced = text.replace("_", " ").replace("-", " ")
    if colon_spacing:
        replaced = replaced.replace(":", ": ")
    return re.sub(r"\s+", " ", replaced.lower())


def _parse_scalar(value: str) -> object:
    stripped = value.strip()
    if stripped == "":
        return ""
    if stripped in {"[]", "{}"}:
        return [] if stripped == "[]" else {}
    if stripped.lower() in {"true", "false"}:
        return stripped.lower() == "true"
    return stripped.strip("\"'")
