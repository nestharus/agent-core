# Same-authority source repair v1

Actual current Work may select **one** stopped, same-journal code repair for an
existing continuing capability. This distinct protocol is implemented inside
`report_repair.py`, reusing its schema loader, currentness hooks and original-stop
checker. It adds no production module or import-acquisition footprint. The
legacy collected-report API retains its separate schema and source restrictions;
the two repair protocols cannot stack on one capability.

Work selects the exact changed subset of these eight public modules:
`configuration.py`, `integration.py`, `integration_management.py`,
`resource_scopes.py`, `cli.py`, `report_repair.py`, `local_integration.py`, and
`store.py`. Both release-file and implementation hashes must agree on
every module before and after. Module/dependency addition or removal, a changed
release location, and any other changed release file are refused. Templates,
task definitions, policy, provider/SDK/scheduler sources, static dependencies,
configured ceilings and public hot-pool control identity remain bound to their
original pins. Membership continues to be user-controlled by the supported hot
control; v1 does not select a provider allocation or a fixed pool.

The immutable append-only `same_authority_source_repairs_v1` row changes only the
code pins accepted by currentness. It retains the same capability, selection,
configuration version, original four stopped software grants, source positions,
admissions, report receipts, prospective epoch and every original duty. It never
restamps an input or changes an admission/report policy hash. It records the
start count and finite selections at the repair point without resetting charges
or extending time. Current software and launch checks continue enforcing the
original finite windows and resource/association gates.

Basis capture acquires metadata for only one to thirty-two explicit queued,
unheld, unprocessed inputs with `job IS NULL` and no frozen job membership. It
accepts genuine future Board sources, whole Work-attributed report inputs, and
already-selected retained Board inputs with their exact original mapping pins.
It excludes internal producer/delivery sources and historical unselected inputs.
Packaged Board input requires its original same-capability immutable software
admission/resolution. Source bodies are not read during basis capture. The
owner-selected application installs the proposed pins in one journal
transaction, checks full current source bytes and existing Board/report and
admission authority, and rolls back the repair on any failure. The source row,
admission, queue and receipt remain untouched. There is no cross-Board atomicity
or protection against a noncooperating external source writer; ordinary launch
checks still revalidate actual rights.

The service must be off with its cooperative lock available. Every original
controller of that same capability must have returned and have its actual
parent-collected numeric END recorded through `processing-release`; every owned
attempt must be collected. Evidence strings attest to Work's asserted facts;
synthetic tests, model DONE, file existence and inferred liveness do not
authenticate an actual stop or parent collection.

The normal sequence, performed by the actual owner after review, is:

1. Authenticate `processing-service-control CAP stop` with the unchanged
   configuration. Collect the **same** original foreground handle to numeric
   END. Record its original `processing-release`; do not revoke or reissue the
   capability/epoch. Retain uncertainty or incomplete original collectors.
2. Install the exact reviewed merged public files at the same selected release
   location. No source supplier may perform this step against an actual service.
3. With the current configuration, call
   `same-authority-source-repair-basis CAP EVENT... --controller ORIGINAL
   --module MODULE --module MODULE --purpose 'current explicit Work purpose'`.
   Events and module names must be distinct and sorted. The command holds the
   cooperative stop lock and a journal transaction. It does not select a repair.
4. Review every returned pin and source anchor. Supply a selection with exact
   keys `schema`, `basis`, `authority`, `evidence`, where both schemas are
   `same-authority-source-repair-v1`, `basis` is the unchanged returned object,
   and authority/evidence contain the actual Work decision and complete review
   and qualification references. Apply with
   `select-same-authority-source-repair --selection REVIEWED.json`. Stale pins,
   changed sources, grants, counters, admissions, mappings or epochs refuse.
5. Perform any independently authorized paused management with its own precise
   operation selection. Code-release resolution works without a processing
   Access object, including while ordinary Work enrollment is stopped. This
   gives no processing mutation authority or broader record-read permission.
6. Restart through the existing `processing-service CAP` command under the same
   capability. It creates a new actual controller with its own collection duty;
   it inherits neither an old collector identity nor renewed finite windows.

The application receipt has `schema`, `capability`, `configuration`,
`selection_hash`, `repair_hash`, exact `sources` (`event`, `hash`, `queue`),
`producer_replay: false`, `authority_renewed: false`, and `acceptance: null`.
An identical request is idempotent after consumption: it checks current pins
without rereading or requeuing the original inputs. A different request refuses.
Queued permission is not schedulability, native execution, Root association
acceptance, downstream processing completion or permission to waive effects.
An expired report policy/epoch remains expired. Recovery outside this finite
repair point needs a separately authorized design; v1 is not a migration service.
