#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VECTOR_WORKTREE="${VECTOR_WORKTREE:-$SCRIPT_DIR}"
FIXTURE_ROOT="${FIXTURE_ROOT:-$VECTOR_WORKTREE/.tmp/v2-fixtures}"

rm -rf "$FIXTURE_ROOT"
mkdir -p "$FIXTURE_ROOT"

write_base_button() {
  cat > AuthButton.js <<'EOF'
export function renderSignInButton(label) {
  return `<button class="btn">${label}</button>`;
}
EOF
}

write_main_hotfix() {
  cat > AuthButton.js <<'EOF'
export function MicrosoftLogo() {
  return '<svg aria-label="Microsoft"></svg>';
}

export function renderSignInButton(label) {
  return `<button class="btn">${MicrosoftLogo()}<span>${label}</span></button>`;
}
EOF
}

write_dev_restructure() {
  cat > AuthButton.js <<'EOF'
function primaryButton(content) {
  const classes = ['btn', 'btn-primary'].join(' ');
  return `<button class="${classes}">${content}</button>`;
}

export function renderSignInButton(label) {
  return primaryButton(label);
}
EOF
}

write_main_comment_only() {
  cat > AuthButton.js <<'EOF'
// Button label is supplied by the caller.
export function renderSignInButton(label) {
  return `<button class="btn">${label}</button>`;
}
EOF
}

write_typo_base() {
  cat > AuthButton.js <<'EOF'
export function renderRecieveNotice(label) {
  return `<button class="btn">${label}</button>`;
}
EOF
}

write_main_typo_fix() {
  cat > AuthButton.js <<'EOF'
export function renderReceiveNotice(label) {
  return `<button class="btn">${label}</button>`;
}
EOF
}

write_dev_typo_superseding_restructure() {
  cat > AuthButton.js <<'EOF'
function receiveNoticeButton(content) {
  const classes = ['btn', 'btn-primary'].join(' ');
  return `<button class="${classes}">${content}</button>`;
}

export function renderNotice(label) {
  return receiveNoticeButton(label);
}
EOF
}

make_bundle() {
  local repo="$1"
  local scenario="$2"
  local out="$repo/bundle-$scenario"
  local pre_base pre_tip new_target post_tip predicted_tree predicted_output

  pre_base=$(git rev-parse base)
  pre_tip=$(git rev-parse dev)
  new_target=$(git rev-parse main)
  post_tip=$(git rev-parse resolved-pick-dev)
  predicted_output=$(git merge-tree --write-tree --merge-base="$pre_base" "$pre_tip" "$new_target" 2>/dev/null || true)
  predicted_tree="${predicted_output%%$'\n'*}"
  if ! git cat-file -e "$predicted_tree^{tree}" 2>/dev/null; then
    predicted_tree=$(git rev-parse "$post_tip^{tree}")
  fi

  mkdir -p "$out/conflict-artifacts"
  printf 'AuthButton.js\n' > "$out/conflict-artifacts/files.txt"
  git diff "$pre_base" "$new_target" --find-renames > "$out/target-delta.patch"
  git diff "$pre_base" "$pre_tip" --find-renames > "$out/branch-intended.patch"
  git diff "$new_target" "$post_tip" --find-renames > "$out/branch-actual.patch"
  git diff "$predicted_tree" "$post_tip^{tree}" --find-renames > "$out/residual.patch" || true
  git range-diff "$pre_base..$pre_tip" "$new_target..$post_tip" > "$out/range-diff.txt" 2>/dev/null || true
  git show "$pre_base:AuthButton.js" > "$out/conflict-artifacts/AuthButton.js.base"
  git show "$new_target:AuthButton.js" > "$out/conflict-artifacts/AuthButton.js.target"
  git show "$pre_tip:AuthButton.js" > "$out/conflict-artifacts/AuthButton.js.branch"
  git show "$post_tip:AuthButton.js" > "$out/conflict-artifacts/AuthButton.js.resolved"
  cat > "$out/refs.json" <<EOF
{
  "branch": "dev",
  "target": "main",
  "PRE_BASE": "$pre_base",
  "PRE_TIP": "$pre_tip",
  "NEW_TARGET": "$new_target",
  "POST_TIP": "$post_tip",
  "PREDICTED_TREE": "$predicted_tree",
  "verdict": "DIRTY-EXPLAINED"
}
EOF
  printf '%s\n' "$out"
}

init_repo() {
  local repo="$1"
  mkdir -p "$repo"
  cd "$repo"
  git init -q -b main
  git config user.email "prototype@example.invalid"
  git config user.name "Prototype Fixture"
}

make_hotfix_on_restructured() {
  local repo="$FIXTURE_ROOT/hotfix-on-restructured"
  init_repo "$repo"
  write_base_button
  git add AuthButton.js
  git commit -q -m "base: sign-in button"
  git tag base
  write_main_hotfix
  git commit -am "fix: add Microsoft logo to sign-in button" -q
  git checkout -q -b dev base
  write_dev_restructure
  git commit -am "refactor: extract primary button helper" -q
  git checkout -q -b resolved-pick-dev main
  git checkout -q dev -- AuthButton.js
  git commit -am "resolve: pick dev refactor side" -q
  make_bundle "$repo" "bad-pick"
}

make_orthogonal_comment_pick() {
  local repo="$FIXTURE_ROOT/orthogonal-comment-pick"
  init_repo "$repo"
  write_base_button
  git add AuthButton.js
  git commit -q -m "base: sign-in button"
  git tag base
  write_main_comment_only
  git commit -am "style: document sign-in button label source" -q
  git checkout -q -b dev base
  write_dev_restructure
  git commit -am "refactor: extract primary button helper" -q
  git checkout -q -b resolved-pick-dev main
  git checkout -q dev -- AuthButton.js
  git commit -am "resolve: pick dev refactor side" -q
  make_bundle "$repo" "legit-pick"
}

make_superseded_typo_pick() {
  local repo="$FIXTURE_ROOT/superseded-typo-pick"
  init_repo "$repo"
  write_typo_base
  git add AuthButton.js
  git commit -q -m "base: receive notice button with typo"
  git tag base
  write_main_typo_fix
  git commit -am "fix: correct recieve typo" -q
  git checkout -q -b dev base
  write_dev_typo_superseding_restructure
  git commit -am "refactor: extract receive notice button helper" -q
  git checkout -q -b resolved-pick-dev main
  git checkout -q dev -- AuthButton.js
  git commit -am "resolve: pick dev refactor side" -q
  make_bundle "$repo" "legit-superseded"
}

make_hotfix_on_restructured
make_orthogonal_comment_pick
make_superseded_typo_pick

cat > "$FIXTURE_ROOT/README.md" <<EOF
# V2 fixtures

Generated repositories:

- hotfix-on-restructured: bad pick-one-side; target hotfix is dropped by picking branch refactor.
- orthogonal-comment-pick: legitimate pick; target side is comment-only.
- superseded-typo-pick: legitimate pick; target typo fix is already absorbed/superseded by branch restructure.

Each repo contains a bundle-* directory with verified-rebase-shaped refs/diffs.
EOF

printf 'FIXTURE_ROOT=%s\n' "$FIXTURE_ROOT"
