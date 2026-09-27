# GovGraph — University Governance Mapping & Analytics

COMP3900 2026 T2 · Project 14 · Team **T18B-BANANA**

GovGraph is a proof-of-concept web platform that acts as a central source of
truth for institutional governance structures — committees, boards, working
groups, advisory panels — letting users register groups, track memberships,
visualise relationships, and analyse governance complexity.

## Repository layout
```
.
├── backend/            Flask + SQLAlchemy REST API (see backend/README.md)
├── frontend/           React + TypeScript + Vite SPA (see frontend/README.md)
├── docker-compose.yml  Local PostgreSQL
├── .env.example        Copy to .env and adjust
└── .github/workflows/  CI: lint + test (backend) and lint + build (frontend)
```

## Tech stack
| Layer     | Choice                                            |
|-----------|---------------------------------------------------|
| Frontend  | React 18 + TypeScript (Vite), React Flow          |
| Backend   | Python 3.10, Flask, SQLAlchemy                    |
| Database  | PostgreSQL (via Docker Compose)                   |
| CI        | GitHub Actions                                    |

## Quick start (one command)

**Prerequisites:** Docker Desktop. (Node 22+ and Python 3.10 are only needed
for the manual workflow below.)

```bash
cp .env.example .env          # 1. configure environment (first time only)
docker compose up --build     # 2. build + run db, backend, and frontend
```

Then open **http://localhost:5173**. The backend API is on
**http://localhost:5000** (Swagger UI at `/api/docs`) and Postgres on `5432`.
The backend auto-creates tables and seeds initial data on startup, so no
migration step is needed. Source is bind-mounted, so edits to `backend/` or
`frontend/` hot-reload inside the containers.

```bash
docker compose up --build -d  # run detached (in the background)
docker compose logs -f        # follow logs
docker compose down           # stop everything (add -v to also wipe the db volume)
```

Verify the stack: `curl http://localhost:5000/health` returns `{"status":"ok"}`.

### Manual workflow (without Docker for the apps)

<details>
<summary>Run the database in Docker but the backend/frontend on your host.</summary>

```bash
# 1. Configure environment
cp .env.example .env

# 2. Start PostgreSQL only
docker compose up -d db

# 3. Backend  (terminal A)
cd backend
python -m venv .venv && .venv/Scripts/activate   # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
flask --app wsgi run --debug                      # http://localhost:5000

# 4. Frontend (terminal B)
cd frontend
npm install
npm run dev                                       # http://localhost:5173
```
</details>

## Running checks
```bash
# Backend
cd backend && ruff check . && pytest -q
# Frontend
cd frontend && npm run lint && npm run build

# Frontend — unit tests (Vitest)
cd frontend && npm run test
```

## Testing

| Layer    | Framework | Location             | Command (from that folder) |
|----------|-----------|-----------------------|-----------------------------|
| Backend  | pytest    | `backend/tests/`      | `pytest -q`                |
| Frontend | Vitest    | `frontend/src/**/*.test.ts` | `npm run test`        |

**Backend**
```bash
cd backend
ruff check .     # lint
ruff format .    # auto-format
pytest -q        # tests — run against in-memory SQLite, no Postgres needed
```

**Frontend**
```bash
cd frontend
npm run lint     # eslint
npm run test     # vitest unit tests
```
Frontend tests currently cover the API client, URL normalisation, and the
New Group form adapters/helpers.

CI (`.github/workflows/ci.yml`) runs backend lint + `pytest` (with coverage)
and frontend lint + build on every push/PR. Frontend unit tests are not yet
wired into CI, so run `npm run test` locally before pushing frontend changes.

### Coverage report

Snapshot as of 2026-08-11, from a local run of the current test suites.
Regenerate with the commands below — coverage moves as tests are added, so
treat these numbers as a point-in-time reference, not a guarantee.

**Backend** — `cd backend && pytest -q --cov=app --cov-report=term-missing`

| Metric | Result |
|--------|--------|
| Tests  | 154 passed |
| Statement coverage | 91% (1,987 statements, 169 missed) |

Weakest spots: `app/db_init_seed.py` (69%), `app/routes/types.py` (69%),
`app/services/tor_submission_service.py` (79%), `app/services/type_service.py` (79%).
Most route and service modules sit at 90–100%.

**Frontend** — `cd frontend && npm run coverage`

| Metric | Result |
|--------|--------|
| Tests  | 46 passed (6 test files) |
| Statement coverage | 2.75% overall |

The frontend suite only covers pure logic modules so far — React
components and pages have no tests yet, which is why the overall number is
low:

| File | Statement coverage |
|------|---------------------|
| `src/api/url.ts` | 100% |
| `src/components/new-group/formAdapters.ts` | 96% |
| `src/components/new-group/types.ts` | 95% |
| `src/api/client.ts` | 17% |
| `src/auth/auth.ts` | 25% |
| All components, pages, and `App.tsx` | 0% |

## Backend

REST API for the GovGraph governance registry.

### Stack
- Python 3.10, Flask (app factory in `app/__init__.py`)
- SQLAlchemy ORM (`app/db_schema/`)
- PostgreSQL in dev (in-memory SQLite for tests)

Smoke test once running: `curl http://localhost:5000/health` → `{"status":"ok",...}`

### Schema changes (no migrations)

The app calls `db.create_all()` on startup. That creates **missing tables** but never `ALTER`s
an existing one, so a changed column on a table you already have in your Postgres volume is
silently ignored — it will work in tests (fresh in-memory SQLite every run) and fail on your
dev database.

The ToR lifecycle work reshaped `tor_submissions`, and the registration workflow
adds `users.is_active` plus `admin_registration_requests`. If you have an
existing volume, the simplest dev reset is:

```bash
docker compose down -v
docker compose up -d --build
```

If you need to preserve data, use migrations or run explicit `ALTER TABLE` /
`CREATE TABLE` statements. For the older ToR-only reset, either recreate the
volume (`docker compose down -v`) or run once:

```sql
DROP TABLE IF EXISTS tor_submissions;
DROP TYPE IF EXISTS torsubmissionstatus;
```

The second statement is the one people forget. A `Mapped[TorSubmissionStatus]` column creates a
**native Postgres ENUM type that survives the table drop**; leaving it behind means `create_all()`
reuses the stale 3-value type and every `rejected` write dies with `invalid input value for enum`.
Confirm the type name with `\dT` before assuming it.

This is safe because `tor_submissions` had no rows and no writers before this change.

### Backend layout
```
backend/
  app/
    __init__.py      app factory + db init + blueprint registration
    config.py        env-driven config (DATABASE_URL etc.)
    extensions.py    shared SQLAlchemy instance
    db_schema/       User, Person, GovernanceGroup, Membership, Relationship, submissions
    routes/          health + /api namespaces, with Swagger metadata
    services/        business logic and validation per domain
  tests/             pytest suite (uses in-memory SQLite)
  wsgi.py            entry point; loads ../.env then builds the app
```

### API documentation

The live API documentation is generated by Flask-RESTX:

- Swagger UI: `http://localhost:5000/api/docs`
- OpenAPI JSON: `http://localhost:5000/api/swagger.json`
- Shared DTO models: `backend/app/routes/swagger_models.py`
- Route namespaces: `backend/app/routes/*.py`

### API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness check |
| POST | `/api/auth/login` | Verify email/password and return auth profile + token |
| POST | `/api/register` | Register staff immediately, or submit an admin registration for review |
| GET | `/api/admin-registrations?scope=pending\|history` | Superuser-only admin registration queue/history |
| POST | `/api/admin-registrations/<id>/approve` | Superuser-only admin registration approval |
| POST | `/api/admin-registrations/<id>/reject` | Superuser-only admin registration rejection; comment required |
| POST | `/api/tor` | Submit a completed ToR form |
| POST | `/api/tor/check-duplicates` | Check a draft ToR for possible duplicate groups |
| GET | `/api/tor/<group_uuid>` | Return stored ToR JSON for a group/submission UUID |
| POST | `/api/tor/autofill` | Extract partial ToR form data from an uploaded document |
| GET | `/api/tor-submissions?scope=mine\|pending\|history` | List ToR submissions visible to the caller |
| POST | `/api/tor-submissions` | Save a ToR draft |
| GET | `/api/tor-submissions/<uuid>` | Fetch one ToR submission including form JSON |
| PUT | `/api/tor-submissions/<uuid>` | Update a draft or editable review submission |
| DELETE | `/api/tor-submissions/<uuid>` | Delete a draft |
| POST | `/api/tor-submissions/<uuid>/submit` | Submit a draft for review |
| POST | `/api/tor-submissions/<uuid>/approve` | Superuser-only ToR approval |
| POST | `/api/tor-submissions/<uuid>/reject` | Superuser-only ToR rejection |
| GET/POST | `/api/tor/entity_types` | List/add group entity types |
| GET/POST | `/api/tor/member_roles` | List/add membership role types |
| GET | `/api/tor/group_relation_types` | List relation types |
| GET | `/api/groups` | List/search governance groups |
| GET | `/api/groups/<uuid>` | Read one governance group |
| GET | `/api/person` | List/search people |
| GET | `/api/person/<uuid>` | Read one person, shaped by caller authority |
| GET | `/api/graph` | Governance graph nodes/edges |
| GET | `/api/analytics/*` | Superuser-only governance analytics endpoints |

## Frontend

Single-page app for exploring the governance graph and managing the registry.

### Stack
- React 18 + TypeScript, built with Vite
- `@xyflow/react` (React Flow) for the interactive governance graph
- `axios` for API calls, `react-router-dom` for routing

The dev server reads `VITE_API_BASE_URL` from the repo-root `.env`
(defaults to `http://localhost:5000/api`).

### Scripts
```bash
cd frontend
npm run dev         # start dev server
npm run build       # type-check + production build
npm run lint        # eslint
npm run typecheck   # tsc, no emit
npm run test        # vitest unit tests
```

### Frontend layout
```
frontend/
  src/
    main.tsx                    app entry
    App.tsx                     root layout
    api/client.ts               axios instance + typed endpoint wrappers
    types/governance.ts         shared types mirroring the backend contract
    components/GovernanceGraph.tsx   React Flow graph fed by GET /api/graph
```

## Team
| Name | Role |
|------|------|
| Jinhao Li | Product Owner + Backend |
| ZhengYu Chen | Backend + Database |
| Riyaz Mohamed Rabeek | Scrum Master + Backend |
| Raymond Zhuang | Frontend |
| Tim Faithfull | Backend |
| Johny Ha | Frontend |

## Commit Message Format

Here are some commit messagetags for reference:
Core Development Tags

Feat: New feature implementation
Fix: Bug fixes and error corrections
Hotfix: Critical/urgent bug fixes for production
Chore: Maintenance tasks, housekeeping, manual work
Refactor: Code restructuring without changing functionality
Perf: Performance improvements and optimizations
Revert: Reverting previous commits
Cleanup: Code cleanup, removing dead code
 
Documentation & Content Tags
 
Docs: Documentation updates, README changes
Style: Code formatting, whitespace, semicolons (no logic changes)
Comment: Adding or updating code comments
Typo: Fixing typos in code or documentation

Testing & Quality Tags

Test: Adding, updating, or fixing tests
Deploy: Deployment-related changes
 
Configuration & Setup Tags
 
Config: Configuration file changes
Env: Environment setup, variables, secrets
