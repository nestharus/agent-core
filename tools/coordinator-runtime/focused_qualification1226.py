"""Focused recorder for coordinator and continuing-review fictional controls.

The original conservation recorder owns pre-close physical bytes and separate
logical readbacks. This entry adds the shared test location to assertion tracing;
it never discovers tests or runs a provider.
"""
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parents[1]/'direct-child'))
import focused_qualification1216 as base


class Recorder(base.Recorder):
    def trace(self, frame, event, arg):
        if self.current is None:
            return self.trace
        path = frame.f_code.co_filename
        prefixes = ('/src/tools/coordinator-runtime/tests/', '/src/tools/direct-child/')
        prefix = next((p for p in prefixes if path.startswith(p)), None)
        if event == 'line' and prefix:
            self.current['lines'].setdefault(path[len('/src/tools/'):], set()).add(frame.f_lineno)
        if event == 'call' and prefix and frame.f_code.co_name == self.current['id'].split('.')[-1]:
            self.current['body_entered'] = True
        if event == 'call' and frame.f_code.co_name.startswith('assert'):
            caller = frame.f_back
            if caller and any(caller.f_code.co_filename.startswith(p) for p in prefixes):
                self.current['assertions'].append(dict(method=frame.f_code.co_name,
                    file=caller.f_code.co_filename[len('/src/tools/'):], line=caller.f_lineno))
        return self.trace


if __name__ == '__main__':
    os.environ['REVIEW_FIXTURE_ROOT'] = '/fixtures'
    os.environ['ONEOFF1077_FIXTURES'] = '/fixtures'
    base.Recorder = Recorder
    raise SystemExit(base.main())

