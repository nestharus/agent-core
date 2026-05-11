#!/usr/bin/env bash
# Visual review loop for SVG diagrams.
#
# Usage:
#   review_svg.sh <svg_file> <description> [max_rounds]
#
# 1. Converts SVG to PNG via cairosvg
# 2. Sends PNG to Gemini for visual review
# 3. If issues found, sends original prompt + feedback to Gemini for regeneration
# 4. Repeats until clean or max_rounds reached
#
# Requires: agents binary, cairosvg (Python), gemini-medium model

set -euo pipefail

SVG_FILE="$1"
DESCRIPTION="$2"
MAX_ROUNDS="${3:-3}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [[ ! -f "$SVG_FILE" ]]; then
    echo "Error: SVG file not found: $SVG_FILE" >&2
    exit 1
fi

PNG_FILE="${SVG_FILE%.svg}.review.png"

for round in $(seq 1 "$MAX_ROUNDS"); do
    echo "=== Visual review round $round/$MAX_ROUNDS ==="

    # Step 1: Convert SVG to PNG
    python3 "$SCRIPT_DIR/svg_to_png.py" "$SVG_FILE" "$PNG_FILE" --width 800

    # Step 2: Send to Gemini for visual review
    REVIEW_PROMPT=$(cat <<EOF
You are reviewing an SVG diagram that was rendered to PNG. The diagram is supposed to show: $DESCRIPTION

Look at the image and check for these issues:
1. Are arrows properly aligned to the edges of rectangles/shapes? (not starting/ending inside shapes, not floating in whitespace)
2. Is all text horizontal and readable? (no rotated, vertical, or overlapping text)
3. Are shapes properly sized and spaced? (no overlapping shapes, no cramped layout)
4. Are colors correct and text visible against its background?
5. Is the overall layout clean and professional?

If the diagram looks good, respond with EXACTLY: PASS

If there are issues, respond with EXACTLY:
FAIL
[list each specific issue with the fix needed]

Be strict. Any arrow misalignment, text overlap, or layout issue is a failure.
EOF
)

    REVIEW_RESULT=$(echo "$REVIEW_PROMPT" | agents --model gemini-medium --file "$PNG_FILE" 2>/dev/null || true)

    if echo "$REVIEW_RESULT" | head -1 | grep -q "PASS"; then
        echo "PASS on round $round"
        rm -f "$PNG_FILE"
        exit 0
    fi

    echo "Issues found:"
    echo "$REVIEW_RESULT"

    if [[ "$round" -eq "$MAX_ROUNDS" ]]; then
        echo "Max rounds reached. Manual review needed."
        rm -f "$PNG_FILE"
        exit 1
    fi

    # Step 3: Regenerate with feedback
    CURRENT_SVG=$(cat "$SVG_FILE")
    REGEN_PROMPT=$(cat <<EOF
The following SVG diagram has visual issues that need fixing. The diagram shows: $DESCRIPTION

Current SVG:
\`\`\`xml
$CURRENT_SVG
\`\`\`

Issues found by visual review:
$REVIEW_RESULT

Fix ALL the issues listed above. Pay special attention to:
- Arrow endpoints must be calculated to intersect rectangle edges exactly
- All text must be horizontal, not rotated
- No overlapping elements
- Clean spacing between all elements

Output ONLY the corrected SVG code, no markdown fences, no explanation.
EOF
)

    echo "$REGEN_PROMPT" | agents --model gemini-medium 2>/dev/null > "${SVG_FILE}.tmp"

    # Strip any markdown fences
    sed -i '/^```/d' "${SVG_FILE}.tmp"
    mv "${SVG_FILE}.tmp" "$SVG_FILE"

    echo "Regenerated SVG, starting next review round..."
done

rm -f "$PNG_FILE"
