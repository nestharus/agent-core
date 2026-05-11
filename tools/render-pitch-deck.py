#!/usr/bin/env python3
"""Render pitch deck markdown to styled PDF via WeasyPrint."""

import argparse
import sys
from pathlib import Path

import markdown
from weasyprint import HTML

CSS = """
@page {
    size: letter;
    margin: 1in 1.2in;

    @bottom-center {
        content: counter(page);
        font-size: 10px;
        color: #888;
        font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    }
}

body {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    font-size: 13px;
    line-height: 1.6;
    color: #1a1a2e;
}

h1 {
    font-size: 32px;
    font-weight: 700;
    color: #16213e;
    margin-top: 2.5in;
    margin-bottom: 0.3em;
    text-align: center;
    page-break-before: avoid;
}

h1 + p {
    text-align: center;
    font-size: 16px;
    color: #555;
    font-style: italic;
}

h2 {
    font-size: 22px;
    font-weight: 600;
    color: #16213e;
    border-bottom: 2px solid #0f3460;
    padding-bottom: 6px;
    margin-top: 1.5em;
    page-break-before: always;
}

/* Don't page-break before the first h2 after h1 */
h1 ~ h2:first-of-type {
    page-break-before: always;
}

h3 {
    font-size: 16px;
    font-weight: 600;
    color: #0f3460;
    margin-top: 1.2em;
}

hr {
    border: none;
    page-break-after: always;
    margin: 0;
    padding: 0;
    height: 0;
}

p {
    margin-bottom: 0.8em;
}

ul, ol {
    margin-bottom: 0.8em;
    padding-left: 1.5em;
}

li {
    margin-bottom: 0.3em;
}

blockquote {
    background: #f0f4ff;
    border-left: 4px solid #0f3460;
    padding: 12px 16px;
    margin: 1em 0;
    font-style: italic;
    color: #333;
}

blockquote p {
    margin-bottom: 0.4em;
}

strong {
    color: #16213e;
}

em {
    color: #555;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
    font-size: 12px;
}

th {
    background: #16213e;
    color: white;
    padding: 8px 12px;
    text-align: left;
    font-weight: 600;
}

td {
    padding: 6px 12px;
    border-bottom: 1px solid #e0e0e0;
}

tr:nth-child(even) td {
    background: #f8f9fa;
}

code {
    background: #f0f0f0;
    padding: 2px 5px;
    border-radius: 3px;
    font-size: 12px;
}
"""


def render(md_path: Path, pdf_path: Path) -> None:
    md_text = md_path.read_text(encoding="utf-8")

    html_body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "smarty"],
    )

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><style>{CSS}</style></head>
<body>{html_body}</body>
</html>"""

    HTML(string=full_html).write_pdf(str(pdf_path))
    print(f"Rendered: {pdf_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Render pitch deck markdown to PDF")
    parser.add_argument(
        "input",
        nargs="?",
        default="product-strategy/pitch deck.md",
        help="Input markdown file (default: product-strategy/pitch deck.md)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output PDF path (default: same name with .pdf extension)",
    )
    args = parser.parse_args()

    md_path = Path(args.input)
    if not md_path.exists():
        print(f"Error: {md_path} not found", file=sys.stderr)
        sys.exit(1)

    pdf_path = Path(args.output) if args.output else md_path.with_suffix(".pdf")
    render(md_path, pdf_path)


if __name__ == "__main__":
    main()
