"""Bounded unified-method definitions; references are not executable imports.

This is an opt-in consumer interpretation of the public unified procedure.
Unknown local Markdown links are required, never silently omitted. A changed
provider relationship therefore fails closed until its meaning is examined.
"""
import hashlib
import posixpath
import re
from pathlib import Path
from urllib.parse import urlsplit, unquote

from .contracts import Refusal
from .custody import read_file

VERSION = 'unified-definitions-v1'

# This version incorporates all nine families and 27 constituent definitions.
REQUIRED_DEFINITIONS = frozenset({
    'agent-definition-risk-reviewer.prompt.md',
    'authority/allocation-enforcement-risk.prompt.md',
    'authority/shared-outcome-risk.prompt.md',
    'continuity/availability-capacity-risk.prompt.md',
    'continuity/lifecycle-obligation-risk.prompt.md',
    'continuity/scaling-headroom-risk.prompt.md',
    'continuity/state-analyzability-risk.prompt.md',
    'continuity/transition-legality-risk.prompt.md',
    'evidence/domain-representation-risk.prompt.md',
    'evidence/evidence-producer-admission-continuity-risk.prompt.md',
    'evidence/experiment-discrimination-risk.prompt.md',
    'evidence/implementation-identity-risk.prompt.md',
    'families/agent-reasoning-integrity.prompt.md',
    'families/authority-and-enforcement.prompt.md',
    'families/claim-and-evidence-validity.prompt.md',
    'families/cross-change-understanding.prompt.md',
    'families/local-behavior-and-continuity.prompt.md',
    'families/operational-evidence-capabilities.prompt.md',
    'families/organization-and-communication.prompt.md',
    'families/purpose.prompt.md',
    'families/service-capability-and-headroom.prompt.md',
    'operational-evidence/adversarial-activity-reconstruction-risk.prompt.md',
    'operational-evidence/authority-exercise-accountability-risk.prompt.md',
    'operational-evidence/causal-operation-reconstruction-risk.prompt.md',
    'operational-evidence/longitudinal-outcome-validation-risk.prompt.md',
    'operational-evidence/service-health-inference-risk.prompt.md',
    'operational-evidence/telemetry-integrity-survivability-risk.prompt.md',
    'organization/convention-evolution-risk.prompt.md',
    'organization/entity-identity-risk.prompt.md',
    'organization/inter-application-communication-risk.prompt.md',
    'organization/internal-protocol-layer-risk.prompt.md',
    'organization/relationship-choreography-risk.prompt.md',
    'organization/structural-variation-risk.prompt.md',
    'organization/utilitarian-intent-risk.prompt.md',
    'outcome/premise-risk.prompt.md',
    'synthesis/change-set-coherence-risk.prompt.md',
})


def require_definitions(entry, found):
    home = Path(entry).parent
    missing = sorted(str(home / p) for p in REQUIRED_DEFINITIONS if str(home / p) not in found)
    if missing:
        raise Refusal("required unified definitions missing: " + ", ".join(missing))

# Exact reference edges, from the public procedure's selection/optional prose.
# These do not incorporate the alternate cohort, optional adapters, evaluation
# records, contributing lifecycle or model calibration into ordinary review.
REFERENCES = {
    'unified-reviewer.prompt.md': {'coverage-preserving-review-candidate.md'},
    'semantic-review-contract.md': {
        'manual/README.md', 'manual/coordinator.prompt.md',
        'coverage-preserving-review-candidate.md', '../methods/evidence-to-change.md',
        '../docs/model-calibration.md', 'ecosystem-contract-context.md', '../docs/evaluation-cadence.md'},
    'adjacent-work-tracking-contract.md': {
        '../methods/evidence-to-change.md', 'coverage-preserving-review-candidate.md'},
    'decision-semantics.md': {'coverage-preserving-review-candidate.md'},
    'review-dimensions.md': {'coverage-preserving-review-candidate.md'},
    'families/procedure.md': {'coverage-preserving-review-candidate.md'},
    'manual/change-aware-reuse.md': {'coverage-preserving-review-candidate.md'},
    'families/claim-and-evidence-validity.prompt.md': {'ecosystem-contract-context.md'},
    'review-scope-adapter-contract.md': {'ecosystem-contract-context.md', 'coverage-preserving-review-candidate.md'},
}


def files(entry, exclusions=()):
    """Return complete required pins within 128 files/1MiB, before any model.

    Bounds are acquisition bounds for this compiler, not model/context limits.
    No reference target is stat'ed. Exclusions apply before each acquisition.
    """
    entry = Path(entry)
    if (not entry.is_absolute() or '..' in entry.parts or entry.name != 'unified-reviewer.prompt.md'
            or any(p.startswith('.') or p in {'runs', 'AGENTS.md', 'WORK_LOG.md'} for p in entry.parts)):
        raise Refusal('unified closure requires its exact absolute entry name')
    home = entry.parent
    pending, found, total = [entry], {}, 0
    while pending:
        path = pending.pop()
        if str(path) in found:
            continue
        # Lexical checks precede read_file's no-follow metadata/body walk.
        if (not path.is_relative_to(home) or path.name in {'AGENTS.md', 'WORK_LOG.md'}
                or any(p in {'runs', '.git'} or p.startswith('.') for p in path.relative_to(home).parts)
                or any(path == Path(p) or path.is_relative_to(Path(p)) for p in exclusions)):
            raise Refusal('method dependency outside authorized public definitions before acquisition')
        if len(found) >= 128 or total >= 1024 * 1024:
            raise Refusal('method closure exceeds bounded definition acquisition')
        try:
            body, _ = read_file(path, min(256 * 1024, 1024 * 1024 - total))
            source = body.decode('utf-8')
        except (OSError, UnicodeError) as exc:
            raise Refusal('required public method dependency unavailable: ' + str(path)) from exc
        total += len(body)
        found[str(path)] = hashlib.sha256(body).hexdigest()
        current = path.relative_to(home).as_posix()
        # Fenced examples do not introduce Markdown imports.
        source = re.sub(r'^```[^\n]*\n.*?^```[^\n]*$', '', source, flags=re.M | re.S)
        for target in re.findall(r'\[[^\]\n]+\]\(([^)\s]+)\)', source):
            url = urlsplit(target)
            if url.scheme or url.netloc:
                if url.scheme in {'https', 'http'} and url.netloc and not url.username and not url.password:
                    continue  # Public citation only, never network/local acquisition.
                raise Refusal('malformed or non-public method link refused')
            value = unquote(url.path)
            if not value:
                continue  # Same-document anchor.
            if (value.startswith('/') or '\\' in value or '%' in value or '\x00' in value
                    or url.query or ':' in value):
                raise Refusal('malformed/absolute method dependency refused before acquisition')
            relative = posixpath.normpath(posixpath.join(posixpath.dirname(current), value))
            if relative in REFERENCES.get(current, set()):
                continue
            if relative.startswith('../') or relative in {'..', '.'}:
                raise Refusal('required provider dependency outside selected public method home: ' + relative)
            if Path(relative).suffix != '.md':
                raise Refusal('unsupported required method dependency: ' + relative)
            pending.append(home / relative)
    return found
