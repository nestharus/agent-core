"""Bounded existing-monitor metadata acquisition. No listener or shell execution.

Selection of an admitted metadata capability is the caller's responsibility.
Only relevant typed fields enter the projection. Producer text/commands never gain
execution authority. Raw custody is write-only and never used as a replay feed.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import math
import json
import os
from pathlib import Path
import stat
from copy import deepcopy
from adapter_support import exact_json, need
from board_receipt_adapter import stamp

MONITOR = Path("/home/nes/.local/share/rfq-root-emergency-captures/01a1276d-c325-7c01-a079-ca1fbea2a3f4/20261030/Install-Work-board-monitors-using-allowed-dot-codex3-profile-20261101")
INPUTS = tuple(MONITOR/"state"/n for n in
               ("branches-latest.json", "branches-health.json", "branches-commands.json"))
MAX_INPUT = 32 * 1024**2
MAX_AGGREGATE = 128 * 1024**2
LATEST_KEYS = {"check_id", "checked_at", "code_version", "errors", "result"}
class HeldInput(ValueError):
    """A whole input is unavailable; exception text is always a static reason."""

def seq(obj, maximum=1000):
    if type(obj) is not list or len(obj)>maximum:
        raise HeldInput("unrecognized-input-list-whole-family-held")
    return obj

def text(core, value):
    core.token(value)
    return value

def label(value):
    # Operational source labels may be absolute paths; they are not core tokens.
    need(type(value) is str and 0<len(value)<=1024 and all(ord(c)>=32 for c in value),
         "bounded-operational-source-label")
    return value


def integer(value, minimum=0):
    if type(value) is not int or value < minimum:
        raise HeldInput("typed-integer-required")
    return value

def number(value):
    if type(value) not in (int,float) or not math.isfinite(value) or value<0:
        raise HeldInput("typed-finite-nonnegative-age-required")
    return value

def bool_(value):
    if type(value) is not bool:
        raise HeldInput("typed-Boolean-required")
    return value

def required(obj, names):
    """Validate consumed fields only. Extra metadata conveys no authority."""
    if type(obj) is not dict or not set(names) <= obj.keys():
        raise HeldInput("missing-relevant-metadata-fields")


def project_latest(core, data, repo, prs, refs):
    """Scope first; validate consumed values, ignore unrelated producer metadata.

    Review, eligibility fulfillment, CI and logical edges are never inferred from
    physical rows. In particular, an empty projection is not complete coverage.
    """
    required(data,LATEST_KEYS); r=data["result"]
    required(r,("coverage","selected","pending_review_excluded","stale_alerts"))
    errors=seq(data["errors"])
    source_errors=[]
    for e in errors:
        required(e,("source","state"))
        source_errors.append({"source":label(e["source"]),"state":text(core,e["state"])})
    result={"check_id":text(core,data["check_id"]),
            "code_version":text(core,data["code_version"]),
            "checked_at":stamp(data["checked_at"]).isoformat(),
            "source_failures":len(errors),"source_errors":source_errors,
            "coverage":[],"rows":[],"complete_inventory":False}
    for c in seq(r["coverage"]):
        required(c,())
        if c.get("repo")!=repo: continue
        required(c,("repo","remote_live_refs","remote_live_state","local_registry"))
        result["coverage"].append({"repo":repo,"remote_live_refs":integer(c["remote_live_refs"]),
            "remote_live_state":text(core,c["remote_live_state"]),
            "local_registry":text(core,c["local_registry"])})
    for category in ("selected","pending_review_excluded","stale_alerts"):
        for row in seq(r[category]):
            required(row,())
            if row.get("repo")!=repo: continue
            # Determine selected membership before touching unrelated row facets.
            rowprs=seq(row.get("prs",[]))
            matched=[pr for pr in rowprs if type(pr) is dict and pr.get("number") in prs]
            if row.get("branch") not in refs and not matched: continue
            required(row,("branch","age_seconds","activity","distinct_heads","heads"))
            neutral={"category":category,"repo":repo,"branch":text(core,row["branch"]),
                "age_seconds":number(row["age_seconds"]),"activity":number(row["activity"]),
                "distinct_heads":[core.oid(v) for v in seq(row["distinct_heads"])],
                "heads":[],"prs":[]}
            for h in seq(row["heads"]):
                required(h,("oid","activity"))
                neutral["heads"].append({"oid":core.oid(h["oid"]),"activity":number(h["activity"])})
            for pr in matched:
                required(pr,("repo","branch","number","head"))
                need(pr["repo"]==repo and pr["branch"]==row["branch"],"collector-PR-ref-binding")
                neutral["prs"].append({"number":integer(pr["number"],1),"head":core.oid(pr["head"]),
                                      "branch":text(core,pr["branch"]),"repo":repo})
            result["rows"].append(neutral)
    return result


def project_health(core, data):
    required(data,("check_id","code_version","started_at","ended_at","source_state",
        "source_failures","numeric_exit","queue_accepted","recipient_acknowledged","actual_board_notice"))
    return {"check_id":text(core,data["check_id"]),"code_version":text(core,data["code_version"]),
        "started_at":stamp(data["started_at"]).isoformat(),
        "ended_at":stamp(data["ended_at"]).isoformat(),"source_state":text(core,data["source_state"]),
        "source_failures":integer(data["source_failures"]),"numeric_exit":integer(data["numeric_exit"]),
        "queue_accepted":bool_(data["queue_accepted"]),
        "recipient_acknowledged":bool_(data["recipient_acknowledged"]),
        "actual_board_notice":bool_(data["actual_board_notice"]),
        "delivery_stage":"UNKNOWN_MODEL_RECEIPT_NOT_ACQUIRED"}


def project_commands(core,data):
    """Only generation/count metadata. Never return or execute any command argv."""
    required(data,("category","check_id","code_version","commands"))
    need(data["category"]=="branches","commands-category-binding")
    commands=seq(data["commands"],10000)
    return {"category":"branches","check_id":text(core,data["check_id"]),
            "code_version":text(core,data["code_version"]),"count":len(commands),
            "execution_authority":False}

@dataclass(frozen=True)
class ReadSelection:
    """Parent assertion of admitted roles and kernel-RO setup; not authentication."""
    paths: tuple
    producer: str
    role: str = "ADMITTED_BOUNDED_ORDINARY_OBSERVATION_METADATA"
    kernel_readonly: bool = False

def acquire_once(core, selection, *, repo, prs, refs, custody, receipt=None):
    """Read three exact admitted files at most once. No alternate discovery.

    custody(name, bytes) must write to fresh private custody before projection.
    No command content is returned or executed. Unknown irrelevant fields are ignored;
    consumed fields remain strictly typed and bound to the selected generation.
    """
    need(selection.paths==INPUTS and selection.producer==str(MONITOR)
         and selection.role=="ADMITTED_BOUNDED_ORDINARY_OBSERVATION_METADATA"
         and selection.kernel_readonly is True, "exact-admitted-read-selection-required")
    result={"latest":None,"health":None,"commands":None,"frontiers":[]}
    total=0
    for path,kind in zip(INPUTS,("latest","health","commands")):
        start=datetime.now(timezone.utc).isoformat()
        size=None; state="UNKNOWN"; reason="bounded-input-unavailable"
        try:
            fd=os.open(path, os.O_RDONLY|os.O_NOFOLLOW)
            with os.fdopen(fd,"rb") as f:
                need(stat.S_ISREG(os.fstat(f.fileno()).st_mode),"regular-observation-file")
                raw=f.read(MAX_INPUT+1)
            custody(path.name,raw)
            size=len(raw); total+=size
            if total>MAX_AGGREGATE: raise HeldInput("aggregate-budget-whole-input-held")
            if len(raw)>MAX_INPUT: raise HeldInput("bounded-input-too-large-whole-family-held")
            def pairs(items):
                out={}
                for k,v in items:
                    if k in out: raise HeldInput("duplicate-observation-key")
                    out[k]=v
                return out
            data=json.loads(raw,object_pairs_hook=pairs)
            result[kind]=(project_latest(core,data,repo,prs,refs) if kind=="latest"
                          else project_health(core,data) if kind=="health" else project_commands(core,data))
            state="PROJECTED"; reason=None
        except (OSError,ValueError,KeyError,TypeError) as exc:
            # No exception text/body projection. Keep the input UNKNOWN, never healthy.
            if isinstance(exc,HeldInput): reason=str(exc)
            else: reason="typed-schema-or-read-unavailable-whole-input-held"
            result["frontiers"].append(kind+"-input-UNKNOWN")
        finally:
            if receipt is not None:
                receipt({"input":kind,"path":str(path),"acquisition_start":start,
                         "acquisition_end":datetime.now(timezone.utc).isoformat(),
                         "bytes_acquired":size,"state":state,"reason":reason,
                         "per_file_cap":MAX_INPUT,"aggregate_cap":MAX_AGGREGATE,
                         "raw_hash_or_mtime_used":False})
    return deepcopy(result)
