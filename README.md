# Basic Banking Application

A beginner-friendly full-stack banking demo with a layered FastAPI backend and a responsive React dashboard. Users can create an account, sign in, view their balance, deposit, withdraw, transfer funds, and review transaction history.

## Technology

- Python 3.11 or later, FastAPI, Uvicorn, Pydantic v2, and pydantic-settings
- SQLAlchemy 2.x and SQLite
- PyJWT bearer tokens and bcrypt password hashing
- React, TypeScript, and Vite
- pytest and httpx

Backend versions are pinned in `requirements.txt`. The frontend dependencies and lockfile are in `frontend/`.

## Prerequisites

- Python 3.11+ (the project also works on newer Python versions)
- Node.js 20.19+ or 22.12+
- npm

## Install

From the project root, create a Python virtual environment and install the backend dependencies.

**Windows PowerShell**

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

If PowerShell blocks activation, run the environment's executable directly, for example `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`.

**macOS/Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Generate a unique secret and put it in `.env` as `SECRET_KEY`. For example:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

The development fallback key in the source is not suitable for a deployed application. Never commit `.env` or a production secret.

Install the frontend packages:

```powershell
cd frontend
npm install
cd ..
```

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./bank.db` | SQLAlchemy connection string |
| `SECRET_KEY` | Development-only fallback | Signs JWTs; set a long random value in `.env` |
| `ALGORITHM` | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access-token lifetime |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated allowed browser origins |

`frontend/.env.local` may set `VITE_API_BASE_URL` when the API is hosted at a different origin. During local development, Vite proxies `/api` to `http://127.0.0.1:8000`.

## Run the application

Start the backend from the project root. Tables are created automatically when the application starts.

```powershell
python -m uvicorn app.main:app --reload
```

Start the frontend in a second terminal:

```powershell
cd frontend
npm run dev
```

Open the Vite URL printed in the terminal, normally `http://localhost:5173`. Keep both servers running. The API is at `http://127.0.0.1:8000`.

## API documentation

FastAPI serves interactive Swagger documentation at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) and ReDoc at [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc).

The API routes are:

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/auth/register` | Register a user and automatically create their account |
| `POST` | `/api/auth/login` | Verify credentials and return a JWT |
| `POST` | `/api/auth/logout` | Revoke the current JWT |
| `GET` | `/api/accounts/me` | Return the signed-in user's account |
| `POST` | `/api/accounts/deposit` | Deposit a positive amount |
| `POST` | `/api/accounts/withdraw` | Withdraw a positive amount if funds are available |
| `POST` | `/api/accounts/transfer` | Transfer funds to another account |
| `GET` | `/api/accounts/transactions` | Return the signed-in user's transaction history |

Protected requests use `Authorization: Bearer <access-token>`. Login uses JSON with `email` and `password`. Swagger documents HTTP Bearer security on protected operations.

## Authentication and security

Passwords are hashed with bcrypt and password hashes are never included in response schemas. Login failures use the same `Invalid email or password` response for an unknown email and an incorrect password. JWTs contain the user ID in `sub`, an expiry in `exp`, and a unique token ID in `jti`.

The browser keeps the access token in `sessionStorage` for the active tab and attaches it to API requests. A `401` clears the token and returns the user to sign-in. Logout calls the API first and then clears browser state. This is appropriate for a student demo; as with any JavaScript-readable token storage, a production app should also invest in strong XSS protections or use a carefully designed secure, HttpOnly cookie flow.

Logout inserts the token ID and expiration into `blacklisted_tokens`; protected requests reject revoked tokens. Expired blacklist rows are removed during subsequent logout activity.

## Database design

SQLAlchemy models map to four SQLite tables:

- `users`: unique case-insensitive email, display name, bcrypt hash, and creation time
- `accounts`: one account per user, unique 10-digit account number, and `Numeric(12,2)` balance
- `transactions`: account, transaction type, amount, status, reference ID, and creation time
- `blacklisted_tokens`: unique JWT ID and token expiry

Money is represented with Python `Decimal` and SQL `Numeric(12,2)`, not floating point. Balances cannot be negative, and service validation prevents values above the column's maximum. Transfers produce a `TRANSFER_DEBIT` and `TRANSFER_CREDIT` row with the same reference ID.

The transfer service locks both account rows in ascending account-ID order where the database supports row locks and commits both balance changes and both ledger rows as one unit. If a write fails, the session rolls back. SQLite does not implement `SELECT ... FOR UPDATE`; its write-locking behavior is more limited than a production database, so this project does not promise high-concurrency transfer safety. Use a database with row-level locking for production workloads.

## Architecture and design decisions

HTTP routes in `app/api/` validate requests and serialize responses. `app/services/` owns authentication and money rules. `app/repositories/` contains database queries. `app/models/` defines SQLAlchemy tables, while `app/schemas/` defines Pydantic request and response models. `app/core/` and `app/db/` hold settings, security, and database setup.

The frontend deliberately keeps its page flow small: sign in/register, dashboard, account details, and transaction history. Deposit, withdrawal, and transfer use the same API contract as Swagger. The user interface is responsive and displays balances and ledger amounts in INR.

Errors use appropriate HTTP status codes: validation errors are `422`, unauthenticated requests are `401`, business-rule failures are `400`, missing accounts are `404`, and duplicate email is `409`. Unexpected server errors return a generic message without exposing exception details.

## Tests

Run the suite from the project root:

```powershell
python -m pytest -v
```

Tests use an in-memory SQLite database and cover registration, duplicate email, login, bearer authorization, logout revocation, account ownership, deposits, withdrawals, transaction history, transfers, and transfer rollback.

To build the frontend:

```powershell
cd frontend
npm run build
```

## Known limitations

- SQLite's locking model is not sufficient for high-volume concurrent banking operations.
- The app has no external payment rail; deposits and withdrawals are internal demo ledger actions.
- There is no password-reset flow, rate limiting, audit monitoring, or production deployment configuration.
- The frontend uses session-scoped bearer storage, not an HttpOnly cookie.

## Frontend/backend integration

The React app sends JSON to the FastAPI routes and includes the bearer token for protected requests. Vite forwards `/api` requests to the local backend, so the browser can use the same-origin development URL. Start both development servers as described above; the frontend cannot complete account operations while the backend is stopped.