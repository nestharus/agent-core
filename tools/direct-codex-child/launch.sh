#!/usr/bin/env bash
# One foreground Codex child; the caller owns the native terminal session.
set -u -o pipefail
umask 077

usage() {
  cat <<'EOF'
Usage: launch.sh --profile .codex[2|3|4] --cwd /absolute/workspace \
  --prompt /absolute/prompt.md --runs-dir /absolute/runs --id child-name [--dry-run]

The launcher reserves one unique attempt directory and runs one Codex child in
the foreground. Launch it in a native persistent terminal, record that terminal's
handle in state.txt, and await its real exit. --dry-run validates local inputs
without creating files or invoking Codex; it does not certify MCP state.
EOF
}

die() { printf 'direct-codex-child: %s\n' "$*" >&2; exit 2; }

profile='' cwd='' prompt='' runs_dir='' child_id='' dry_run=false
while (($#)); do
  case "$1" in
    --profile|--cwd|--prompt|--runs-dir|--id)
      (($# >= 2)) || die "missing value for $1"
      case "$1" in
        --profile) [[ -z $profile ]] || die 'duplicate --profile'; profile=$2 ;;
        --cwd) [[ -z $cwd ]] || die 'duplicate --cwd'; cwd=$2 ;;
        --prompt) [[ -z $prompt ]] || die 'duplicate --prompt'; prompt=$2 ;;
        --runs-dir) [[ -z $runs_dir ]] || die 'duplicate --runs-dir'; runs_dir=$2 ;;
        --id) [[ -z $child_id ]] || die 'duplicate --id'; child_id=$2 ;;
      esac
      shift 2 ;;
    --dry-run) [[ $dry_run == false ]] || die 'duplicate --dry-run'; dry_run=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

case "$profile" in .codex|.codex2|.codex3|.codex4) ;; *) die 'profile must be .codex, .codex2, .codex3, or .codex4' ;; esac
[[ $child_id =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || die 'id must use letters, digits, dot, underscore, or hyphen'
for value in "$cwd" "$prompt" "$runs_dir"; do
  [[ $value == /* && $value != *$'\n'* ]] || die 'cwd, prompt, and runs-dir must be absolute paths without newlines'
done
[[ -d $cwd ]] || die "cwd is not a directory: $cwd"
[[ -f $prompt && -s $prompt && -r $prompt ]] || die "prompt must be a readable nonempty file: $prompt"
cwd=$(cd -P -- "$cwd" && pwd -P) || die 'cannot resolve cwd'
[[ -n ${HOME:-} ]] || die 'HOME is required to select a profile'
profile_home="$HOME/$profile"
[[ -f $profile_home/config.toml ]] || die "missing profile config: $profile_home/config.toml"
[[ -d $profile_home ]] || die "missing profile: $profile_home"

if [[ $dry_run == true ]]; then
  printf 'DRY RUN: profile=%s model=gpt-6-sol effort=xhigh cwd=%s prompt=%s runs-dir=%s id=%s\n' \
    "$profile" "$cwd" "$prompt" "$runs_dir" "$child_id"
  printf 'DRY RUN: no artifacts created; Codex and MCP preflight not invoked\n'
  exit 0
fi

command -v codex >/dev/null 2>&1 || die 'codex is not installed'
command -v python3 >/dev/null 2>&1 || die 'python3 is required to read configured MCP server names'
server_names=$(python3 - "$profile_home/config.toml" <<'PY'
import re
import sys
import tomllib

with open(sys.argv[1], 'rb') as config_file:
    config = tomllib.load(config_file)
servers = config.get('mcp_servers', {})
if not isinstance(servers, dict):
    raise SystemExit('mcp_servers must be a table')
for name in sorted(servers):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', name):
        raise SystemExit(f'unsupported MCP server name: {name!r}')
    print(name)
PY
) || die 'cannot read MCP server configuration'

mcp_flags=(-c 'mcp_servers={}')
if [[ -n $server_names ]]; then
  while IFS= read -r server; do
    mcp_flags+=(-c "mcp_servers.$server.enabled=false")
  done <<< "$server_names"
fi
mcp_report=$(CODEX_HOME="$profile_home" codex "${mcp_flags[@]}" mcp list 2>&1) || die 'MCP preflight failed; Codex child was not started'
if [[ -n $server_names ]]; then
  printf '%s\n' "$mcp_report" | awk -v expected="$server_names" '
    BEGIN { count=split(expected, names, "\n"); for (i=1; i<=count; i++) wanted[names[i]]=1 }
    NF==0 || $1=="Name" { next }
    { if (!($1 in wanted) || seen[$1]++) bad=1
      status=0
      for (i=2; i<=NF; i++) if ($i=="disabled" || $i=="enabled") {
        status++
        if ($i!="disabled") bad=1
      }
      if (status!=1) bad=1
      found++ }
    END { if (bad || found!=count) exit 1 }
  ' || die 'MCP preflight did not confirm every configured server disabled'
else
  [[ $mcp_report == *'No MCP servers configured'* ]] || die 'MCP preflight reported an unexpected server'
fi

mkdir -p -- "$runs_dir" || die "cannot create runs-dir: $runs_dir"
runs_dir=$(cd -P -- "$runs_dir" && pwd -P) || die 'cannot resolve runs-dir'
attempt=$(mktemp -d "$runs_dir/$child_id.XXXXXXXX") || die 'cannot reserve attempt directory'
prompt_snapshot="$attempt/prompt.md"
log_path="$attempt/log.txt"
final_path="$attempt/final.md"
state_path="$attempt/state.txt"
cp -- "$prompt" "$prompt_snapshot" || die 'cannot snapshot prompt'
chmod 400 -- "$prompt_snapshot" || die 'cannot protect prompt snapshot'
: > "$log_path" || die 'cannot create log'
: > "$final_path" || die 'cannot reserve final'
git_head=$(git -C "$cwd" rev-parse HEAD 2>/dev/null || printf 'unavailable')
git_branch=$(git -C "$cwd" branch --show-current 2>/dev/null || printf 'unavailable')
{
  printf 'child_id=%s\nprofile=%s\nmodel=gpt-6-sol\neffort=xhigh\n' "$child_id" "$profile"
  printf 'cwd=%s\ngit_branch=%s\ngit_head_at_start=%s\n' "$cwd" "$git_branch" "$git_head"
  printf 'prompt=%s\nlog=%s\nfinal=%s\n' "$prompt_snapshot" "$log_path" "$final_path"
  printf 'start_utc=%s\nexpected_status=native terminal exit plus codex_exit entry\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
} > "$state_path" || die 'cannot write state'

printf 'DIRECT_CODEX_ATTEMPT=%s\nDIRECT_CODEX_STATE=%s\n' "$attempt" "$state_path"
printf 'MCP_PREFLIGHT=all configured servers disabled\n'
cd -- "$cwd" || die "cannot enter cwd: $cwd"
CODEX_HOME="$profile_home" codex exec --dangerously-bypass-approvals-and-sandbox \
  -m gpt-6-sol -c 'model_reasoning_effort="xhigh"' "${mcp_flags[@]}" \
  -C "$cwd" --color never -o "$final_path" - < "$prompt_snapshot" 2>&1 | tee -a "$log_path"
pipeline_status=("${PIPESTATUS[@]}")
codex_rc=${pipeline_status[0]}
tee_rc=${pipeline_status[1]}
printf 'codex_exit=%s\nlog_capture_exit=%s\nend_utc=%s\n' "$codex_rc" "$tee_rc" "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" >> "$state_path"
if ((tee_rc != 0)); then
  printf 'direct-codex-child: log capture failed with status %s; log may be incomplete\n' "$tee_rc" >&2
fi
printf 'DIRECT_CODEX_EXIT=%s\n' "$codex_rc" | tee -a "$log_path"
if [[ -s $final_path ]]; then
  printf 'DIRECT_CODEX_FINAL_BEGIN=%s\n' "$final_path"
  cat -- "$final_path"
  printf '\nDIRECT_CODEX_FINAL_END\n'
else
  printf 'DIRECT_CODEX_FINAL_MISSING_OR_EMPTY=%s\n' "$final_path"
fi
exit "$codex_rc"
