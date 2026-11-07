# Release-validation latency

Release validation compiles current lexical exclusion paths into a set of path
component tuples once per synchronous `release()` invocation. Each candidate
path checks its component prefixes against that set before alias metadata or
source bytes are acquired. The module directory is also guarded before glob
enumeration. Component matching preserves `Path` ancestry, including the
distinct POSIX `/` and `//` roots and sibling names that share a text prefix.

The set is derived only from that invocation's current `artifact_exclusions`
and supported profile paths under the current home. It is discarded on return
or failure; a direct `_path()` call constructs its own set. There is no
cross-call key, accepted-release marker, TTL or cached validation outcome.
Every call still checks all aliases, hashes every source file, verifies the
retention closure, reads the exact operator configuration and public pool
control, and compares the complete release pins. Processing still checks the
current configuration, capability/revocation, implementation and applicable
role, task, source, mapping, actor, grant and effect authority. Pool membership
remains user-controlled and is read again at allocation and admission.

This removes repeated lexical preparation and exclusion scans, rather than
reusing source hashes or permissions. It keeps the existing cooperative
filesystem assumptions: sequential checks are not a multi-file atomic snapshot,
physical isolation or protection against a hostile writer changing paths
between guard and read. A mutation during a call remains subject to the
existing source-pin comparisons and downstream boundaries. No lock, timeout,
capacity, conflict recovery or execution-completion policy is changed.

In fresh isolated fixtures, the same four-role wake/classification/ACK workload
with 56 exclusions and 82 release files performed 181 release checks before and
after this change. Median repeated `Access.current()` fell from 97.4 ms to
9.8 ms; four-role wake through durable classification and ACK fell from
17.819 s to 2.157 s. All full source hashes were still read at each boundary.
These measurements use synthetic SDK principals, a synthetic transition row
and deterministic classifier returns. They do not measure provider latency or
prove actual semantic role responses. Parent-owned operations and the actual
32-second retest remain separate.

`tests/test_validation_latency668.py` runs with a fresh writable `/fixtures`,
read-only selected source at `/src`, no actual home, and empty network/PID
namespaces. Its service-loop test retains the existing three-second fixture
bound and disables only product task scheduling, automatic cleanup and external
custodian work. Source/currentness/wake/intake/classification/ACK run through
production code. Adverse tests cover source/template/provider/config drift,
same-size rewrites with restored mtime, identical-byte inode replacement,
parent aliases, new exclusions before metadata/enumeration, revoked grants and
capabilities, and membership changes between allocation and admission. Focused
existing tests separately exercise genuine fixture configuration selection,
current source/task/mapping/actor checks and the hot pool control API.
