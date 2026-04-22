# FastAPI Best Practices Reference

Purpose: opinionated reviewer reference for pull requests.
Audience: reviewers who already know FastAPI and need a fast "is this right?" anchor.
Mode: checklist, not tutorial.

Baseline sources used for this reference:
- FastAPI official docs on dependencies, bigger applications, middleware, lifespan, testing, async tests, SQL/session dependencies, and security scopes.
- Pydantic official docs on `ConfigDict`, validators, serialization, aliases, and the v1-to-v2 migration.
- SQLAlchemy official docs on `Session` scope and `AsyncSession` behavior.
- Community guide: `zhanymkanov/fastapi-best-practices`.
- Primary repo reference: `github.com/nestharus/ai-workflow`, branch `init`, directory `app/`.

How to use this document:
- Treat sections 1-14 as general reviewer guidance.
- Treat section 15 as org-specific conventions observed in `ai-workflow`.
- If a topic is contested, this document picks one reviewer anchor on purpose.

General reviewer stance:
- Prefer explicit contracts over cleverness.
- Prefer short dependency chains over hidden globals.
- Prefer service-owned business logic over router-owned workflows.
- Prefer repository-owned persistence over ORM/session use in routers.
- Prefer boring, testable lifecycle and error handling over framework magic.

## 1. Project Structure & Layered Architecture

Scope:
- Controllers or routers are HTTP adapters.
- Services own use-case and business rules.
- Repositories own persistence concerns.
- Schemas or contracts own API I/O shape.
- Core owns settings, app factory, middleware, and cross-cutting wiring.

### DO
- Split transport, business logic, and persistence into different modules.
  Why: reviewers can locate ownership fast and reason about change impact.
- Keep routers thin and declarative.
  Why: route handlers should map HTTP to use-case calls, not execute workflows.
- Put orchestration and business decisions in services.
  Why: services are easier to test without HTTP or database machinery.
- Put SQL, ORM, or driver-specific code in repositories.
  Why: persistence changes should not force router or service rewrites.
- Use request and response schemas that are separate from persistence models.
  Why: API contracts change at a different rate than tables and ORM entities.
- Keep dependency direction one-way: router -> service -> repository -> infrastructure.
  Why: upward imports or callbacks create cycles and hidden coupling.
- Centralize app assembly in an application factory.
  Why: reviewers can verify middleware, routers, handlers, and lifespan in one place.
- Put framework-agnostic domain exceptions in a core or domain package.
  Why: services should not need FastAPI imports to signal domain failure.
- Make cross-cutting concerns explicit modules: settings, middleware, exceptions, dependencies.
  Why: reviewers should not have to hunt through endpoints for app-wide behavior.

### DON'T
- Don't place business logic directly in route handlers.
  Why: HTTP details leak into use-case code and the handler becomes hard to unit test.
- Don't let repositories return raw driver responses to routers.
  Why: transport ends up depending on storage-specific shapes and metadata.
- Don't import FastAPI primitives deep into service or repository code without need.
  Why: it destroys portability and makes unit tests framework-aware for no reason.
- Don't expose ORM models directly as API responses.
  Why: you leak internal columns, lazy fields, and persistence semantics into the contract.
- Don't let services reach into `request`, `app.state`, or `Depends()` directly.
  Why: dependency injection stops being explicit and reviewers lose traceability.
- Don't use one giant `main.py` for routers, settings, middleware, handlers, and models.
  Why: changes become noisy and ownership boundaries vanish.
- Don't let repositories perform unrelated side effects like email, cache invalidation, or auth checks.
  Why: persistence boundaries become muddled and transaction semantics get unclear.
- Don't create "utils" dumping grounds for logic that really belongs to a service or repository.
  Why: reviewers cannot tell whether changes affect HTTP, domain rules, or storage.
- Don't build circular dependency graphs between layers.
  Why: they are a strong signal that responsibilities are misplaced.

### Right
```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel

class In(BaseModel): text: str
class Out(BaseModel): text: str
class Service:
    async def run(self, text: str) -> Out: return Out(text=text.upper())
def get_service() -> Service: return Service()
router = APIRouter()
@router.post("/messages", response_model=Out)
async def create_message(payload: In, svc: Service = Depends(get_service)) -> Out:
    return await svc.run(payload.text)
```

### Wrong
```python
from fastapi import APIRouter

router = APIRouter()
_storage: dict[str, str] = {}
@router.post("/messages")
async def create_message(text: str) -> dict[str, str]:
    key = str(len(_storage) + 1)
    _storage[key] = text.upper()
    return {"id": key, "text": _storage[key]}
```

### Reviewer Red Flags
- Router imports `Session`, `engine`, ORM models, or driver clients directly.
  Why it matters: transport and persistence are collapsing into one layer.
- Services import `Request`, `Response`, `HTTPException`, or `APIRouter`.
  Why it matters: business logic has become HTTP-coupled.
- Repositories call other services.
  Why it matters: dependency direction is inverted and transactions become ambiguous.
- Response models mirror tables one-for-one without review.
  Why it matters: this often leaks internal fields and blocks API evolution.
- A module-level dict or list is used as "temporary state" in production code.
  Why it matters: this is hidden process-local state, not architecture.
- A PR adds logic to `main.py` because it was "easy".
  Why it matters: assembly code is becoming an application layer dumping ground.

### Convention Observed in ai-workflow
- Convention observed in `ai-workflow`: app assembly is centralized in `create_app(settings)`.
  File reference: `app/core/factory.py:190-217`.
- Convention observed in `ai-workflow`: HTTP wiring lives under versioned API packages.
  File reference: `app/api/v1/router.py:1-8`.
- Convention observed in `ai-workflow`: route handlers depend on typed aliases like `ExampleServiceDep`.
  File reference: `app/api/v1/dependencies.py:105-126`.
- Convention observed in `ai-workflow`: service classes accept repositories and settings in the constructor.
  File reference: `app/services/example_service.py:44-56`.
- Convention observed in `ai-workflow`: repository classes accept infrastructure clients in the constructor.
  File reference: `app/repositories/example_repository.py:74-82`.
- Convention observed in `ai-workflow`: API schemas live in `contracts`, not in repositories or endpoints.
  File reference: `app/contracts/example_contract.py:38-112`.

## 2. FastAPI Framework Idioms

Scope:
- `FastAPI` is the application container.
- `APIRouter` is the composition unit for endpoints.
- Function signatures define request inputs.
- Decorator metadata defines contract and docs behavior.

### DO
- Use `APIRouter` per bounded route group and include routers from a central place.
  Why: router registration stays predictable and reviewable.
- Put `prefix`, `tags`, shared `dependencies`, and `responses` at router inclusion points when appropriate.
  Why: shared policy is easier to audit at one boundary than repeated per endpoint.
- Declare `response_model` on routes that return structured data.
  Why: output filtering and docs stay aligned with the public contract.
- Declare `status_code` explicitly for non-default success responses.
  Why: reviewers should not infer semantics from implementation details.
- Use `Query`, `Path`, `Header`, `Cookie`, `Body`, and `Form` to make HTTP intent explicit.
  Why: validation and docs become first-class instead of accidental.
- Use `Annotated[...]`-style dependency aliases in larger codebases.
  Why: route signatures stay readable without losing typing.
- Keep route summaries, descriptions, and error response metadata accurate.
  Why: reviewers should treat OpenAPI as part of the product.
- Prefer `lifespan=` over deprecated startup or shutdown events.
  Why: FastAPI now anchors lifecycle around lifespan context managers.
- Keep unversioned root routes narrow and deliberate, such as liveness.
  Why: most application behavior should live behind versioned routers.

### DON'T
- Don't mount large endpoint groups directly on the app object in random files.
  Why: registration order and shared configuration become opaque.
- Don't omit `response_model` for convenience when the route has a stable schema.
  Why: output filtering and docs drift immediately.
- Don't rely on implicit parameter sources when review clarity matters.
  Why: `item_id: int` is obvious for path only if the decorator path and name still match.
- Don't mix router-local and app-local registration without a reason.
  Why: reviewers cannot tell which URLs are canonical and which are special cases.
- Don't keep using `@app.on_event("startup")` in new code.
  Why: FastAPI recommends lifespan and warns that lifespan and events should not be mixed.
- Don't overload route handlers with custom OpenAPI mutations unless the public contract demands it.
  Why: docs customizations create maintenance cost and often hide schema issues.
- Don't use ambiguous names like `data`, `payload`, and `body` for every parameter.
  Why: reviewers need semantics, not filler names.
- Don't return bare dicts for complex success responses when a schema exists.
  Why: contract validation is lost exactly where it matters most.
- Don't make route metadata lie.
  Why: wrong status codes or responses in decorators are reviewer-visible contract bugs.

### Right
```python
from fastapi import APIRouter, Query

router = APIRouter(prefix="/reports", tags=["reports"])
@router.get("/", response_model=list[str], status_code=200)
async def list_reports(page: int = Query(1, ge=1)) -> list[str]:
    return [f"page:{page}"]
```

### Wrong
```python
from fastapi import FastAPI

app = FastAPI()
@app.get("/reports")
async def list_reports(page=1):
    return {"page": page, "items": ["x"]}
```

### Reviewer Red Flags
- Endpoints are registered in multiple files with no single router aggregator.
  Why it matters: route discovery, auth policy, and versioning become error-prone.
- `response_model` is absent on most routes even though DTOs exist.
  Why it matters: the app is no longer enforcing its public response contract.
- Query or path constraints are buried in ad hoc `if` statements.
  Why it matters: reviewers should expect framework-level validation, not manual checks everywhere.
- New code uses `@app.on_event("startup")`.
  Why it matters: that is legacy lifecycle style for new FastAPI code.
- Route descriptions mention statuses or shapes that decorator metadata does not declare.
  Why it matters: docs are already lying before merge.
- One route returns multiple success shapes without a declared union or documented reason.
  Why it matters: clients and reviewers cannot know the real contract.

### Convention Observed in ai-workflow
- Convention observed in `ai-workflow`: a central `api_router` includes endpoint modules and applies prefixes and tags there.
  File reference: `app/api/v1/router.py:5-8`.
- Convention observed in `ai-workflow`: the full API router is included with a version prefix from settings.
  File reference: `app/core/factory.py:207-208`.
- Convention observed in `ai-workflow`: routes declare `response_model`, summaries, descriptions, and `responses`.
  File reference: `app/api/v1/endpoints/example.py:24-139`.
- Convention observed in `ai-workflow`: there is both a versioned readiness route and an unversioned liveness route.
  File reference: `app/api/v1/endpoints/health.py:19-54`, `app/core/factory.py:212`.
- Convention observed in `ai-workflow`: the app uses `lifespan=_lifespan(settings)` instead of startup/shutdown events.
  File reference: `app/core/factory.py:199-205`.

## 3. Dependency Injection

Scope:
- FastAPI DI is request-scoped wiring, not a service locator excuse.
- `Depends()` should assemble collaborators, not hide global state.
- Dependency trees are part of the public architecture.

### DO
- Use dependencies to provide request-scoped collaborators such as sessions, current user, and service instances.
  Why: construction stays explicit and overridable in tests.
- Prefer small provider functions that each do one construction step.
  Why: reviewers can follow the dependency graph without reading a mini framework.
- Use `Annotated[T, Depends(...)]` aliases when the same dependency appears across many routes.
  Why: signatures stay readable and type-aware.
- Distinguish framework-facing providers from framework-agnostic providers.
  Why: not every dependency helper should require `Request`.
- Put provider functions near the boundary they serve.
  Why: versioned HTTP dependencies can evolve separately from domain wiring.
- Use dependencies with `yield` for managed resources that need cleanup.
  Why: FastAPI guarantees the teardown order for the dependency tree.
- Keep dependencies pure in meaning: either fetch context, build a collaborator, or enforce policy.
  Why: reviewers should not see unrelated work hidden in a DI function.
- Override dependencies in tests via `app.dependency_overrides`.
  Why: that is the framework-supported replacement hook.
- Cache immutable settings providers carefully.
  Why: config objects are good singleton candidates; request data is not.

### DON'T
- Don't use dependencies as a backdoor to reach global mutable objects.
  Why: the DI signature becomes decorative and the real source of truth is hidden.
- Don't perform unrelated business logic in provider functions.
  Why: provider execution becomes surprising and hard to test.
- Don't create giant provider functions that build half the app.
  Why: reviewers lose the DI graph and test overrides become coarse.
- Don't hide request-bound resources behind module-level singletons.
  Why: cleanup, concurrency, and test isolation all degrade.
- Don't inject repositories directly into every route if the route should call a use-case service.
  Why: service boundaries disappear.
- Don't depend on import-time side effects to initialize dependencies.
  Why: tests, scripts, and background entry points become fragile.
- Don't forget to clear dependency overrides after tests.
  Why: leaked overrides create false positives and non-deterministic failures.
- Don't use `Depends()` inside service code.
  Why: DI belongs at framework entry points, not in domain objects.
- Don't flatten every concern into route-level dependencies.
  Why: nested dependencies are fine when they encode a meaningful chain.

### Right
```python
from typing import Annotated
from fastapi import Depends

class Repo: ...
class Service:
    def __init__(self, repo: Repo) -> None: self.repo = repo
def get_repo() -> Repo: return Repo()
def get_service(repo: Annotated[Repo, Depends(get_repo)]) -> Service:
    return Service(repo)
ServiceDep = Annotated[Service, Depends(get_service)]
```

### Wrong
```python
from fastapi import Depends

_repo = object()
def get_repo():
    return _repo
def get_service(_: object = Depends(get_repo)):
    return {"service": "hidden-global"}
```

### Reviewer Red Flags
- Provider functions mutate module-level state.
  Why it matters: the dependency result is no longer request-scoped or testable.
- The same dependency is rebuilt with copy-pasted constructor code in many routes.
  Why it matters: reviewers should ask for a provider or alias.
- Providers do network I/O, database writes, or business side effects before the route runs.
  Why it matters: the dependency graph is doing real work outside explicit use-case flow.
- Test code monkeypatches internals instead of using `dependency_overrides`.
  Why it matters: the test is bypassing the framework's real seam.
- Dependency names like `get_stuff` or `common_dep` do not describe what is provided.
  Why it matters: reviewers cannot reason about intent from the signature.
- DI functions import application globals from arbitrary modules.
  Why it matters: the code is drifting toward service-locator behavior.

### Convention Observed in ai-workflow
- Convention observed in `ai-workflow`: HTTP-facing providers live in a versioned dependency module.
  File reference: `app/api/v1/dependencies.py:1-5`.
- Convention observed in `ai-workflow`: app-state-backed infrastructure providers read from `request.app.state`.
  File reference: `app/api/v1/dependencies.py:27-60`.
- Convention observed in `ai-workflow`: provider composition is layered from infrastructure to repository to service.
  File reference: `app/api/v1/dependencies.py:68-102`.
- Convention observed in `ai-workflow`: `Annotated` aliases are the preferred endpoint injection style.
  File reference: `app/api/v1/dependencies.py:105-126`.
- Convention observed in `ai-workflow`: settings are cached with `@lru_cache(maxsize=1)`.
  File reference: `app/core/dependencies.py:1-9`.
- Convention observed in `ai-workflow`: tests override settings and service providers through `app.dependency_overrides`.
  File reference: `tests/unit/test_error_handler_integration.py:69-80`, `tests/unit/test_error_handler_integration.py:145-147`.

## 4. State Management & Singletons

Scope:
- FastAPI apps need shared resources.
- Shared resources do not justify ad hoc globals.
- Reviewer default: mutable process state is suspicious until proven safe.

### DO
- Store lifespan-scoped shared clients on `app.state`.
  Why: ownership and teardown stay tied to application lifetime.
- Treat settings objects as effectively immutable once created.
  Why: config should be read, not mutated during request handling.
- Use `lru_cache` or equivalent only for immutable, side-effect-free configuration providers.
  Why: cached settings are fine; cached request or DB state is not.
- Initialize shared external clients in lifespan, not lazily in random request paths.
  Why: failures surface at startup and teardown is centralized.
- Make request-specific state explicit as function parameters or dependency results.
  Why: reviewers should know whether data is per-request or process-wide.
- Prefer explicit caches with size, eviction, and ownership semantics.
  Why: "temporary dict cache" becomes permanent production state very quickly.
- Ensure tests can replace shared resources by overriding providers or building a fresh app.
  Why: singleton state must not leak between tests.
- Distinguish immutable singleton data from mutable singleton services.
  Why: the latter needs concurrency and lifecycle scrutiny.
- Put cleanup paths next to creation paths.
  Why: reviewers should not have to guess how sockets, pools, or files get closed.

### DON'T
- Don't use module-level dicts, lists, sets, or objects as application state.
  Why: state becomes process-local, invisible to DI, and unsafe under reloads or multi-worker deploys.
- Don't mutate `app.state.settings` during requests as a control mechanism.
  Why: that makes configuration request-dependent and test-order-dependent.
- Don't create long-lived clients on first use in route handlers.
  Why: lazy initialization tends to hide startup failures and duplicate connection pools.
- Don't store request-specific data on global objects.
  Why: concurrency turns that into a cross-request bug.
- Don't use globals to communicate between middleware and routes.
  Why: `scope`, `request.state`, and headers exist for that reason.
- Don't use in-memory state for correctness-critical workflows in multi-process deployments.
  Why: each worker sees different state.
- Don't assume `lru_cache` makes unsafe objects safe.
  Why: caching changes lifetime, not thread-safety.
- Don't hide caches inside dependency providers without invalidation strategy.
  Why: reviewers cannot reason about staleness or memory growth.
- Don't patch singletons in tests without restoring them.
  Why: flaky tests are a near-certainty.

### Right
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

class Client:
    async def close(self) -> None: pass
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.client = Client()
    yield
    await app.state.client.close()
app = FastAPI(lifespan=lifespan)
```

### Wrong
```python
from fastapi import FastAPI

app = FastAPI()
client = {"connected": True}
@app.get("/status")
async def status() -> dict[str, bool]:
    client["checked"] = True
    return {"ok": client["connected"]}
```

### Reviewer Red Flags
- `_storage = {}` or `_cache = {}` at module scope in production code.
  Why it matters: that is hidden stateful global storage.
- A route creates a shared client and assigns it to a module variable.
  Why it matters: lifecycle is now first-request-wins.
- Tests depend on execution order because singleton state is reused.
  Why it matters: the app boundary is not isolated.
- `app.state` is used for random business data, not infrastructure.
  Why it matters: application state is becoming a junk drawer.
- Configuration flags are toggled dynamically during a request.
  Why it matters: one request can alter another request's behavior.
- Singleton services perform request-specific accumulation.
  Why it matters: concurrency bugs are imminent.

### Convention Observed in ai-workflow
- Convention observed in `ai-workflow`: shared clients are created in lifespan and stored on `app.state`.
  File reference: `app/core/factory.py:147-166`.
- Convention observed in `ai-workflow`: settings are also placed on `app.state` for handler access.
  File reference: `app/core/factory.py:207`.
- Convention observed in `ai-workflow`: HTTP dependencies read app-state resources instead of importing globals.
  File reference: `app/api/v1/dependencies.py:27-60`.
- Convention observed in `ai-workflow`: settings provider is cached, but DB and search clients are not.
  File reference: `app/core/dependencies.py:1-9`, `app/core/factory.py:147-166`.
- Convention observed in `ai-workflow`: tests build fresh apps or override providers instead of mutating module globals.
  File reference: `tests/conftest.py:81-111`, `tests/unit/test_error_handler_integration.py:69-80`.

## 5. Async / Sync Handler Choice

Scope:
- FastAPI allows both `async def` and plain `def`.
- They are not interchangeable in performance or correctness terms.
- Reviewer default: async is for non-blocking I/O; sync is for blocking I/O or CPU work delegated elsewhere.

### DO
- Use `async def` for handlers and dependencies that await non-blocking I/O.
  Why: this is the natural FastAPI execution model.
- Use plain `def` only when the code is truly synchronous and blocking.
  Why: FastAPI will move it to a threadpool instead of blocking the event loop.
- Use `anyio.to_thread.run_sync()` or `run_in_threadpool()` when an async path must call a sync SDK.
  Why: blocking libraries should not run directly in the event loop.
- Use one `AsyncSession` per task when doing concurrent async database work.
  Why: SQLAlchemy documents that `AsyncSession` is not safe to share across concurrent tasks.
- Keep background work short if you use `BackgroundTasks`.
  Why: it runs in-process after the response and can be lost if the worker dies.
- Use a real task queue for retryable, durable, long-running, or CPU-heavy work.
  Why: in-process background tasks are not job infrastructure.
- Favor `async def` for trivial compute-only FastAPI handlers too.
  Why: FastAPI runs sync handlers in a threadpool, so trivial sync code is not a performance win here.
- Eager-load or otherwise avoid implicit async ORM lazy loads.
  Why: implicit I/O on attribute access is a common async SQLAlchemy failure mode.
- Keep transactions and awaits tight around actual I/O.
  Why: long-lived transactions or long gaps between awaits complicate failure handling.

### DON'T
- Don't call `time.sleep()`, sync HTTP clients, sync cloud SDKs, or blocking file/database work inside `async def`.
  Why: that blocks the event loop and stalls other requests.
- Don't use `asyncio.gather()` with one shared `AsyncSession`.
  Why: SQLAlchemy says one session per concurrent task.
- Don't mark everything `async def` and then fill it with sync libraries.
  Why: the syntax becomes misleading and reviewers miss actual blocking behavior.
- Don't use `BackgroundTasks` for jobs you would need to retry, monitor, or guarantee.
  Why: lost tasks are normal failure mode there.
- Don't do CPU-bound work on the request thread without an offload strategy.
  Why: async does not make CPU work cheap.
- Don't treat threadpool offload as a free abstraction.
  Why: threads have overhead and still need bounded usage.
- Don't leave ORM lazy loading behavior implicit in async code.
  Why: it often turns into runtime surprises like "implicit IO not allowed".
- Don't use sync dependencies by default when they do no blocking work.
  Why: community guidance favors async dependencies to avoid needless threadpool hops.
- Don't claim a route is async-safe just because the function is `async def`.
  Why: safety depends on the called libraries, not the keyword.

### Right
```python
import anyio
from fastapi import FastAPI

app = FastAPI()
def read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f: return f.read()
@app.get("/config")
async def get_config() -> dict[str, str]:
    text = await anyio.to_thread.run_sync(read_file, "config.txt")
    return {"text": text}
```

### Wrong
```python
import time
from fastapi import FastAPI

app = FastAPI()
@app.get("/block")
async def block() -> dict[str, bool]:
    time.sleep(5)
    return {"ok": True}
```

### Reviewer Red Flags
- `async def` handler calls `requests.get`, `boto3`, `subprocess.run`, or `time.sleep`.
  Why it matters: the event loop is being blocked.
- PR adds `asyncio.gather()` around repository calls sharing one session.
  Why it matters: async database concurrency is likely incorrect.
- A durable workflow is implemented with `BackgroundTasks`.
  Why it matters: that is a reliability bug disguised as a convenience.
- Async ORM objects are accessed after commit with lazy relationships still unresolved.
  Why it matters: implicit I/O will bite later, often only in production.
- Sync route handlers are used everywhere "for performance".
  Why it matters: FastAPI's documented behavior makes that a bad default.
- CPU-heavy loops, PDF rendering, or large compression jobs happen inline in request handlers.
  Why it matters: latency spikes and worker starvation follow.

### Convention Observed in ai-workflow
- Convention observed in `ai-workflow`: endpoints are async when calling async services.
  File reference: `app/api/v1/endpoints/example.py:72-74`, `app/api/v1/endpoints/example.py:93-113`.
- Convention observed in `ai-workflow`: sync external clients are wrapped with async-friendly thread offload via `anyio.to_thread.run_sync`.
  File reference: `app/infrastructure/elasticsearch/client.py:45-117`, `app/infrastructure/duckdb/client.py:86-140`.
- Convention observed in `ai-workflow`: the SurrealDB pool is truly async and exposes async acquire/query methods.
  File reference: `app/infrastructure/surrealdb/pool.py:74-145`.
- Convention observed in `ai-workflow`: no `BackgroundTasks` usage was observed under `app/`.
  File reference: repository-wide inspection of `app/` showed no `BackgroundTasks`.
- Convention observed in `ai-workflow`: one sync demo route exists, but most real flow routes are async.
  File reference: `app/api/v1/endpoints/example.py:41-49`, `app/api/v1/endpoints/example.py:72-139`.

## 6. Pydantic Models & API Contracts

Scope:
- Pydantic v2 is the baseline.
- DTOs are contract objects, not persistence mirrors.
- Reviewers should treat schema drift as API drift.

### DO
- Use Pydantic v2 APIs: `model_dump`, `model_copy`, `model_validate`, `model_json_schema`.
  Why: v1-style calls are migration debt now.
- Set `model_config = ConfigDict(...)` explicitly when contract behavior matters.
  Why: extra fields, aliases, and attribute parsing should never be accidental.
- Use `Field(...)` constraints or `Annotated[..., Field(...)]` for length, range, regex, and alias semantics.
  Why: schema rules belong in the schema.
- Prefer separate request and response models.
  Why: output usually should not equal accepted input or DB layout.
- Use `field_validator` for field-local normalization and `model_validator` for cross-field invariants.
  Why: reviewers should see exactly where validation semantics live.
- Consider `extra="forbid"` for external request contracts by default.
  Why: it surfaces client mistakes instead of silently accepting junk.
- Use `from_attributes=True` only when intentionally validating from objects.
  Why: it is the v2 replacement for `from_orm`, not a default setting.
- Use `exclude_none=True` or route-level `response_model_exclude_none=True` when `null` noise hurts contract clarity.
  Why: optional output should be deliberate, not accidental clutter.
- Use strict fields or model strict mode when coercion would be dangerous.
  Why: silent coercion can hide bad client behavior.

### DON'T
- Don't keep authoring new Pydantic v1 code unless you are on a bounded migration path.
  Why: FastAPI moved on and Python 3.14 support for v1 is gone.
- Don't mix v1 and v2 models inside one nested model graph.
  Why: Pydantic explicitly does not support that.
- Don't rely on `from_orm`, `.dict()`, `.json()`, or `.copy()` in fresh code.
  Why: those are old APIs or deprecated migration crutches.
- Don't put every possible output field on one mega response model.
  Why: sparse kitchen-sink schemas are hard for clients and reviewers to trust.
- Don't use ORM models as request bodies.
  Why: validation and API meaning are now coupled to storage classes.
- Don't raise generic `ValueError` in random service code and expect FastAPI to shape it nicely.
  Why: only schema validation paths get automatic validation response semantics.
- Don't accept `extra="ignore"` for public request DTOs unless there is a compatibility reason.
  Why: silent acceptance makes bad clients look healthy.
- Don't use aliases casually.
  Why: Pydantic validation and serialization alias behavior is subtle and should be intentional.
- Don't model secrets as normal strings without representation control.
  Why: secrets leak through logs and reprs surprisingly easily.

### Right
```python
from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field, field_validator

class UserIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: Annotated[str, Field(min_length=3)]
    @field_validator("email")
    @classmethod
    def normalize(cls, value: str) -> str:
        return value.strip().lower()
```

### Wrong
```python
from pydantic.v1 import BaseModel

class User(BaseModel):
    class Config:
        orm_mode = True
    email: str
    is_admin: bool = False
```

### Reviewer Red Flags
- New code imports from `pydantic.v1` without an explicit migration note.
  Why it matters: that is debt, not a neutral choice.
- Public input DTOs use permissive defaults and accept unknown keys silently.
  Why it matters: client bugs are being hidden.
- Response DTOs are reused as write DTOs.
  Why it matters: write and read semantics usually diverge quickly.
- A PR uses `.dict()` or `.json()` on v2 models in new code.
  Why it matters: old API usage spreads migration drag.
- Cross-field validation is hidden in the service layer instead of schema or domain invariant code.
  Why it matters: reviewers have to guess where invalid payloads are stopped.
- Aliases are added without clarifying validation and serialization direction.
  Why it matters: Pydantic uses aliases for validation by default but not for serialization.

### Convention Observed in ai-workflow
- Convention observed in `ai-workflow`: request and response contracts are separate models under `contracts`.
  File reference: `app/contracts/example_contract.py:38-112`.
- Convention observed in `ai-workflow`: most external contracts use `ConfigDict(extra="forbid")`.
  File reference: `app/contracts/example_contract.py:49`, `app/contracts/example_contract.py:79`, `app/contracts/example_contract.py:107`, `app/contracts/pagination.py:43-49`.
- Convention observed in `ai-workflow`: field-local validation uses `field_validator(..., mode="before")`.
  File reference: `app/contracts/example_contract.py:54-60`.
- Convention observed in `ai-workflow`: the canonical error envelope uses alias `statusCode` and `populate_by_name=True`.
  File reference: `app/contracts/errors.py:41-52`.
- Convention observed in `ai-workflow`: settings use Pydantic Settings and field validators for URLs and numeric constraints.
  File reference: `app/core/settings.py:75-186`.
- Convention observed in `ai-workflow`: responses are serialized with `model_dump(..., by_alias=True, exclude_none=True)` in handlers.
  File reference: `app/core/exceptions.py:92-95`, `app/core/exceptions.py:110-113`, `app/core/exceptions.py:127-130`.

## 7. Error Handling & HTTP Responses

Scope:
- Errors are part of the API contract.
- Reviewers should look for consistency before cleverness.
- The important split is validation vs domain vs infrastructure failure.

### DO
- Pick one error envelope and use it consistently.
  Why: clients should not parse five shapes for the same API.
- Raise `HTTPException` only for transport-layer conditions that are truly HTTP concerns.
  Why: services should usually raise domain exceptions instead.
- Map domain exceptions in centralized exception handlers.
  Why: policy stays uniform and services remain framework-light.
- Log unexpected exceptions exactly once at the boundary.
  Why: duplicate logging creates noise and false severity.
- Use 404 for missing resources, 409 for conflicts, 401 for missing or invalid authentication, and 403 for authorization failures.
  Why: reviewers should defend precise semantics.
- Distinguish request shape validation from domain-rule failure.
  Why: "field missing" and "business rule rejected" are different classes of error.
- Sanitize validation details before echoing them to clients.
  Why: context objects can contain non-JSON or overly verbose data.
- Decide intentionally whether request validation is 422 or an org-standardized 400.
  Why: both exist in the ecosystem; inconsistency is the real bug.
- Return stable machine-readable error codes in addition to human messages.
  Why: clients automate on codes, humans debug on messages.

### DON'T
- Don't swallow exceptions and return vague success-like payloads.
  Why: reviewers should treat silent failure as correctness loss.
- Don't catch `Exception` in route handlers just to turn everything into 200 or 400.
  Why: the global handler boundary already exists for unexpected failures.
- Don't leak raw stack traces, driver errors, or SQL text to clients.
  Why: that is a security and contract stability problem.
- Don't mix multiple validation status codes for the same API family without policy.
  Why: client behavior becomes brittle for no gain.
- Don't raise `HTTPException` deep in repository code.
  Why: storage failures are not transport-layer concerns.
- Don't convert every business error into 500.
  Why: reviewer-visible semantics are being thrown away.
- Don't log expected domain failures at exception severity.
  Why: warning or info is often enough; reserve exception logs for real faults.
- Don't return ad hoc dicts for errors from route handlers.
  Why: a contract exists exactly to prevent this drift.
- Don't include secrets, tokens, or full request bodies in generic error logs by default.
  Why: observability must not become data exfiltration.

### Right
```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

class NotFoundError(Exception): pass
app = FastAPI()
@app.exception_handler(NotFoundError)
async def handle_not_found(_: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": str(exc)})
```

### Wrong
```python
from fastapi import APIRouter

router = APIRouter()
@router.get("/items/{item_id}")
async def read_item(item_id: str) -> dict[str, object]:
    try:
        raise RuntimeError("db timeout")
    except Exception:
        return {"ok": False}
```

### Reviewer Red Flags
- Route handlers wrap everything in `try/except Exception`.
  Why it matters: failures are being flattened and hidden.
- Some endpoints return `{"detail": ...}`, others return `{"error": ...}`, others return custom envelopes.
  Why it matters: error contract fragmentation has already started.
- Repository code raises `HTTPException`.
  Why it matters: persistence layer is now coupled to HTTP semantics.
- Domain-rule violations produce 500.
  Why it matters: the API is misreporting expected failure modes.
- Validation errors echo arbitrary request bodies or internal context objects without filtering.
  Why it matters: client-visible leakage risk is high.
- Caplog tests assert duplicate logs for one failure path.
  Why it matters: the code likely logs the same failure at multiple layers.

### Convention Observed in ai-workflow
- Convention observed in `ai-workflow`: request validation is normalized into a custom `AppError` envelope.
  File reference: `app/core/exceptions.py:45-95`.
- Convention observed in `ai-workflow`: request validation returns 400, not FastAPI's default 422.
  File reference: `app/core/exceptions.py:48-50`, `app/core/exceptions.py:92-95`.
- Convention observed in `ai-workflow`: domain exceptions are mapped centrally, not in routes.
  File reference: `app/core/factory.py:209-211`, `app/core/exceptions.py:98-113`.
- Convention observed in `ai-workflow`: unexpected errors are logged and wrapped as generic 500 responses.
  File reference: `app/core/exceptions.py:116-130`.
- Convention observed in `ai-workflow`: the error envelope uses machine-readable `ErrorCode` values.
  File reference: `app/contracts/errors.py:30-38`.
- Convention observed in `ai-workflow`: validation details are sanitized and truncated before emission.
  File reference: `app/core/exceptions.py:25-42`.

## 8. Persistence & Repository Pattern

Scope:
- Persistence belongs behind an explicit boundary.
- Reviewers should ask two questions:
- Where is the transaction boundary?
- Where does storage-specific code stop?

### DO
- Provide database sessions or connections through dependencies.
  Why: request lifecycle and cleanup stay explicit.
- Keep transaction scope short and aligned to a use case.
  Why: SQLAlchemy recommends clear begin and end points.
- Prefer the service layer to own commit and rollback decisions when one use case may touch multiple repositories.
  Why: transaction boundaries belong to workflows, not just tables.
- Use repository abstractions where business logic should not care about driver details.
  Why: reviewers can evaluate business rules without decoding SQL.
- Use `async_sessionmaker` with SQLAlchemy async stacks.
  Why: that is the supported factory for typed `AsyncSession` creation.
- Use one `AsyncSession` per concurrent task.
  Why: SQLAlchemy explicitly says `AsyncSession` is not safe for concurrent sharing.
- Use eager loading or explicit queries in async ORM code.
  Why: implicit lazy loading can fail under asyncio.
- Keep routers free of ORM mutation logic.
  Why: transport should not be a transaction script.
- Validate repository inputs before using them in query text or file paths.
  Why: low-level boundaries are where injection and traversal bugs land.

### DON'T
- Don't create sessions inside repositories with hidden global engines when request scope matters.
  Why: callers cannot control transaction semantics.
- Don't commit inside every repository method by default.
  Why: multi-repository workflows become impossible to reason about.
- Don't pass ORM sessions through half the codebase "just in case".
  Why: implicit write capability leaks everywhere.
- Don't serialize ORM models directly from routers.
  Why: lazy loads and unwanted fields leak into response generation.
- Don't share one async session across `asyncio.gather()` tasks.
  Why: that violates SQLAlchemy guidance.
- Don't mix read-model shaping logic, persistence, and business decisions in one function.
  Why: reviewers lose the boundary between query and rule.
- Don't keep transactions open across slow network calls to other services.
  Why: DB resources stay locked while unrelated work happens.
- Don't trust "internal only" query strings or file paths without validation.
  Why: internal inputs are still inputs.
- Don't treat repositories as generic grab-bags for anything data-adjacent.
  Why: repositories should expose domain-relevant persistence operations.

### Right
```python
from collections.abc import Generator

class Session: ...
def get_session() -> Generator[Session, None, None]:
    session = Session()
    try: yield session
    finally: ...
```

### Wrong
```python
class Repo:
    def save(self, data: dict[str, str]) -> None:
        global_session.commit()
        global_cache["last"] = data
```

### Reviewer Red Flags
- Route handlers call `session.add`, `session.commit`, or raw SQL directly.
  Why it matters: transport is bypassing the domain or repository boundary.
- Repository methods commit unconditionally without the service choosing.
  Why it matters: transaction ownership is hidden.
- A PR adds `asyncio.gather()` over one shared session.
  Why it matters: async SQLAlchemy safety is being ignored.
- Driver-specific exceptions leak above the repository boundary.
  Why it matters: storage coupling is rising.
- Query strings interpolate user input without parameterization or validation.
  Why it matters: injection risk sits at the persistence edge.
- ORM instances are returned all the way to the API layer.
  Why it matters: response behavior now depends on session state and lazy fields.

### Convention Observed in ai-workflow
- Convention observed in `ai-workflow`: repository interfaces are defined as `Protocol`s.
  File reference: `app/repositories/example_repository.py:34-64`.
- Convention observed in `ai-workflow`: repositories are constructed in DI providers, not imported as globals.
  File reference: `app/api/v1/dependencies.py:68-81`.
- Convention observed in `ai-workflow`: the repository boundary separates SurrealDB writes from DuckDB CSV reads.
  File reference: `app/repositories/example_repository.py:67-145`.
- Convention observed in `ai-workflow`: input file names for CSV access are validated before path construction.
  File reference: `app/infrastructure/duckdb/client.py:44-64`, `app/infrastructure/duckdb/client.py:141-154`.
- Convention observed in `ai-workflow`: SurrealDB connections are acquired through an async pool context manager.
  File reference: `app/infrastructure/surrealdb/pool.py:105-118`.
- Convention observed in `ai-workflow`: service methods, not routes, perform the repository calls that implement use cases.
  File reference: `app/services/example_service.py:58-115`.

Contested point:
- Some FastAPI examples commit in route handlers.
  Reviewer anchor: in production apps, prefer commit ownership in the service layer unless the route itself is the only use-case layer.

## 9. Configuration & Secrets

Scope:
- Config is code-adjacent, not hardcoded.
- Secrets belong in environment or secret stores, not in repo literals.
- Reviewers should inspect default values as carefully as explicit overrides.

### DO
- Use `BaseSettings` from `pydantic-settings` for runtime configuration.
  Why: parsing, validation, and env integration become typed and explicit.
- Validate URLs, timeouts, pool sizes, and enum-like settings at config load time.
  Why: broken deployment config should fail early.
- Use `Field(repr=False)` or dedicated secret types for secrets.
  Why: repr leaks are real.
- Favor secure production defaults or loud documentation warnings on insecure dev defaults.
  Why: reviewers should know when defaults are convenience-only.
- Keep environment variable reads inside the settings object or its provider.
  Why: scattered `os.getenv()` calls rot fast.
- Make test settings explicit in fixtures.
  Why: tests should not depend on a developer's shell environment.
- Separate config loading from app assembly with a small provider function.
  Why: dependency overrides and scripts get simpler.
- Document when a setting is optional, dev-only, or must be tightened in production.
  Why: defaults are part of operational behavior.
- Prefer structured settings over giant untyped dicts.
  Why: reviewers can reason about each field and validation rule.

### DON'T
- Don't hardcode secrets, tokens, DSNs, or credentials in source.
  Why: source control is not a secret store.
- Don't scatter `os.environ[...]` across routers, services, and repositories.
  Why: config ownership becomes impossible to audit.
- Don't perform expensive network or filesystem work in settings validators.
  Why: config load should validate, not initialize infrastructure.
- Don't use config mutation at runtime as a feature toggle mechanism.
  Why: that couples request behavior to process memory state.
- Don't require obscure environment state for tests to even import modules.
  Why: import-time fragility destroys developer velocity.
- Don't hide insecure defaults.
  Why: reviewers need to know whether `"*"` hosts or origins are dev-only compromises.
- Don't let on-prem or local installs fail mysteriously on missing secrets without clear paths.
  Why: operational usability is part of software quality.
- Don't store secrets in plain string repr-visible fields if the model may be logged.
  Why: logs will eventually prove you wrong.
- Don't embed environment-specific path assumptions directly in repositories.
  Why: paths are config, not persistence logic.

### Right
```python
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    api_prefix: str = "/api/v1"
    db_url: str
    secret_key: str = Field(repr=False)
```

### Wrong
```python
import os

DB_URL = os.environ["DB_URL"]
SECRET = "hardcoded-secret"
DEBUG = os.getenv("DEBUG") == "1"
```

### Reviewer Red Flags
- Secrets appear in defaults, fixtures outside tests, or examples copied into real code.
  Why it matters: repo history keeps them forever.
- A PR adds `os.getenv()` calls in multiple layers instead of extending settings.
  Why it matters: configuration is fragmenting.
- Settings validation includes I/O unrelated to validation.
  Why it matters: startup and tests now depend on external behavior during config load.
- Insecure defaults are shipped with no warning comments or docs.
  Why it matters: reviewers should assume they will reach production eventually.
- Tests pass only if specific env vars are already exported on the machine.
  Why it matters: the suite is not hermetic.
- Paths like `/tmp/foo` or `/var/lib/bar` are embedded in business code.
  Why it matters: deployment assumptions leaked out of config.

### Convention Observed in ai-workflow
- Convention observed in `ai-workflow`: runtime config is modeled as `Settings(BaseSettings)`.
  File reference: `app/core/settings.py:75-186`.
- Convention observed in `ai-workflow`: secret-like fields use `repr=False` and password schema hints.
  File reference: `app/core/settings.py:119-132`.
- Convention observed in `ai-workflow`: settings validators check URL schemes and numeric ranges eagerly.
  File reference: `app/core/settings.py:150-186`.
- Convention observed in `ai-workflow`: comments explicitly call out permissive dev defaults that must be tightened in production.
  File reference: `app/core/settings.py:80-105`.
- Convention observed in `ai-workflow`: tests inject deterministic credentials through fixtures and `setdefault`.
  File reference: `tests/conftest.py:64-78`, `tests/conftest.py:126-135`.
- Convention observed in `ai-workflow`: settings retrieval is centralized in `get_settings()`.
  File reference: `app/core/dependencies.py:1-9`.

## 10. Logging & Observability

Scope:
- Logs, metrics, and correlation IDs are boundary concerns.
- Reviewers should look for useful signal, not maximal verbosity.
- Observability that leaks secrets is not observability.

### DO
- Log at system boundaries: request entry and exit, external client failures, lifecycle startup and shutdown, and unexpected exceptions.
  Why: these are the places reviewers need when debugging behavior.
- Use structured log fields such as method, path, request ID, status code, and duration.
  Why: searchable context beats prose-heavy logs.
- Propagate or generate request IDs.
  Why: correlation across middleware, handlers, and downstream clients matters.
- Keep success logs short and machine-friendly.
  Why: access logs should be easy to aggregate.
- Log unexpected failures with stack traces once at the boundary.
  Why: that preserves debuggability without duplication.
- Keep validation and domain errors at warning or info unless policy says otherwise.
  Why: expected client or business failures are not crash-level events.
- Consider metrics for latency and status-code distributions on hot paths.
  Why: some production questions are better answered by counters than by logs.
- Exclude secrets and PII by default from logs.
  Why: reviewers should assume logs are broadly visible.
- Include latency using monotonic or high-precision timers.
  Why: wall-clock drift is not useful for request timing.

### DON'T
- Don't use `print()` for application diagnostics in server code.
  Why: prints are unstructured and bypass logging policy.
- Don't log request or response bodies globally by default.
  Why: that is a secret and PII hazard.
- Don't log the same failure in every layer on the way up.
  Why: one bug turns into six alerts.
- Don't omit correlation IDs in distributed or multi-step workflows.
  Why: debugging becomes guesswork.
- Don't make every log line a paragraph.
  Why: observability should be queryable, not literary.
- Don't create custom middleware that logs but never preserves or emits request identity.
  Why: the most useful join key is missing.
- Don't record in-memory metrics without a clear exposure or scrape strategy and call it "monitoring".
  Why: counters trapped in process memory are only half a solution.
- Don't log secrets just because a library exception includes them.
  Why: scrub or summarize.
- Don't bury lifecycle failures in silent startup retries.
  Why: if the app cannot initialize resources, reviewers should expect hard failure and clear logs.

### Right
```python
import logging, time
from fastapi import FastAPI, Request

log = logging.getLogger(__name__)
app = FastAPI()
@app.middleware("http")
async def timing(request: Request, call_next):
    started = time.perf_counter(); response = await call_next(request)
    log.info("request", extra={"path": request.url.path, "status": response.status_code, "ms": round((time.perf_counter() - started) * 1000, 2)})
    return response
```

### Wrong
```python
from fastapi import FastAPI, Request

app = FastAPI()
@app.middleware("http")
async def noisy(request: Request, call_next):
    print("request", request.headers, await request.body())
    return await call_next(request)
```

### Reviewer Red Flags
- `print()` statements in app code, handlers, or middleware.
  Why it matters: observability is bypassing the logging system.
- Middleware logs full headers or bodies.
  Why it matters: secrets and PII are at risk.
- There is no request ID but the app makes multiple downstream calls.
  Why it matters: troubleshooting cross-service flows will be painful.
- Access logging exists but omits status and latency.
  Why it matters: it is not enough for operational debugging.
- Metrics collection stores data only in in-memory objects with no exposure plan.
  Why it matters: "metrics" may be purely local trivia.
- Startup/shutdown failures are retried or ignored without logging context.
  Why it matters: broken infrastructure will look like transient weirdness.

### Convention Observed in ai-workflow
- Convention observed in `ai-workflow`: request IDs are generated or propagated in middleware and echoed as `X-Request-ID`.
  File reference: `app/core/middleware.py:63-105`.
- Convention observed in `ai-workflow`: request logging includes method, path, request ID, status, and duration.
  File reference: `app/core/middleware.py:107-165`.
- Convention observed in `ai-workflow`: lifecycle setup and teardown log initialization and cleanup outcomes.
  File reference: `app/core/factory.py:154-185`.
- Convention observed in `ai-workflow`: unexpected errors are logged with exception context in the central handler.
  File reference: `app/core/exceptions.py:116-125`.
- Convention observed in `ai-workflow`: metrics middleware exists but is in-memory only.
  File reference: `app/core/middleware.py:168-218`.
- Convention observed in `ai-workflow`: settings toggle logging, metrics, request IDs, and rate limiting explicitly.
  File reference: `app/core/settings.py:108-114`.

## 11. Middleware & Lifecycle

Scope:
- Middleware order is architecture, not decoration.
- Lifespan is the preferred home for app-wide startup and teardown.
- Reviewers should read middleware stacks outside-in.

### DO
- Use `lifespan` with `@asynccontextmanager` for startup and shutdown logic.
  Why: FastAPI recommends lifespan over legacy events.
- Register middleware in a deliberate order and document the intent.
  Why: last added runs first on the request path.
- Put CORS outside auth-heavy or business middleware when browser preflights must succeed cleanly.
  Why: preflight behavior is cross-cutting transport policy.
- Put security headers in middleware rather than repeating them in routes.
  Why: headers are app-wide response policy.
- Put request IDs early enough that later middleware and handlers can log them.
  Why: correlation should exist before most logging executes.
- Fail fast if critical shared resources cannot initialize during lifespan.
  Why: partial startup is usually worse than no startup.
- Ensure teardown closes clients and pools even if startup partly failed.
  Why: startup failure paths still leak resources if not handled.
- Use `with TestClient(app)` when tests depend on lifespan startup behavior.
  Why: FastAPI documents that this triggers lifespan.
- Keep middleware focused on cross-cutting concerns only.
  Why: middleware is the wrong place for business workflows.

### DON'T
- Don't mix `lifespan` and old startup or shutdown events in new code.
  Why: FastAPI warns that it is one model or the other.
- Don't register middleware without understanding stack order.
  Why: headers, logging, rate limiting, and CORS can easily end up in the wrong place.
- Don't put per-request DB or business logic into middleware if DI can express it better.
  Why: middleware sees everything and becomes an opaque bottleneck fast.
- Don't assume `AsyncClient` test fixtures trigger lifespan automatically.
  Why: FastAPI docs call that out as a caveat for async tests.
- Don't put secrets or raw bodies into request logging middleware.
  Why: one global log sink can leak everything.
- Don't do expensive synchronous work in middleware around every request.
  Why: the cost multiplies across the entire API surface.
- Don't swallow startup failures and keep serving traffic in a degraded unknown state.
  Why: reviewers should prefer a hard, observable failure.
- Don't implement stateful rate limiting in process memory unless the scale and deployment model justify it.
  Why: multi-worker deployments will see inconsistent limits.
- Don't let middleware mutate shared global state for communication.
  Why: request-scoped communication belongs in `scope` or request state.

### Right
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.ready = True
    yield
    app.state.ready = False
app = FastAPI(lifespan=lifespan)
```

### Wrong
```python
from fastapi import FastAPI

app = FastAPI()
items = {}
@app.on_event("startup")
async def startup() -> None:
    items["ready"] = True
```

### Reviewer Red Flags
- Middleware order is undocumented and clearly accidental.
  Why it matters: request behavior may be correct only by chance.
- CORS is configured with `"*"` while credentials are expected.
  Why it matters: FastAPI docs explicitly note that wildcard origins do not support credentialed browser flows.
- A PR adds `@app.on_event("startup")` instead of touching lifespan.
  Why it matters: new code is extending legacy lifecycle style.
- Tests use async clients against lifespan-dependent apps with no lifespan manager.
  Why it matters: startup resources may never initialize in tests.
- Rate limiting or metrics are stored only in one process's memory without acknowledgment.
  Why it matters: reviewers should question deployment correctness.
- Middleware performs authz decisions that belong in route or dependency context.
  Why it matters: business policy becomes harder to reason about than dependency-based auth.

### Convention Observed in ai-workflow
- Convention observed in `ai-workflow`: middleware order is explicitly documented in code comments.
  File reference: `app/core/factory.py:97-102`.
- Convention observed in `ai-workflow`: `TrustedHost`, HTTPS redirect, CORS, security headers, compression, request ID, rate limiting, metrics, and request logging are centralized in `_register_middleware`.
  File reference: `app/core/factory.py:97-145`.
- Convention observed in `ai-workflow`: critical shared resources are created and closed in lifespan with cleanup guards.
  File reference: `app/core/factory.py:147-185`.
- Convention observed in `ai-workflow`: security headers are attached in a custom ASGI middleware, not per route.
  File reference: `app/core/middleware.py:31-60`.
- Convention observed in `ai-workflow`: request ID and logging are middleware concerns, not endpoint concerns.
  File reference: `app/core/middleware.py:63-165`.
- Convention observed in `ai-workflow`: settings drive whether optional middleware features are enabled.
  File reference: `app/core/settings.py:92-114`.

## 12. Testing

Scope:
- Reviewers should expect tests at the right level, not just any tests.
- FastAPI gives two main seams:
- black-box HTTP tests through clients.
- dependency overrides for collaborator replacement.

### DO
- Use `TestClient` for straightforward black-box HTTP tests.
  Why: FastAPI documents this as the simplest path and it triggers lifespan when used as a context manager.
- Use `httpx.AsyncClient` with `ASGITransport` when the test body itself needs `await`.
  Why: async DB assertions and other awaits require async tests.
- Use `app.dependency_overrides` to replace auth, settings, services, and external clients.
  Why: that is the official FastAPI test seam.
- Clear or reset dependency overrides after each test.
  Why: override leakage creates order-dependent failures.
- Build explicit test settings fixtures instead of relying on developer env.
  Why: tests should be reproducible everywhere.
- Mock or fake external infrastructure at the app boundary.
  Why: integration tests should exercise your code, not vendor networks.
- Use unit tests for pure service and schema logic, and integration tests for request-flow behavior.
  Why: level-appropriate tests are easier to understand and cheaper to maintain.
- Keep fixtures small and composable.
  Why: reviewers should be able to see what each test really depends on.
- Use parametrization for input matrix coverage instead of copy-pasted tests.
  Why: reviewers should see the actual contract dimensions.

### DON'T
- Don't monkeypatch deep internals when a dependency override exists.
  Why: that bypasses the real app boundary.
- Don't let tests depend on external services unless they are clearly marked and isolated.
  Why: routine PR feedback should stay fast and deterministic.
- Don't build one global app fixture that keeps mutated state between tests.
  Why: state bleed causes flakiness.
- Don't use sync clients inside async tests.
  Why: FastAPI documents that `TestClient` magic does not apply there.
- Don't skip lifespan in tests that require startup-created resources.
  Why: you are not testing the real app.
- Don't encode secrets, ports, or env assumptions implicitly in tests.
  Why: CI and local environments will diverge.
- Don't assert only on status codes when error-envelope content is part of the contract.
  Why: structure matters, not just transport status.
- Don't overuse mocks at the router layer for behavior that should be verified with a request.
  Why: route wiring bugs disappear when you call functions directly only.
- Don't let fixture graphs become more complex than the app graph.
  Why: tests should reduce complexity, not amplify it.

### Right
```python
from fastapi import FastAPI
from fastapi.testclient import TestClient

app = FastAPI()
@app.get("/") async def root() -> dict[str, str]:
    return {"ok": "yes"}
def test_root() -> None:
    with TestClient(app) as client:
        assert client.get("/").json() == {"ok": "yes"}
```

### Wrong
```python
from fastapi.testclient import TestClient

client = TestClient(app)  # noqa: F821
def test_mutates_global_overrides() -> None:
    app.dependency_overrides[get_service] = lambda: object()  # noqa: F821
    assert client.get("/").status_code == 200
```

### Reviewer Red Flags
- Tests patch helper functions deep in the stack instead of overriding dependencies.
  Why it matters: they are not exercising real wiring.
- Overrides are set but never cleared.
  Why it matters: later tests can silently reuse the wrong collaborator.
- Async tests still use `TestClient`.
  Why it matters: that is not the correct execution model.
- Lifespan-dependent apps are tested without `with TestClient(...)` or equivalent lifespan management.
  Why it matters: startup resources may not exist.
- Test fixtures read real env vars or real secrets by default.
  Why it matters: the suite is not hermetic.
- Error tests assert only status code and ignore envelope code/message/details.
  Why it matters: contract regressions can slip through.

### Convention Observed in ai-workflow
- Convention observed in `ai-workflow`: tests define explicit `Settings` fixtures with safe credentials.
  File reference: `tests/conftest.py:64-78`.
- Convention observed in `ai-workflow`: sync HTTP tests use `with TestClient(app)`.
  File reference: `tests/conftest.py:87-101`.
- Convention observed in `ai-workflow`: async integration tests use `httpx.AsyncClient` plus `ASGITransport`.
  File reference: `tests/conftest.py:104-111`, `tests/integration/test_example_endpoints.py:119-129`.
- Convention observed in `ai-workflow`: provider overrides are applied through `app.dependency_overrides`.
  File reference: `tests/unit/test_error_handler_integration.py:77-80`, `tests/unit/test_error_handler_integration.py:145-147`.
- Convention observed in `ai-workflow`: external resources are replaced with small fakes at the app factory boundary.
  File reference: `tests/integration/test_example_endpoints.py:81-91`.
- Convention observed in `ai-workflow`: tests assert error-envelope structure, not just status.
  File reference: `tests/unit/test_error_handler_integration.py:89-114`, `tests/unit/test_error_handler_integration.py:153-204`.

## 13. Security & Auth

Scope:
- Authn and authz should be dependency-driven and centrally reviewable.
- Reviewers should separate identity, scopes, and business permissions.
- Client-provided state is never enough by itself.

### DO
- Implement authentication as dependencies.
  Why: route signatures make protected surfaces obvious.
- Use `Security()` rather than plain `Depends()` when OAuth2 scopes are part of the contract.
  Why: FastAPI integrates scopes into OpenAPI and dependency trees.
- Centralize token verification in one dependency or a small dependency chain.
  Why: reviewers should not see JWT parsing scattered through routes.
- Enforce authorization separately from authentication.
  Why: "who are you?" and "may you do this?" are different checks.
- Keep required scopes close to the endpoint or a shared dependency alias.
  Why: reviewers can audit access policy from the signature.
- Validate and normalize all externally supplied identifiers before use.
  Why: auth does not eliminate input-validation duties.
- Rate-limit sensitive endpoints such as login, password reset, and expensive search.
  Why: abuse resistance is part of security.
- Use explicit CORS origins when credentials or bearer tokens are involved in browser flows.
  Why: wildcard origins do not work correctly for credentialed requests.
- Log auth failures with enough context to investigate, but not enough to leak secrets.
  Why: boundary logging still applies under security pressure.

### DON'T
- Don't trust role or permission claims just because the client sent them.
  Why: authorization must be derived from verified tokens or server-side state.
- Don't hand-roll crypto primitives, password hashing, or token formats without a strong reason.
  Why: use proven libraries and patterns.
- Don't put authz checks deep in repositories unless they are row-level policies by design.
  Why: most authz belongs above persistence.
- Don't duplicate scope strings and permission logic in many places.
  Why: policy drift follows immediately.
- Don't expose whether a username exists, token parsing failed, or a permission rule failed more than needed on sensitive flows.
  Why: detailed auth error behavior can aid attackers.
- Don't allow `"*"` CORS origins if browser credentials or authorization headers must be supported.
  Why: FastAPI docs call out that wildcard origins exclude credentialed flows.
- Don't leak tokens or auth headers into logs.
  Why: observability must not become credential storage.
- Don't confuse 401 and 403.
  Why: authentication failure and authorization denial are not the same thing.
- Don't let route handlers manually parse `Authorization` headers unless you are implementing a very custom protocol.
  Why: FastAPI security dependencies already provide the seam.

### Right
```python
from typing import Annotated
from fastapi import FastAPI, Security

app = FastAPI()
def get_user() -> str: return "user-1"
@app.get("/me")
async def read_me(user: Annotated[str, Security(get_user, scopes=["me"])]) -> dict[str, str]:
    return {"user": user}
```

### Wrong
```python
from fastapi import FastAPI, Request

app = FastAPI()
@app.get("/admin")
async def admin(request: Request) -> dict[str, bool]:
    return {"ok": request.headers.get("x-role") == "admin"}
```

### Reviewer Red Flags
- Routes read custom role headers directly instead of using verified auth dependencies.
  Why it matters: the app may trust unverified client state.
- Scope or permission strings are duplicated across many modules with no central definition.
  Why it matters: auth drift will happen.
- Auth failures log entire tokens or headers.
  Why it matters: credential leakage risk is immediate.
- Browser credential flows use wildcard CORS origins.
  Why it matters: FastAPI docs say that excludes credentialed cross-origin behavior.
- One code path returns 401 and another 403 for the same missing-permission case.
  Why it matters: semantics are inconsistent.
- Repositories decide broad application permissions.
  Why it matters: security policy is now hidden in storage code.

### Convention Observed in ai-workflow
- Convention observed in `ai-workflow`: no concrete auth or authz dependency graph was implemented under `app/`.
  File reference: repository-wide inspection of `app/` found no OAuth2 or `Security()` usage.
- Convention observed in `ai-workflow`: there is a domain-level `UnauthorizedError` for future policy mapping.
  File reference: `app/core/errors.py:18-26`.
- Convention observed in `ai-workflow`: unauthorized domain errors map to 401 in the standard `AppError` envelope.
  File reference: `app/contracts/errors.py:71-77`.
- Convention observed in `ai-workflow`: CORS settings are explicit fields on `Settings`, including origins, regex, methods, headers, and credentials.
  File reference: `app/core/settings.py:95-106`.
- Convention observed in `ai-workflow`: a simple in-memory rate-limiting middleware exists but is process-local only.
  File reference: `app/core/middleware.py:221-306`.
- Gap noted from `ai-workflow`: reviewers cannot yet infer the org's canonical auth dependency layering from this repo alone.
  File reference: no implemented auth module under `app/`.

## 14. Anti-patterns & Code Smells

Purpose:
- This is the reviewer triage section.
- If you see one of these patterns, stop assuming the rest of the code is fine.

### DO
- Flag module-level mutable state used as caches or stores.
  Why: process-local state is a correctness bug disguised as convenience.
- Flag business logic in routers.
  Why: it is the fastest path to untestable transport scripts.
- Flag ORM or driver objects crossing the API boundary.
  Why: contract and persistence are becoming one thing.
- Flag broad `except Exception` blocks.
  Why: they usually hide defects or destroy error semantics.
- Flag sync blocking calls inside `async def`.
  Why: event-loop blocking is a production latency bug.
- Flag hardcoded secrets or DSNs immediately.
  Why: that is a security incident, not a style issue.
- Flag route handlers that mutate global singletons.
  Why: concurrency and test isolation are already broken.
- Flag missing `response_model` on stable structured endpoints.
  Why: contract drift is starting.
- Flag tests that monkeypatch internals instead of overriding dependencies.
  Why: they are bypassing the framework seam.

### DON'T
- Don't wave through "temporary" in-memory state like `_storage = {}` or `_cache = {}`.
  Why: temporary state almost always becomes undeclared production state.
- Don't accept routers returning ORM entities or raw SQL rows directly.
  Why: lazy loading, hidden fields, and storage coupling follow.
- Don't accept silent `except Exception: return ...`.
  Why: operational failures become invisible business responses.
- Don't accept `print()` as logging.
  Why: it bypasses policy, structure, and redaction.
- Don't accept auth based on custom headers or client claims alone.
  Why: that is unverified trust.
- Don't accept sync SDK calls inside async handlers with no offload.
  Why: event-loop blocking is not hypothetical.
- Don't accept routes that read env vars, construct sessions, and execute SQL all in one function.
  Why: that is architectural collapse in one diff.
- Don't accept wildcard CORS in credentialed browser APIs without a very specific justification.
  Why: the browser behavior will not match the product expectation.
- Don't accept ad hoc error dicts when the app already has a canonical error envelope.
  Why: inconsistency compounds quickly.

### Right
```python
from fastapi import APIRouter

router = APIRouter()
@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
```

### Wrong
```python
from fastapi import APIRouter

router = APIRouter()
_storage: dict[str, str] = {}
@router.get("/items/{item_id}")
async def read_item(item_id: str) -> dict[str, str]:
    _storage["last"] = item_id
    return {"item_id": item_id}
```

### Reviewer Red Flags
- Module-level `_storage = {}` used as a cache or pseudo-database.
  Why it matters: flag as stateful global; use lifespan-scoped dependencies or a real cache instead.
- `time.sleep`, `requests.get`, or sync SDK calls inside `async def`.
  Why it matters: flag as event-loop blocking; offload or switch libraries.
- Business rules, DB writes, and response shaping all happen in one route function.
  Why it matters: flag as missing service and repository boundaries.
- ORM models or raw driver rows are returned directly from endpoints.
  Why it matters: flag as contract leakage and lazy-loading risk.
- `except Exception: pass` or `except Exception: return {"ok": False}`.
  Why it matters: flag as silent failure and lost observability.
- `print()` calls in handlers, services, or middleware.
  Why it matters: flag as non-policy logging.
- Route code reads `os.getenv()` or `os.environ` directly.
  Why it matters: flag as configuration leakage into transport.
- Repositories raise `HTTPException`.
  Why it matters: flag as transport concerns leaking down the stack.
- Tests monkeypatch internals instead of `app.dependency_overrides`.
  Why it matters: flag as bypassed app boundary.
- Auth checks trust role or scope headers sent directly by clients.
  Why it matters: flag as unverified authorization.
- Credentialed browser APIs use `allow_origins=["*"]`.
  Why it matters: flag as incorrect CORS setup for credentialed requests.
- A single `AsyncSession` is shared across concurrent tasks.
  Why it matters: flag as unsupported SQLAlchemy async usage.
- Lifespan resources are initialized lazily in the first request instead of startup.
  Why it matters: flag as hidden initialization and teardown risk.
- Error handlers log secrets, raw bodies, or tokens.
  Why it matters: flag as security leakage in observability.
- Pydantic v1 APIs are used in new code with no migration note.
  Why it matters: flag as avoidable compatibility debt.

### Quick Triage List
- If the diff adds a global mutable object, start skeptical.
  Why: this is one of the highest-signal reviewer smells in FastAPI apps.
- If the diff adds HTTP concerns to services or repositories, start skeptical.
  Why: boundary erosion spreads quickly.
- If the diff adds manual validation that the schema layer could do, ask why.
  Why: contract logic is becoming duplicated.
- If the diff adds middleware, inspect order and scope before anything else.
  Why: middleware mistakes are app-wide.
- If the diff touches error handling, compare all failure paths for shape and status consistency.
  Why: the bug is often inconsistency, not a single broken branch.
- If the diff touches auth, inspect CORS, scopes, and logging together.
  Why: security bugs often span those concerns.

## 15. ai-workflow/init/app Conventions

Important:
- This section is descriptive, not universal FastAPI law.
- Use it when reviewing code meant to match this org's style.
- If general best practice and org convention differ, reviewers should note both.

### App Assembly
- Convention observed in `ai-workflow`: the application is built by a factory, not assembled ad hoc in `main.py`.
  File reference: `app/main.py:1-6`, `app/core/factory.py:190-217`.
- Convention observed in `ai-workflow`: `main.py` is intentionally thin and only calls `get_settings()` plus `create_app(settings)`.
  File reference: `app/main.py:1-6`.
- Convention observed in `ai-workflow`: the app defaults to `ORJSONResponse` globally.
  File reference: `app/core/factory.py:199-205`.
- Convention observed in `ai-workflow`: the app factory stores validated settings on `app.state`.
  File reference: `app/core/factory.py:207`.
- Convention observed in `ai-workflow`: the OpenAPI schema is customized centrally instead of per route.
  File reference: `app/core/factory.py:59-94`, `app/core/factory.py:214-215`.

### Router Layout
- Convention observed in `ai-workflow`: versioned routes live under `app/api/v1`.
  File reference: repository layout under `app/api/v1/`.
- Convention observed in `ai-workflow`: router aggregation happens in a dedicated module.
  File reference: `app/api/v1/router.py:1-8`.
- Convention observed in `ai-workflow`: route modules expose a module-level `router = APIRouter()`.
  File reference: `app/api/v1/endpoints/example.py:21`, `app/api/v1/endpoints/health.py:10`.
- Convention observed in `ai-workflow`: prefixes and tags are applied when routers are included, not by scattering metadata across the app.
  File reference: `app/api/v1/router.py:5-8`.
- Convention observed in `ai-workflow`: the version prefix is config-driven via `settings.api_prefix`.
  File reference: `app/core/settings.py:89`, `app/core/factory.py:208`.

### Endpoint Style
- Convention observed in `ai-workflow`: handlers are thin and mostly call a service.
  File reference: `app/api/v1/endpoints/example.py:72-74`, `app/api/v1/endpoints/example.py:99-113`, `app/api/v1/endpoints/example.py:137-144`.
- Convention observed in `ai-workflow`: route decorators declare `response_model`, `summary`, `description`, and `responses`.
  File reference: `app/api/v1/endpoints/example.py:24-39`, `app/api/v1/endpoints/example.py:52-70`, `app/api/v1/endpoints/health.py:19-35`.
- Convention observed in `ai-workflow`: pagination parameters are declared with `Query(...)` constraints, not manual parsing.
  File reference: `app/api/v1/endpoints/example.py:95-97`.
- Convention observed in `ai-workflow`: the health route reads directly from `request.app.state` to assess readiness.
  File reference: `app/api/v1/endpoints/health.py:37-54`.
- Convention observed in `ai-workflow`: an unversioned `/health` liveness route is also attached directly in the app factory.
  File reference: `app/core/factory.py:212`.

### Dependency Injection Style
- Convention observed in `ai-workflow`: HTTP-facing dependencies are separate from core settings dependency utilities.
  File reference: `app/api/v1/dependencies.py:1-5`, `app/core/dependencies.py:1-9`.
- Convention observed in `ai-workflow`: app-state resource access is wrapped in typed provider functions rather than read inline in routes.
  File reference: `app/api/v1/dependencies.py:27-60`.
- Convention observed in `ai-workflow`: repository providers compose infrastructure clients.
  File reference: `app/api/v1/dependencies.py:68-81`.
- Convention observed in `ai-workflow`: service providers compose repository plus settings.
  File reference: `app/api/v1/dependencies.py:89-102`.
- Convention observed in `ai-workflow`: `Annotated` aliases like `ExampleServiceDep` are the preferred route signature form.
  File reference: `app/api/v1/dependencies.py:110-126`.

### Service Layer Style
- Convention observed in `ai-workflow`: service logic lives in classes, not free functions.
  File reference: `app/services/example_service.py:24-123`.
- Convention observed in `ai-workflow`: services take collaborators in the constructor.
  File reference: `app/services/example_service.py:44-56`.
- Convention observed in `ai-workflow`: services transform request DTOs into response DTOs and domain objects.
  File reference: `app/services/example_service.py:58-76`, `app/services/example_service.py:96-115`.
- Convention observed in `ai-workflow`: missing-resource behavior is expressed as a domain exception, not `HTTPException`.
  File reference: `app/services/example_service.py:78-94`.
- Convention observed in `ai-workflow`: configuration can affect service behavior without changing route code.
  File reference: `app/services/example_service.py:60-62`.
- Convention observed in `ai-workflow`: service shutdown hooks may exist conceptually, though the example implementation is only a placeholder.
  File reference: `app/services/example_service.py:117-123`.

### Repository Layer Style
- Convention observed in `ai-workflow`: repository contracts are expressed as `Protocol`s.
  File reference: `app/repositories/example_repository.py:34-64`.
- Convention observed in `ai-workflow`: domain records returned from repositories are dataclasses, not ORM models.
  File reference: `app/repositories/example_repository.py:17-31`.
- Convention observed in `ai-workflow`: write storage and read storage may differ within one repository.
  File reference: `app/repositories/example_repository.py:67-145`.
- Convention observed in `ai-workflow`: repository methods are async and use driver-specific parameterization where available.
  File reference: `app/repositories/example_repository.py:84-113`.
- Convention observed in `ai-workflow`: mapping from raw row dicts to domain objects is isolated in a private helper.
  File reference: `app/repositories/example_repository.py:147-166`.
- Convention observed in `ai-workflow`: low-level input validation like CSV filename sanitization lives in infrastructure client code.
  File reference: `app/infrastructure/duckdb/client.py:44-64`.

### Pydantic & Contract Style
- Convention observed in `ai-workflow`: contract models sit under `app/contracts`.
  File reference: repository layout under `app/contracts/`.
- Convention observed in `ai-workflow`: request and response models are distinct types.
  File reference: `app/contracts/example_contract.py:38-112`.
- Convention observed in `ai-workflow`: external contracts use `ConfigDict(extra="forbid")` aggressively.
  File reference: `app/contracts/example_contract.py:49`, `app/contracts/example_contract.py:79`, `app/contracts/example_contract.py:107`, `app/contracts/pagination.py:43`.
- Convention observed in `ai-workflow`: string and integer constraints are expressed with `Field(...)`.
  File reference: `app/contracts/example_contract.py:51-52`, `app/contracts/example_contract.py:81-83`, `app/contracts/pagination.py:45-48`.
- Convention observed in `ai-workflow`: request normalization happens in `field_validator`.
  File reference: `app/contracts/example_contract.py:54-60`.
- Convention observed in `ai-workflow`: the canonical error model uses `statusCode` aliasing.
  File reference: `app/contracts/errors.py:44-49`.
- Convention observed in `ai-workflow`: validation detail payloads have bounded list and location sizes.
  File reference: `app/contracts/errors.py:24-27`, `app/contracts/errors.py:120-143`.

### Settings Style
- Convention observed in `ai-workflow`: config fields are strongly typed and validated on load.
  File reference: `app/core/settings.py:75-186`.
- Convention observed in `ai-workflow`: permissive defaults are annotated with comments warning they are for local development only.
  File reference: `app/core/settings.py:80-105`.
- Convention observed in `ai-workflow`: secrets are hidden from repr and marked with JSON-schema password format hints.
  File reference: `app/core/settings.py:119-132`.
- Convention observed in `ai-workflow`: URL schemes are validated with dedicated validators and custom error types.
  File reference: `app/core/settings.py:43-56`, `app/core/settings.py:150-164`.
- Convention observed in `ai-workflow`: numeric settings are validated centrally with one reusable validator.
  File reference: `app/core/settings.py:166-179`.
- Convention observed in `ai-workflow`: settings retrieval is cached.
  File reference: `app/core/dependencies.py:1-9`.

### Lifecycle & Infrastructure Style
- Convention observed in `ai-workflow`: startup creates infrastructure in a clear sequence: SurrealDB pool, Elasticsearch wrapper, DuckDB client.
  File reference: `app/core/factory.py:153-164`.
- Convention observed in `ai-workflow`: shutdown closes resources in reverse-like defensive cleanup blocks.
  File reference: `app/core/factory.py:170-185`.
- Convention observed in `ai-workflow`: partial startup failure still attempts cleanup.
  File reference: `app/core/factory.py:167-185`.
- Convention observed in `ai-workflow`: blocking infrastructure libraries are adapted through `anyio.to_thread.run_sync`.
  File reference: `app/infrastructure/elasticsearch/client.py:45-117`, `app/infrastructure/duckdb/client.py:86-140`.
- Convention observed in `ai-workflow`: async infrastructure uses explicit acquire and close semantics.
  File reference: `app/infrastructure/surrealdb/pool.py:105-145`.
- Convention observed in `ai-workflow`: health endpoints query infrastructure health checks rather than only checking object existence.
  File reference: `app/api/v1/endpoints/health.py:41-54`.

### Middleware Style
- Convention observed in `ai-workflow`: middleware ordering is treated as deliberate policy and documented in comments.
  File reference: `app/core/factory.py:97-102`.
- Convention observed in `ai-workflow`: security headers are injected centrally.
  File reference: `app/core/middleware.py:31-60`.
- Convention observed in `ai-workflow`: request IDs are propagated if supplied, otherwise generated.
  File reference: `app/core/middleware.py:86-104`.
- Convention observed in `ai-workflow`: request logs are structured via `extra={...}`.
  File reference: `app/core/middleware.py:144-164`.
- Convention observed in `ai-workflow`: rate limiting is a simple in-memory fixed window keyed by client IP.
  File reference: `app/core/middleware.py:221-306`.
- Convention observed in `ai-workflow`: metrics are in-memory only and track counts, durations, and statuses.
  File reference: `app/core/middleware.py:168-218`.

### Error-Handling Style
- Convention observed in `ai-workflow`: domain exceptions inherit from a framework-agnostic `DomainError`.
  File reference: `app/core/errors.py:1-26`.
- Convention observed in `ai-workflow`: request validation errors are converted to a standard envelope instead of exposing raw FastAPI defaults.
  File reference: `app/core/exceptions.py:45-95`.
- Convention observed in `ai-workflow`: validation error context is sanitized for JSON safety.
  File reference: `app/core/exceptions.py:25-42`.
- Convention observed in `ai-workflow`: all exception handlers return `ORJSONResponse`.
  File reference: `app/core/exceptions.py:45-130`.
- Convention observed in `ai-workflow`: handlers serialize errors using aliases and `exclude_none=True`.
  File reference: `app/core/exceptions.py:92-95`, `app/core/exceptions.py:110-113`, `app/core/exceptions.py:127-130`.
- Convention observed in `ai-workflow`: app-level exception handlers are registered centrally in the factory.
  File reference: `app/core/factory.py:209-211`.

### Testing Style
- Convention observed in `ai-workflow`: `tests/conftest.py` acts as a composition root for common fixtures.
  File reference: `tests/conftest.py:1-12`, `tests/conftest.py:61-111`.
- Convention observed in `ai-workflow`: tests supply explicit safe credentials to satisfy settings validation.
  File reference: `tests/conftest.py:64-78`.
- Convention observed in `ai-workflow`: async integration tests use in-process ASGI transport.
  File reference: `tests/conftest.py:104-111`.
- Convention observed in `ai-workflow`: app-boundary dependencies are replaced with dummy resources via monkeypatch in integration tests.
  File reference: `tests/integration/test_example_endpoints.py:81-91`.
- Convention observed in `ai-workflow`: error-path tests validate both status and envelope shape.
  File reference: `tests/unit/test_error_handler_integration.py:89-204`.
- Convention observed in `ai-workflow`: settings overrides may use `model_copy(update=...)` for isolation.
  File reference: `tests/conftest.py:94-101`.

### Auth Gap
- Convention observed in `ai-workflow`: auth infrastructure is not yet fleshed out in `app/`.
  File reference: repository inspection found no auth module under `app/`.
- Convention observed in `ai-workflow`: the error system is ready for unauthorized failures even though concrete auth dependencies are absent.
  File reference: `app/core/errors.py:18-26`, `app/contracts/errors.py:71-77`.
- Reviewer implication for this org: new auth code should likely follow the existing patterns of typed dependencies, domain exceptions, and centralized handlers.
  File reference: inferred from `app/api/v1/dependencies.py`, `app/core/errors.py`, `app/core/factory.py`.

### Reviewer Anchor For This Codebase
- Prefer `create_app(settings)` over ad hoc app construction.
  Why: that is the current composition root.
- Prefer typed dependency aliases over repeated raw `Depends(...)` signatures.
  Why: that is the current router style.
- Prefer services raising domain errors over routes raising `HTTPException` for business failures.
  Why: that is the current error-handling shape.
- Prefer contract models under `app/contracts` with `ConfigDict(extra="forbid")`.
  Why: that is the dominant DTO convention.
- Prefer lifespan-managed shared clients on `app.state`.
  Why: that is the existing singleton pattern.
- Prefer test-time provider overrides and dummy resources over monkeypatching deep internals.
  Why: that is the current testing seam.

## Appendix: Reviewer Defaults When Unsure

If a PR forces a choice and the codebase gives no stronger signal, anchor on these defaults:
- Route handlers stay thin.
  Why: transport is not the use-case layer.
- Services own business logic and usually own transaction boundaries.
  Why: workflows often touch more than one persistence concern.
- Repositories own persistence details and should not leak HTTP concerns upward.
  Why: dependency direction matters.
- Pydantic v2 is the baseline.
  Why: new v1 code is debt.
- Lifespan is the lifecycle anchor.
  Why: FastAPI recommends it.
- `dependency_overrides` is the preferred testing seam.
  Why: the framework provides it directly.
- Wildcard CORS is not acceptable for credentialed browser APIs.
  Why: FastAPI docs explicitly call out the limitation.
- A single `AsyncSession` must not be shared across concurrent tasks.
  Why: SQLAlchemy explicitly warns against it.
