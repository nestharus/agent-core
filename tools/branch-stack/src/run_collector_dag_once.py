"""Frozen neutral input replay only; no acquisition, sender, Git or scheduler."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from adapter_support import load_core
from collector_dag_adapter import ACCOUNT, foreground_check, OwnerBindings

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("core","bundle","expected-snapshot-id","repo","binding","runtime","check-id"):
        parser.add_argument("--"+name,required=True)
    parser.add_argument("--max-age",type=int,default=300)
    parser.add_argument("--expected-code-version",required=False)
    parser.add_argument("--owner-bindings",help="Explicit scope facts; no inferred logical edges")
    args=parser.parse_args(argv)
    # Source and neutral input must already be kernel RO. Only a distinct fresh
    # runtime output is writable, never an existing taskhome/journal namespace.
    core=load_core(Path(args.core))
    bundle=core.load_json(args.bundle)
    runtime=Path(args.runtime)
    core.require(runtime.is_absolute(),"absolute-fresh-runtime")
    runtime.mkdir(mode=0o700)  # Preserve previous output on retry.
    captures=runtime/"producer-envelopes";captures.mkdir(mode=0o700)
    owner_bindings=None
    if args.owner_bindings:
        owner_bindings=OwnerBindings(**core.load_json(args.owner_bindings))
    result=foreground_check(core,bundle,account=ACCOUNT,repo=args.repo,binding=args.binding,
          expected_snapshot_id=args.expected_snapshot_id,
          now=datetime.now(timezone.utc).isoformat(),capture_dir=captures,
          journal_path=runtime/"existing-core-journal.json",lock_path=runtime/"existing-core-owner.lock",
          owner=ACCOUNT["session"],check_id=args.check_id,max_age=args.max_age,sender=None,
          expected_code_version=args.expected_code_version,owner_bindings=owner_bindings)
    (runtime/"result.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"status":result["status"],"frontiers":result.get("frontiers",[]),
          "delivery":result["delivery"],"native_effects":False,"installed":False},sort_keys=True))
    # Structured evaluation is complete; uncertainty is a distinct process result.
    return 4 if result["status"]=="INDETERMINATE" else 0

if __name__=="__main__":
    raise SystemExit(main())
