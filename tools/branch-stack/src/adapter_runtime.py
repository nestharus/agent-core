"""Foreground adapter/core bridge. No scheduler, registration or installation."""
from copy import deepcopy
from adapter_support import need
from feed_adapter import apply_on_encounter

def check_once(core, feed_result, *, journal_path, lock_path, owner, check_id,
               sender=None, deferral_projection=None, triggers=None,
               deferral_capability="rfq.branch-deferral-eligibility-projection/1",
               work_decision=None, work_owner=None):
    """Use the existing canonical owner flock and core journal for one occurrence.

    Caller owns startup freezing, actual account/state binding and source admission.
    A decoder frontier cannot be recast as a healthy check. No native effects occur.
    """
    need(feed_result.get("schema")=="branch-adapter-result/v1","typed-adapter-result-required")
    if feed_result.get("snapshot") is None:
        return {"schema":"branch-adapter-check/v1","status":"UNKNOWN",
                "frontiers":deepcopy(feed_result.get("frontiers",[])),
                "delivery":"UNSUPPORTED_INCOMPLETE_CORE_BINDING","installed":False,
                "native_effects":False,"owner":owner}
    snapshot=deepcopy(feed_result["snapshot"])
    policy=None
    if deferral_projection is not None:
        policy=apply_on_encounter(core,snapshot,deferral_projection,triggers=triggers or {},
                                 capability=deferral_capability,work_decision=work_decision,
                                 work_owner=work_owner)
        snapshot=policy["snapshot"]
    frontiers=deepcopy(feed_result.get("frontiers",[]))+(policy["frontiers"] if policy else [])
    # This exact marker describes the intentionally bounded inventory, not a gap
    # in an encountered unit. All other unresolved decoder/policy frontiers count.
    unresolved=[f for f in frontiers if f != "outside-explicit-pr-scope-UNKNOWN"]
    with core.owner_lock(lock_path,owner,journal_path=journal_path) as lock_fd:
        journal=core.DeliveryJournal(journal_path,lock_fd=lock_fd)
        accepted=journal.accept(snapshot,check_id,context={
            "feed":feed_result,"policy":policy,"owner":owner})
        prepared=accepted["plan"]; notices=accepted["alerts"]
        persistence=accepted["persistence"]
        row=accepted["delivery"]
        if sender is not None and not accepted["replayed"] and persistence["durability"] == "CONFIRMED":
            try:
                row=journal.deliver(check_id,notices,prepared["plan_id"],sender)
            except core.JournalDurabilityUnconfirmed:
                row=journal.receipt(check_id)
            persistence=deepcopy(journal.persistence)
    return {"schema":"branch-adapter-check/v1",
            "status":("INDETERMINATE" if persistence["durability"] != "CONFIRMED" else
                      ("UNKNOWN" if unresolved else ("VIOLATION" if notices else "HEALTHY_WITHIN_EXPLICIT_SCOPE"))),
            "acceptance":persistence["outcome"],"persistence":persistence,
            "known_violations":bool(notices),"replayed":accepted["replayed"],
            "plan":prepared,"alerts":notices,"delivery":row,"owner":owner,
            "event_ids":deepcopy(feed_result.get("event_ids",[])),
            "frontiers":frontiers,
            "transport_bound":sender is not None,"installed":False,"native_effects":False}

def native_operation_dto(core, snapshot, *, mode, unit=None):
    """Existing native operation DTO only. Parent owns capability/CAS/effects."""
    result=core.native_contract(snapshot,mode,unit)
    return dict(result,actual_effects_owner="parent-Branch",
                capability_frontier="parent-qualified-native-operation-and-CAS-required")

