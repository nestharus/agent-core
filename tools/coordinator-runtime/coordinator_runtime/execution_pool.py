"""Runtime adapter to the shared public pool; account/receive identities stay separate."""

from contextlib import asynccontextmanager
import asyncio
import importlib.util
from pathlib import Path

from .contracts import Refusal

def public_pool_module():
    # Ordinary runtime fallback. Invocation callers instead inject the Pool
    # compiled from their admitted bytes; importing this adapter has no loader.
    path = Path(__file__).resolve().parents[2] / 'direct-child/execution_pool.py'
    spec = importlib.util.spec_from_file_location('coordinator_public_execution_pool', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ExecutionPool:
    def __init__(self, config, runtime=None, *, pool=None, pool_module=None, expected_control=None):
        self.runtime, self.expected_control = runtime, expected_control
        self.authorized = config['profiles']
        self.bind_seconds = config['deadlines']['bind']
        self.pool_module = public_pool_module() if pool_module is None else pool_module
        self.pool = self.pool_module.Pool(config.get('execution_pool_routes', self.pool_module.DEFAULT_ROUTES)) if pool is None else pool

    def control(self):
        from .configuration import selected
        transition = selected(self.runtime) if self.runtime is not None else None
        return transition['basis']['release']['pool_control'] if transition else self.expected_control

    def allocate(self):
        try:
            return self.pool.allocate(self.authorized, blocking=False, expected_control=self.control())
        except self.pool_module.PoolError as exc:
            raise Refusal(str(exc)) from exc

    def status(self):
        try:
            value = self.pool.status(blocking=False, expected_control=self.control())
            self.pool.eligible(value['enabled'], self.authorized)
            return value
        except self.pool_module.PoolError as exc:
            return {'state': 'held', 'error': str(exc), 'routes': str(self.pool.routes), 'availability': 'not-probed'}

    @asynccontextmanager
    async def admission(self, profile):
        # Never block this event loop on a flock held across another spawn's
        # await. Busy admissions wait only within the existing bind budget.
        deadline = asyncio.get_running_loop().time() + self.bind_seconds
        while True:
            guard = self.pool.admission(profile, self.authorized, blocking=False, expected_control=self.control())
            try:
                witness = guard.__enter__()
                break
            except self.pool_module.PoolBusy as exc:
                if asyncio.get_running_loop().time() >= deadline:
                    raise Refusal(str(exc)) from exc
                await asyncio.sleep(.01)
            except self.pool_module.PoolError as exc:
                raise Refusal(str(exc)) from exc
        try:
            yield witness
        finally:
            guard.__exit__(None, None, None)
