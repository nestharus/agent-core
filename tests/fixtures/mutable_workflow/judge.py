"""Fake judgment actor consumes caller handoff, not engine internals."""
import base64
import json
import sys

handoff = json.load(sys.stdin)
state = handoff['current']
attempt = handoff['output']
result = attempt['output']['result']
assert result['outcome'] == 'failure'
assert 'missing local prerequisite: seed' in result['detail']
assert 'missing local prerequisite: seed' in base64.b64decode(attempt['output']['stdout_b64']).decode()
print(json.dumps(dict(run_id=state['run_id'], cursor=state['cursor'],
                     blocked_step=state['steps'][state['position']]['id'],
                     actor='fake-judgment-actor', reason=result['detail'],
                     insert=[dict(id='unplanned-recovery', worker='local', input='recover')])))
