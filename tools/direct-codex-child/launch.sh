#!/usr/bin/env bash
# One foreground Codex child; the caller owns the native terminal session.
set -u -o pipefail
umask 077

usage() {
  cat <<'EOF'
Usage: launch.sh --profile .codex[2|3|4|5] --cwd /absolute/workspace \
  --prompt /absolute/prompt.md --runs-dir /absolute/runs --id child-name \
  [--model native-model --effort native-effort] \
  [--ephemeral] [--log-max-bytes POSITIVE_INTEGER] \
  [--session-lifecycle oneoff|reusable --session-owner-receipt /absolute/receipt.json] \
  [--dry-run | --preflight-only]

The launcher reserves one unique attempt directory and runs one Codex child in
the foreground. Launch it in a native persistent terminal, record that terminal's
handle in state.txt, and await its real exit. --dry-run validates local inputs
without creating files or invoking Codex; it does not certify MCP state.
--preflight-only checks effective MCP state without creating an attempt or child.
Without --model/--effort the child uses gpt-6.1-sol at high. Both values are
passed literally to Codex. --route-json is the contextual dispatcher's
single-line resolution record, stored as route.json in the attempt.
The launcher takes no profile lock: concurrent launches on one profile run
side by side. --lease-wait SECONDS is a retired option, accepted and ignored.
EOF
}

die() { printf 'direct-codex-child: %s\n' "$*" >&2; exit 2; }

profile='' cwd='' prompt='' runs_dir='' child_id='' dry_run=false preflight_only=false
session_lifecycle='' session_owner_receipt=''
model='' effort='' route_json='' ephemeral=false log_max_bytes='' execution_pool_routes=''
while (($#)); do
  case "$1" in
    --profile|--cwd|--prompt|--runs-dir|--id|--model|--effort|--route-json|--lease-wait|--log-max-bytes|--execution-pool-routes|--session-lifecycle|--session-owner-receipt)
      (($# >= 2)) || die "missing value for $1"
      case "$1" in
        --session-lifecycle) [[ -z $session_lifecycle ]] || die 'duplicate --session-lifecycle'; session_lifecycle=$2 ;;
        --session-owner-receipt) [[ -z $session_owner_receipt ]] || die 'duplicate --session-owner-receipt'; session_owner_receipt=$2 ;;
        --profile) [[ -z $profile ]] || die 'duplicate --profile'; profile=$2 ;;
        --cwd) [[ -z $cwd ]] || die 'duplicate --cwd'; cwd=$2 ;;
        --prompt) [[ -z $prompt ]] || die 'duplicate --prompt'; prompt=$2 ;;
        --runs-dir) [[ -z $runs_dir ]] || die 'duplicate --runs-dir'; runs_dir=$2 ;;
        --id) [[ -z $child_id ]] || die 'duplicate --id'; child_id=$2 ;;
        --model) [[ -z $model ]] || die 'duplicate --model'; model=$2 ;;
        --effort) [[ -z $effort ]] || die 'duplicate --effort'; effort=$2 ;;
        --route-json) [[ -z $route_json ]] || die 'duplicate --route-json'; route_json=$2 ;;
        --execution-pool-routes) [[ -z $execution_pool_routes ]] || die 'duplicate --execution-pool-routes'; execution_pool_routes=$2 ;;
        --log-max-bytes) [[ -z $log_max_bytes ]] || die 'duplicate --log-max-bytes'; log_max_bytes=$2 ;;
        --lease-wait) ;;  # retired with the profile lock; accepted and ignored
      esac
      shift 2 ;;
    --dry-run) [[ $dry_run == false ]] || die 'duplicate --dry-run'; dry_run=true; shift ;;
    --preflight-only) [[ $preflight_only == false ]] || die 'duplicate --preflight-only'; preflight_only=true; shift ;;
    --ephemeral) [[ $ephemeral == false ]] || die 'duplicate --ephemeral'; ephemeral=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done
[[ $dry_run == false || $preflight_only == false ]] || die 'choose either --dry-run or --preflight-only'

[[ -z $session_lifecycle && -z $session_owner_receipt ]] || {
  [[ $session_lifecycle == oneoff || $session_lifecycle == reusable ]] || die 'explicit session lifecycle required'
  [[ $session_owner_receipt == /* && -f $session_owner_receipt ]] || die 'absolute owner receipt required'
}
case "$profile" in .codex|.codex2|.codex3|.codex4|.codex5) ;; *) die 'profile must be .codex, .codex2, .codex3, .codex4, or .codex5' ;; esac
[[ -n $model || -z $effort ]] && [[ -z $model || -n $effort ]] \
  || die 'give --model and --effort together, or neither for gpt-6.1-sol/high'
model=${model:-gpt-6.1-sol}
effort=${effort:-high}
[[ $model =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || die 'model must be a native model id'
[[ $effort =~ ^[a-z]+$ ]] || die 'effort must be a lowercase native effort'
[[ -z $log_max_bytes || $log_max_bytes =~ ^[1-9][0-9]{0,11}$ ]] \
  || die 'log-max-bytes must be a positive decimal integer of at most 12 digits'
[[ $route_json != *$'\n'* ]] || die 'route-json must be a single line'
[[ -z $execution_pool_routes || ( $execution_pool_routes == /* && $execution_pool_routes != *$'\n'* ) ]] \
  || die 'execution-pool-routes must be an absolute public control path'
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
  printf 'DRY RUN: profile=%s model=%s effort=%s cwd=%s prompt=%s runs-dir=%s id=%s\n' \
    "$profile" "$model" "$effort" "$cwd" "$prompt" "$runs_dir" "$child_id"
  printf 'DRY RUN: no artifacts created; Codex and MCP preflight not invoked\n'
  exit 0
fi

command -v codex >/dev/null 2>&1 || die 'codex is not installed'
command -v python3 >/dev/null 2>&1 || die 'python3 is required to inspect effective MCP servers'
launcher_dir=$(cd -P -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P) || die 'cannot locate launcher'
[[ -z $log_max_bytes || -r $launcher_dir/capture_output.py ]] || die 'missing bounded output collector'
parse_mcp_json() {
  python3 -c '
import json
import re
import sys

try:
    servers = json.load(sys.stdin)
    if not isinstance(servers, list):
        raise ValueError("expected an MCP server list")
    rows = {}
    for server in servers:
        if not isinstance(server, dict):
            raise ValueError("invalid MCP server entry")
        name, enabled = server.get("name"), server.get("enabled")
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", name):
            raise ValueError("unsupported MCP server name")
        if type(enabled) is not bool or name in rows:
            raise ValueError("invalid or duplicate MCP server status")
        rows[name] = enabled
    for name in sorted(rows):
        print(f"{name}\t{int(rows[name])}")
except (ValueError, TypeError, json.JSONDecodeError) as error:
    print(f"invalid effective MCP list: {error}", file=sys.stderr)
    sys.exit(1)
'
}

discovery_report=$(CODEX_HOME="$profile_home" codex -c 'mcp_servers={}' mcp list --json 2>/dev/null) \
  || die 'MCP discovery failed; Codex child was not started'
server_rows=$(printf '%s\n' "$discovery_report" | parse_mcp_json) \
  || die 'cannot parse effective MCP server discovery'

mcp_flags=(-c 'mcp_servers={}')
expected_rows=''
server_count=0
if [[ -n $server_rows ]]; then
  while IFS= read -r row; do
    server=${row%%$'\t'*}
    if [[ $server == openaiDeveloperDocs ]]; then
      continue
    fi
    mcp_flags+=(-c "mcp_servers.$server.enabled=false")
    expected_rows+="$server"$'\t0\n'
    ((server_count+=1))
  done <<< "$server_rows"
fi
mcp_flags+=(-c 'mcp_servers.openaiDeveloperDocs.url="https://developers.openai.com/mcp"' \
            -c 'mcp_servers.openaiDeveloperDocs.enabled=false')
expected_rows+='openaiDeveloperDocs'$'\t0\n'
((server_count+=1))
expected_rows=$(printf '%s' "$expected_rows" | LC_ALL=C sort)
mcp_report=$(CODEX_HOME="$profile_home" codex "${mcp_flags[@]}" mcp list --json 2>/dev/null) \
  || die 'MCP preflight failed; Codex child was not started'
verified_rows=$(printf '%s\n' "$mcp_report" | parse_mcp_json) \
  || die 'cannot parse effective MCP preflight'
[[ $verified_rows == "$expected_rows" ]] \
  || die 'MCP preflight did not confirm every effective server disabled'
if [[ $preflight_only == true ]]; then
  printf 'MCP_PREFLIGHT=all effective servers disabled profile=%s count=%s\n' \
    "$profile" "$server_count"
  exit 0
fi

# Request restriction of delegation-like features. Metadata only, before any task
# starts, and upgrade-tolerant: never a version check or a refusal. Only names
# the installed CLI lists are disabled, through -c (`--disable` rejects unknown
# names); feature metadata cannot establish model-facing tool absence. The child
# still launches with capability recorded as not established.
delegation_like='multi_agent|agent_message|collab|subagent'
delegation_rows() {
  CODEX_HOME="$profile_home" codex "$@" features list 2>/dev/null | python3 -c '
import re
import sys

rows = {}
for line in sys.stdin:
    fields = line.split()
    if fields and re.search(sys.argv[1], fields[0]) and (len(fields) < 3 or fields[-1] not in ("true", "false")):
        sys.exit(1)
    if len(fields) >= 3 and fields[-1] in ("true", "false") and re.fullmatch(r"[a-z0-9_]+", fields[0]):
        if fields[0] in rows:
            sys.exit(1)
        rows[fields[0]] = fields[-1]
if not rows:
    sys.exit(1)
for name in sorted(rows):
    if re.search(sys.argv[1], name):
        print(f"{name}\t{rows[name]}")
' "$delegation_like"
}
delegation_flags=() delegation_status=not-established delegation_note='' delegation_readback=''
delegation_feature_readback=unknown
listed=$(delegation_rows); listed_rc=$?
if ((listed_rc == 0)) && [[ -n $listed ]]; then
  while IFS=$'\t' read -r feature _; do
    delegation_flags+=(-c "features.$feature=false")
  done <<< "$listed"
  if delegation_readback=$(delegation_rows "${delegation_flags[@]}") && [[ -n $delegation_readback ]]; then
    expected_readback=$(printf '%s\n' "$listed" | sed 's/\ttrue$/\tfalse/')
    if [[ $delegation_readback == "$expected_readback" ]]; then
      delegation_feature_readback=all-listed-false
      delegation_note='listed features read back false; model-facing delegation capability not established'
    else
      delegation_feature_readback=incomplete-or-enabled
      delegation_note='feature readback incomplete or still enabled; model-facing delegation capability not established'
    fi
  else
    delegation_flags=() delegation_readback=''
    delegation_note='feature readback with disable flags failed; flags not passed'
  fi
elif ((listed_rc == 0)); then
  delegation_note='no delegation-like feature listed'
else
  delegation_note='feature listing unavailable or unparsed'
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
if [[ -n $route_json ]]; then
  printf '%s\n' "$route_json" > "$attempt/route.json" || die 'cannot write route record'
fi
git_head=$(git -C "$cwd" rev-parse HEAD 2>/dev/null || printf 'unavailable')
git_branch=$(git -C "$cwd" branch --show-current 2>/dev/null || printf 'unavailable')
{
  printf 'child_id=%s\nprofile=%s\nmodel=%s\neffort=%s\n' "$child_id" "$profile" "$model" "$effort"
  [[ -z $route_json ]] || printf 'route_record=%s\n' "$attempt/route.json"
  printf 'cwd=%s\ngit_branch=%s\ngit_head_at_start=%s\n' "$cwd" "$git_branch" "$git_head"
  printf 'prompt=%s\nlog=%s\nfinal=%s\n' "$prompt_snapshot" "$log_path" "$final_path"
  printf 'ephemeral=%s\nlog_max_bytes=%s\n' "$ephemeral" "${log_max_bytes:-unlimited}"
  [[ -z $log_max_bytes ]] || printf 'log_capture_summary=%s\n' "$attempt/capture.json"
  printf 'delegation_capability=%s\n' "$delegation_status"
  [[ -z $delegation_note ]] || printf 'delegation_capability_note=%s\n' "$delegation_note"
  printf 'delegation_feature_readback=%s\n' "$delegation_feature_readback"
  [[ -z $listed ]] || printf 'delegation_features_listed=%s\n' "$(printf '%s' "$listed" | tr '\t\n' '=,')"
  printf 'delegation_restriction_args=%s\n' "${delegation_flags[*]}"
  [[ -z $delegation_readback ]] || printf 'delegation_features=%s\n' "$(printf '%s' "$delegation_readback" | tr '\t\n' '=,')"
  printf 'delegation_scope=built-in features listed by the installed CLI; shell-launched processes, hooks, plugins and skills not covered\n'
  printf 'transport=direct\nprofile_lock=none\n'
  printf 'start_utc=%s\nexpected_status=native terminal exit plus codex_exit entry\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
} > "$state_path" || die 'cannot write state'

if [[ -n $session_lifecycle ]]; then
  codex_binary=$(command -v codex)
  retirement_binding=$(python3 - "$codex_binary" "$profile_home" "$profile" "$attempt" "$ephemeral" "$session_owner_receipt" <<'PYB'
import hashlib, json, os, sys
binary, home, profile, attempt, ephemeral, receipt = sys.argv[1:]
binary = os.path.realpath(binary)
with open(receipt) as f:
    owner = json.load(f)
route = os.path.join(attempt, 'route.json')
print(json.dumps(dict(binary=binary, binary_sha256=hashlib.sha256(open(binary,'rb').read()).hexdigest(),
    codex_home=home, profile=profile, account_binding=owner['account_binding'],
    route_ref=route if os.path.isfile(route) else None,
    route_digest=hashlib.sha256(open(route,'rb').read()).hexdigest() if os.path.isfile(route) else None,
    ephemeral=ephemeral == 'true')))
PYB
  ) || die 'cannot capture original session binding'
  python3 "$launcher_dir/session_retirement.py" bootstrap --attempt "$attempt" \
    --receipt "$session_owner_receipt" --binding "$retirement_binding" --lifetime "$session_lifecycle" \
    || die 'cannot create prospective session manifest'
  printf 'session_retirement_manifest=%s\n' "$attempt/session-retirement.json" >> "$state_path"
fi

printf 'DIRECT_CODEX_ATTEMPT=%s\nDIRECT_CODEX_STATE=%s\n' "$attempt" "$state_path"
printf 'MCP_PREFLIGHT=all effective servers disabled\n'
printf 'DELEGATION_CAPABILITY=%s\n' "$delegation_status"
cd -- "$cwd" || die "cannot enter cwd: $cwd"
session_flags=()
[[ $ephemeral == false ]] || session_flags+=(--ephemeral)
[[ -z $session_lifecycle ]] || session_flags+=(--json)
run_child() {
  local admission=()
  if [[ -n $execution_pool_routes ]]; then
    admission=(python3 "$launcher_dir/../direct-child/execution_pool.py" --routes "$execution_pool_routes" \
      exec --profile "$profile" --receipt "$attempt/pool-admission.json" --)
  fi
  CODEX_HOME="$profile_home" "${admission[@]}" "${codex_binary:-codex}" exec --dangerously-bypass-approvals-and-sandbox \
    -m "$model" -c "model_reasoning_effort=\"$effort\"" "${mcp_flags[@]}" "${delegation_flags[@]}" \
    "${session_flags[@]}" -C "$cwd" --color never -o "$final_path" -
}
run_observed_child() {
  if [[ -n $session_lifecycle ]]; then
    # Typed stdout only; stderr remains opaque and never reaches the extractor.
    run_child | python3 "$launcher_dir/session_retirement.py" intercept --attempt "$attempt"
    observed_status=("${PIPESTATUS[@]}")
    if ((observed_status[1] != 0)); then
      printf 'session_metadata_capture=failed\n' >> "$state_path"
    fi
    return "${observed_status[0]}"
  else
    run_child
  fi
}
if [[ -n $log_max_bytes ]]; then
  run_observed_child < "$prompt_snapshot" 2>&1 | python3 "$launcher_dir/capture_output.py" \
    --log "$log_path" --summary "$attempt/capture.json" --max-bytes "$log_max_bytes"
  pipeline_status=("${PIPESTATUS[@]}")
else
  run_observed_child < "$prompt_snapshot" 2>&1 | tee -a "$log_path"
  pipeline_status=("${PIPESTATUS[@]}")
fi
codex_rc=${pipeline_status[0]}
tee_rc=${pipeline_status[1]}
if [[ -n $session_lifecycle ]]; then
  python3 "$launcher_dir/session_retirement.py" end --attempt "$attempt" --code "$codex_rc" \
    || printf 'session_end_receipt=failed\n' >> "$state_path"
fi
# Codex's human log renders collaboration tool use as `collab:` lines (Wait seen;
# spawn not rendered), so this count is a detection lead, not proof either way.
collab_lines=$(grep -c '^collab:' -- "$log_path" 2>/dev/null) || collab_lines=${collab_lines:-unavailable}
printf 'codex_exit=%s\nlog_capture_exit=%s\nlog_collab_lines=%s\nend_utc=%s\n' "$codex_rc" "$tee_rc" "$collab_lines" "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" >> "$state_path"
if ((tee_rc != 0)); then
  printf 'direct-codex-child: log capture failed with status %s; log may be incomplete\n' "$tee_rc" >&2
fi
if [[ -n $log_max_bytes ]]; then
  # The bounded log contains only the selected output prefix; exits live in state.
  printf 'DIRECT_CODEX_EXIT=%s\n' "$codex_rc"
else
  printf 'DIRECT_CODEX_EXIT=%s\n' "$codex_rc" | tee -a "$log_path"
fi
if [[ -s $final_path ]]; then
  printf 'DIRECT_CODEX_FINAL_BEGIN=%s\n' "$final_path"
  cat -- "$final_path"
  printf '\nDIRECT_CODEX_FINAL_END\n'
else
  printf 'DIRECT_CODEX_FINAL_MISSING_OR_EMPTY=%s\n' "$final_path"
fi
exit "$codex_rc"
