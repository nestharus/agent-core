"""Existing board CLI execution and conservative receipt decoding.

No registration, raw queue/DB/profile lookup, automatic retry, or polling fallback.
Tests inject an explicitly mocked external transport; production executes normal
board.py open/reply through ProcessCapture only after parent binds actual identity.
"""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import time
import uuid
from adapter_support import AdapterError, need, BOARD, RECIPIENT, record

CLI = "/home/nes/ai/tools/message-board/board.py"
STATES=("pending","sending","queued","acknowledged","failed","ambiguous","managed_pending")

def stamp(value):
    need(isinstance(value,str),"explicit-UTC-timestamp-required")
    d=datetime.fromisoformat(value.replace("Z","+00:00"))
    need(d.tzinfo is not None and d.utcoffset().total_seconds()==0,"UTC-timestamp-required")
    return d

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def uuid_exact(value):
    need(str(uuid.UUID(value))==value,"canonical-session-UUID")
    return value

def board_argv(core, alert, *, home, sender, current_actor, thread=None):
    need(uuid_exact(sender)==uuid_exact(current_actor),"sender-must-be-actual-current-actor")
    need(sender!=RECIPIENT,"sender-cannot-impersonate-recipient")
    need(alert["board"]==BOARD and alert["recipient"]==RECIPIENT,"fixed-Branch-route")
    need(Path(home).is_absolute(),"exact-existing-catalog-home-required")
    text=json.dumps(alert,sort_keys=True)
    need(len(text)<=8000,"normal-board-text-budget")
    argv=core.board_command(alert,python="/usr/bin/python3",board_cli=CLI,
                            catalog_home=str(home),sender=sender)
    need(len(argv[argv.index("--title")+1])<=160,"normal-board-title-budget")
    if thread is not None:
        # Existing parent-bound directed thread only; no invented thread ownership.
        need(thread["opener"]==sender and thread["recipient"]==RECIPIENT
             and thread["board"]==BOARD and type(thread["id"]) is int and thread["id"]>0,
             "existing-reply-thread-binding")
        index=argv.index("open")
        argv=argv[:index]+["reply","--session",sender,"--thread",str(thread["id"]),
                          "--kind","status","--text",text,"--cc",RECIPIENT]
    return argv

def decode_normal_cli(result, *, command, expected_thread=None):
    """Actual board_store.py:1494-1518,1198-1208. Queue state only."""
    need(not result["timed_out"] and not result.get("launch_error"),"transport-timeout-or-launch-ambiguous")
    need(result["exit_code"]==0,"board-CLI-nonzero-ambiguous")
    lines=result["stdout"].decode("utf8").splitlines()
    need(len(lines)==3 and re.fullmatch(r"[1-9][0-9]*",lines[0]),"normal-board-output-UNKNOWN")
    value=int(lines[0])
    prefix=re.fullmatch(r"board=([^ ]+) thread=([1-9][0-9]*) post=([1-9][0-9]*) (.+)",lines[1])
    need(prefix is not None and prefix[1]==BOARD,"board-report-route")
    thread,post=int(prefix[2]),int(prefix[3])
    need((command=="open" and value==thread==post) or
         (command=="reply" and post==value and thread==expected_thread),"board-post-thread-binding")
    counts={}
    for part in prefix[4].split():
        key,raw=part.split("=")
        need(key in STATES and key not in counts and re.fullmatch(r"[0-9]+",raw),"board-count-format")
        counts[key]=int(raw)
    need(set(counts) in (set(STATES),set(STATES[:-1])),"board-state-count-contract")
    match=re.fullmatch(r"notices: "+re.escape(BOARD)+r"#([1-9][0-9]*)=([a-z_]+)",lines[2])
    need(match is not None,"single-directed-notice-binding-UNKNOWN")
    state=match[2]
    need(state in ("queued","acknowledged") and counts.get(state)==1 and sum(counts.values())==1,
         "not-enqueued-or-ambiguous-delivery-state")
    # 'acknowledged' means ack-notice, not pushed model arrival.
    return {"core_receipt":{"stage":"ENQUEUED","board":BOARD,"recipient":RECIPIENT,
                            "notification_id":int(match[1])},
            "post_id":post,"thread_id":thread,"notice_state":state,
            "push_frontier":"UNKNOWN","recipient_frontier":"UNKNOWN",
            "native_exit":result["exit_code"]}

class BoardSender:
    def __init__(self, core, *, home, sender, current_actor, transport, evidence_dir,
                 runtime_env, thread=None):
        self.core=core; self.home=home; self.sender=sender; self.actor=current_actor
        self.transport=transport; self.evidence_dir=Path(evidence_dir); self.thread=thread
        need(runtime_env.get("CODEX_SESSION_ID")==sender==current_actor,"runtime-actor-binding")
        self.env=deepcopy(runtime_env)
        self.n=0

    def __call__(self, alert):
        argv=board_argv(self.core,alert,home=self.home,sender=self.sender,
                        current_actor=self.actor,thread=self.thread)
        self.n+=1
        need(re.fullmatch(r"[0-9a-f]{64}", alert["alert_id"]),"exact-alert-identity")
        area=self.evidence_dir/("send-"+alert["alert_id"])
        area.mkdir(mode=0o700)
        # Immutable send-start anchor exists BEFORE transport; never changed by receipts.
        anchor={"schema":"branch-send-anchor/v1","board":BOARD,"recipient":RECIPIENT,
                "sender":self.sender,"check_id":alert["check_id"],"alert_id":alert["alert_id"],
                "started_at":utc_now(),"monotonic_start":time.monotonic()}
        record(area/"anchor.json",anchor)
        r=self.transport.run(argv,env=self.env)
        # Record original envelope even for explicitly mocked transport fixtures.
        record(area/"result.json",
               {k:v for k,v in r.items() if k not in ("stdout","stderr")})
        # Transport must itself preserve raw streams privately before returning.
        d=decode_normal_cli(r,command="reply" if self.thread else "open",
                            expected_thread=self.thread["id"] if self.thread else None)
        record(area/"decoded.json",dict(d,anchor=anchor))
        return d["core_receipt"]

def delivery_receipt(core, queued, anchor, *, provider_push=None, recipient_reply=None,
                     qa_receipt=None, observed_at):
    """Translate independently obtained admitted evidence, not a native push claim.

    Provider/QA adapters must authenticate their evidence refs externally. We validate
    exact identity/timing/mode; this function does not authenticate arbitrary JSON.
    A manual read reply is a real reply but fails this PUSHED_ROUTE_30S contract.
    """
    record_={"schema":"branch-pushed-route-assessment/v1","verdict":"FAIL",
             "owner":RECIPIENT,"snapshot":{"anchor":deepcopy(anchor),"queued":deepcopy(queued),
             "provider_push":deepcopy(provider_push),"recipient_reply":deepcopy(recipient_reply),
             "qa_receipt":deepcopy(qa_receipt)},"reason":"pushed-route-evidence-UNKNOWN"}
    base=deepcopy(queued["core_receipt"])
    need(base["stage"]=="ENQUEUED" and base["board"]==anchor["board"]==BOARD
         and base["recipient"]==anchor["recipient"]==RECIPIENT,"send-anchor-route")
    start=stamp(anchor["started_at"]); now=stamp(observed_at)
    need(now>=start,"observation-before-immutable-send")
    if qa_receipt is None:
        return base,record_
    common={"board":BOARD,"recipient":RECIPIENT,"check_id":anchor["check_id"],
            "alert_id":anchor["alert_id"],"notification_id":base["notification_id"],
            "post_id":queued["post_id"],"thread_id":queued["thread_id"]}
    def bound(e):
        return isinstance(e,dict) and e.get("admitted") is True and e.get("evidence_ref") and all(e.get(k)==v for k,v in common.items())
    need(bound(qa_receipt),"independent-QA-binding")
    announced=stamp(qa_receipt["announced_at"])
    need(announced<=start,"test-must-be-announced-before-send")
    deadline=start.timestamp()+30
    if provider_push is not None:
        need(bound(provider_push),"provider-push-binding")
        need(provider_push.get("arrival_mode")=="native_push" and
             provider_push.get("kind")=="model_arrival","queue-or-watcher-is-not-provider-push")
        pushed=stamp(provider_push["arrived_at"])
        need(start<=pushed<=now,"push-timestamp-not-observed-or-backdated")
        core.token(provider_push["queue_message_id"])
        base.update(stage="PUSHED",queue_message_id=provider_push["queue_message_id"])
    elif qa_receipt.get("independent_model_push_observed") is True:
        need(qa_receipt.get("arrival_mode")=="native_push","QA-mode-must-be-native-push")
        pushed=stamp(qa_receipt["arrived_at"])
        need(start<=pushed<=now,"QA-push-timestamp")
        core.token(qa_receipt["queue_message_id"])
        base.update(stage="PUSHED",queue_message_id=qa_receipt["queue_message_id"])
    else:
        return base,record_
    if recipient_reply is None:
        record_["reason"]="missing-actual-recipient-reply"
        return base,record_
    need(bound(recipient_reply) and recipient_reply.get("author")==RECIPIENT,
         "actual-recipient-reply-author-and-check-binding")
    if recipient_reply.get("arrival_mode")!="native_push":
        record_["reason"]="manual-boardwatch-read-ACK-fails-pushed-route"
        return base,record_
    replytime=stamp(recipient_reply["created_at"])
    need(pushed<=replytime<=now,"reply-timestamp-not-observed-or-backdated")
    need(type(recipient_reply.get("reply_post_id")) is int and
         recipient_reply["reply_post_id"]>queued["post_id"],"actual-reply-post-identity")
    if replytime.timestamp()>deadline:
        record_["reason"]="actual-recipient-ACK-late"
        return base,record_
    need(qa_receipt.get("recipient_reply_verified") is True,"independent-QA-reply-verification")
    core.token(recipient_reply["evidence_ref"])
    base.update(stage="RECIPIENT_ACK",ack_ref=recipient_reply["evidence_ref"])
    record_.update(verdict="PASS",reason="qualified-pushed-model-arrival-and-recipient-reply-within30s",
                   elapsed_seconds=replytime.timestamp()-start.timestamp())
    return base,record_

