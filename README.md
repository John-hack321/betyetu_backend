# PeerStake Backend

FastAPI backend for the PeerStake platform: football fixtures, user wallets, staking flows, and LMSR-powered prediction markets (binary, fixture-based, and group markets).

## What This Service Does

- Provides authenticated user APIs for:
  - account/profile access
  - deposits/withdrawals
  - fixture discovery
  - public/private staking flows
  - prediction market discovery and trading
- Provides admin APIs for:
  - league/fixture ingestion and management
  - market and stake management
  - season operations
- Runs background scheduling logic for polling and data updates.
- Exposes websocket functionality through Socket.IO integration.
- Persists data in PostgreSQL using SQLAlchemy + Alembic migrations.
- Uses Redis for cache-oriented flows (for example popular leagues data workflows).

## Tech Stack

- Python 3.10+
- FastAPI
- SQLAlchemy (async)
- Alembic
- PostgreSQL
- Redis
- APScheduler
- Socket.IO

## Project Structure

- `main.py` - app bootstrap, middleware, lifespan startup/shutdown, router registration
- `api/` - public/authenticated/admin route handlers
- `db/` - database setup and ORM models
- `alembic/` - schema migration history
- `services/` - market math, trade execution, polling, sockets, caching, email, M-Pesa
- `pydantic_schemas/` - request/response contracts
- `scripts/` - utility scripts (including showcase seed script)

## Core Feature Areas

### 1) Authentication and User Identity

- User signup/login with access + refresh token flow.
- Password reset request flow via email service.
- Token-based authorization for user-protected endpoints.
- Separate admin auth surface.

Routes (prefixes):
- `/auth`
- `/users`
- `/admin/auth`
- `/admin/users`

### 2) Fixtures and Leagues

- Fetch paginated fixtures for users.
- Fetch available/popular leagues.
- Admin operations for adding leagues and importing fixtures.
- Admin controls for fixture lifecycle (mark live, log live scores, delete fixtures).

Routes:
- `/fixtures`
- `/leagues`
- `/admin/fixtures`
- `/admin/leagues`
- `/admin/seasons`

### 3) Stakes

- Initiate stake
- Join stake
- Cancel stake
- Query user stakes and public stakes
- Admin winner/settlement operations

Routes:
- `/stakes`
- `/unique_stakes`
- `/admin/stakes`

### 4) Prediction Markets (LMSR)

- Unified market listing endpoint for:
  - binary prediction markets
  - fixture-based 3-way markets
  - group markets with sub-markets
- Buy/sell quote previews
- Trade execution (buy/sell)
- Positions and price history APIs
- User market proposal flow

Routes:
- `/prediction_markets`
- `/admin/prediction_markets`

### 5) Transactions and Payments

- Deposit initiation/checking
- Withdrawal initiation and callbacks/timeouts
- M-Pesa service integration hooks

Routes:
- `/transactions`

## Environment Variables

Create `.env` for local development and `.env.prod` for production-like overrides.

Minimum/high-impact variables:

- `PROD_DATABASE_URL` - Async SQLAlchemy PostgreSQL URL (e.g. `postgresql+asyncpg://...`)
- `AUTH_SECRET_KEY`
- `AUTH_ALGORITHM`
- `REFRESH_ALGORITHM`
- `ADMIN_AUTH_SECRET_KEY`
- `ADMIN_AUTH_ALGORITHM`
- `ADMIN_REFRESH_ALGORITHM`
- `ALLOWED_ORIGINS`
- `FRONTEND_URL`

Payment/email/cache variables depend on your deployment setup and service keys.

## Local Development Setup

1. Clone repository and enter backend folder.
2. Create virtual environment and install dependencies.
3. Configure environment variables.
4. Run migrations.
5. Start the API server.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

API docs:
- `http://localhost:8000/docs`
- `http://localhost:8000/redoc`

## Database and Migrations

Apply latest migrations:

```bash
alembic upgrade head
```

Create a new migration:

```bash
alembic revision --autogenerate -m "describe change"
```

## Seeding Showcase/Demo Data

Use the script below to populate realistic demo data for fixtures and markets:

- `scripts/seed_showcase_data.py`
- Detailed usage: `scripts/README.md`

Quick run:

```bash
python scripts/seed_showcase_data.py --yes
```

Reset and reseed:

```bash
python scripts/seed_showcase_data.py --reset --yes
```

## Deployment Notes

### Self-hosting for Demo/Assessment

- Run backend with `uvicorn` and expose with ngrok/cloudflared.
- Keep machine online while assessment is ongoing.
- Prefer `tmux`/`systemd` so process survives shell/session drops.

### CORS

- For temporary demo debugging, this backend may be configured to allow all origins.
- For production, lock CORS to explicit frontend domains only.

## Troubleshooting

### Frontend gets no data / network errors

Check in browser network tab:
- API base URL points to correct backend URL.
- CORS preflight (`OPTIONS`) succeeds.
- Auth token is sent for protected endpoints (`/users/me`, `/fixtures`, etc).

### Token issues (401)

- Ensure frontend and backend use the same auth secret and algorithms.
- Confirm token is not expired and is included as `Authorization: Bearer <token>`.

### Empty fixtures

- Verify fixtures exist in DB and match filtering criteria (status/date windows).
- Confirm request reaches backend (not blocked by CORS first).

## Current API Prefix Map

- `/auth`
- `/users`
- `/transactions`
- `/fixtures`
- `/leagues`
- `/stakes`
- `/prediction_markets`
- `/admin/auth`
- `/admin/users`
- `/admin/seasons`
- `/admin/stakes`
- `/admin/fixtures`
- `/admin/leagues`
- `/admin/prediction_markets`

## Security Reminder

- Never commit real secrets or production DB passwords.
- Rotate any credential that was ever committed to source control.
- Limit CORS and callback URLs to known trusted origins.

