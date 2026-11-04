"""Runtime adapter to the shared public pool; account/receive identities stay separate."""

from contextlib import asynccontextmanager
import asyncio
import importlib.util
from pathlib import Path

from .contracts import Refusal

_path = Path(__file__).resolve().parents[2] / 'direct-child/execution_pool.py'
_spec = importlib.util.spec_from_file_location('coordinator_public_execution_pool', _path)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


class ExecutionPool:
    def __init__(self, config):
        self.authorized = config['profiles']
        self.bind_seconds = config['deadlines']['bind']
        self.pool = _module.Pool(config.get('execution_pool_routes', _module.DEFAULT_ROUTES))

    def allocate(self):
        try:
            return self.pool.allocate(self.authorized, blocking=False)
        except _module.PoolError as exc:
            raise Refusal(str(exc)) from exc

    def status(self):
        try:
            value = self.pool.status(blocking=False)
            self.pool.eligible(value['enabled'], self.authorized)
            return value
        except _module.PoolError as exc:
            return {'state': 'held', 'error': str(exc), 'routes': str(self.pool.routes), 'availability': 'not-probed'}

    @asynccontextmanager
    async def admission(self, profile):
        # Never block this event loop on a flock held across another spawn's
        # await. Busy admissions wait only within the existing bind budget.
        deadline = asyncio.get_running_loop().time() + self.bind_seconds
        while True:
            guard = self.pool.admission(profile, self.authorized, blocking=False)
            try:
                witness = guard.__enter__()
                break
            except _module.PoolBusy as exc:
                if asyncio.get_running_loop().time() >= deadline:
                    raise Refusal(str(exc)) from exc
                await asyncio.sleep(.01)
            except _module.PoolError as exc:
                raise Refusal(str(exc)) from exc
        try:
            yield witness
        finally:
            guard.__exit__(None, None, None)
