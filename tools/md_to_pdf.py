#!/usr/bin/env python3
"""Convert problem-first-ai-engineering.md to a styled PDF."""

import markdown
from weasyprint import HTML
from pathlib import Path

HERE = Path(__file__).parent
MD_FILE = HERE / "problem-first-ai-engineering.md"
PDF_FILE = HERE / "problem-first-ai-engineering.pdf"

CSS = """
@page {
    size: letter;
    margin: 1in 1in 1in 1in;

    @bottom-center {
        content: counter(page);
        font-size: 9pt;
        color: #666;
        font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    }
}

@page :first {
    @bottom-center { content: none; }
}

body {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #1a1a1a;
    max-width: 100%;
}

/* Part headings */
h1 {
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-size: 22pt;
    font-weight: 700;
    color: #111;
    margin-top: 1.5em;
    margin-bottom: 0.5em;
    border-bottom: 2px solid #333;
    padding-bottom: 0.2em;
    page-break-before: always;
    page-break-after: avoid;
}

/* Section headings */
h2 {
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-size: 16pt;
    font-weight: 600;
    color: #222;
    margin-top: 1.8em;
    margin-bottom: 0.5em;
    page-break-after: avoid;
}

/* Subsection headings */
h3 {
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-size: 13pt;
    font-weight: 600;
    color: #333;
    margin-top: 1.4em;
    margin-bottom: 0.4em;
    page-break-after: avoid;
}

h4 {
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-size: 11pt;
    font-weight: 600;
    color: #444;
    margin-top: 1.2em;
    margin-bottom: 0.3em;
    page-break-after: avoid;
}

p {
    margin-bottom: 0.8em;
    text-align: justify;
    orphans: 3;
    widows: 3;
}

/* Blockquotes */
blockquote {
    border-left: 3px solid #666;
    margin: 1em 0;
    padding: 0.5em 1em;
    background: #f7f7f7;
    font-style: italic;
    page-break-inside: avoid;
}

blockquote p {
    margin-bottom: 0.4em;
}

/* Code blocks */
pre {
    background: #f4f4f4;
    border: 1px solid #ddd;
    border-radius: 3px;
    padding: 0.8em 1em;
    font-family: "Courier New", Courier, monospace;
    font-size: 9.5pt;
    line-height: 1.4;
    overflow-wrap: break-word;
    white-space: pre-wrap;
    page-break-inside: avoid;
    margin: 0.8em 0;
}

code {
    font-family: "Courier New", Courier, monospace;
    font-size: 9.5pt;
    background: #f0f0f0;
    padding: 0.1em 0.3em;
    border-radius: 2px;
}

pre code {
    background: none;
    padding: 0;
}

/* Tables */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
    font-size: 10pt;
    page-break-inside: avoid;
}

th {
    background: #f0f0f0;
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-weight: 600;
    text-align: left;
    padding: 0.5em 0.8em;
    border-bottom: 2px solid #999;
}

td {
    padding: 0.4em 0.8em;
    border-bottom: 1px solid #ddd;
    vertical-align: top;
}

tr:last-child td {
    border-bottom: none;
}

/* Lists */
ul, ol {
    margin-bottom: 0.8em;
    padding-left: 1.5em;
}

li {
    margin-bottom: 0.3em;
}

li > ul, li > ol {
    margin-top: 0.2em;
    margin-bottom: 0.2em;
}

/* Horizontal rules */
hr {
    border: none;
    border-top: 1px solid #ccc;
    margin: 2em 0;
}

/* Bold and emphasis */
strong {
    font-weight: 700;
}

em {
    font-style: italic;
}

/* Links - style for print */
a {
    color: #1a1a1a;
    text-decoration: none;
}

/* Table of contents */
h2#contents, h3:has(+ ol), h3:has(+ ul) {
    page-break-after: avoid;
}

/* Keep numbered items with their content */
li > p {
    margin-bottom: 0.3em;
}

/* Avoid page breaks in the middle of important blocks */
h2 + p, h3 + p, h2 + blockquote, h3 + blockquote {
    page-break-before: avoid;
}

/* Term definition boxes — university textbook style */
.term-box {
    background: #f8f6f0;
    border: 1.5px solid #c4b99a;
    border-radius: 6px;
    padding: 1em 1.2em 0.8em 1.2em;
    margin: 1.2em 0;
    page-break-inside: avoid;
}

.term-box .term-header {
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-size: 11pt;
    font-weight: 700;
    color: #5a4e3a;
    margin-bottom: 0.5em;
    padding-bottom: 0.3em;
    border-bottom: 1px solid #d4c9a8;
    display: flex;
    align-items: center;
    gap: 0.5em;
}

.term-box .term-header svg {
    flex-shrink: 0;
}

.term-box p {
    font-size: 10pt;
    line-height: 1.5;
    color: #3a3427;
    margin-bottom: 0.5em;
    text-align: left;
}

.term-box p:last-child {
    margin-bottom: 0;
}

.term-box .term-history {
    font-size: 9pt;
    font-style: italic;
    color: #7a6e5a;
    margin-top: 0.4em;
}

/* Tangent/history boxes — sidebar explorations */
.tangent-box {
    background: #f2f5f0;
    border: 1.5px solid #a8b89a;
    border-left: 4px solid #7a9a6a;
    border-radius: 6px;
    padding: 1em 1.2em 0.8em 1.2em;
    margin: 1.2em 0;
    page-break-inside: avoid;
}

.tangent-box .tangent-header {
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-size: 11pt;
    font-weight: 700;
    color: #4a5e3a;
    margin-bottom: 0.5em;
    padding-bottom: 0.3em;
    border-bottom: 1px solid #b8c8a8;
    display: flex;
    align-items: center;
    gap: 0.5em;
}

.tangent-box .tangent-header svg {
    flex-shrink: 0;
}

.tangent-box p {
    font-size: 10pt;
    line-height: 1.5;
    color: #3a4227;
    margin-bottom: 0.5em;
    text-align: left;
}

.tangent-box p:last-child {
    margin-bottom: 0;
}

/* Figure containers — subtle frame for diagrams */
.figure-box {
    border: 1px solid #ddd;
    border-radius: 6px;
    padding: 1.2em 1em 0.6em 1em;
    margin: 1.5em 0;
    background: #fafafa;
    text-align: center;
    page-break-inside: avoid;
}

.figure-box img,
.figure-box svg {
    max-width: 100%;
    display: inline-block;
}

.figure-box .fig-caption {
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-size: 8.5pt;
    color: #666;
    margin-top: 0.6em;
    font-style: italic;
    text-align: center;
}

/* Principle callout — for key insights and rules */
.principle-box {
    background: #f0f3f7;
    border-left: 4px solid #2c3e50;
    border-radius: 0 6px 6px 0;
    padding: 0.8em 1.2em;
    margin: 1.2em 0;
    page-break-inside: avoid;
}

.principle-box .principle-label {
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-size: 9pt;
    font-weight: 700;
    color: #2c3e50;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.3em;
}

.principle-box p {
    font-size: 10.5pt;
    line-height: 1.5;
    color: #1a1a1a;
    margin-bottom: 0.4em;
    text-align: left;
}

.principle-box p:last-child {
    margin-bottom: 0;
}

/* Warning/caution box — for anti-patterns and failure modes */
.warning-box {
    background: #fdf8f0;
    border-left: 4px solid #c0392b;
    border-radius: 0 6px 6px 0;
    padding: 0.8em 1.2em;
    margin: 1.2em 0;
    page-break-inside: avoid;
}

.warning-box .warning-label {
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-size: 9pt;
    font-weight: 700;
    color: #c0392b;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.3em;
}

.warning-box p {
    font-size: 10.5pt;
    line-height: 1.5;
    color: #3a2a1a;
    margin-bottom: 0.4em;
    text-align: left;
}

.warning-box p:last-child {
    margin-bottom: 0;
}
"""


def convert():
    md_text = MD_FILE.read_text(encoding="utf-8")

    html_body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "smarty", "toc", "md_in_html"],
        extension_configs={
            "smarty": {"smart_quotes": True, "smart_dashes": True},
        },
    )

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <style>{CSS}</style>
</head>
<body>
{html_body}
</body>
</html>"""

    HTML(string=html_doc, base_url=str(Path(__file__).parent)).write_pdf(str(PDF_FILE))
    print(f"Written: {PDF_FILE}")
    print(f"Size: {PDF_FILE.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    convert()
