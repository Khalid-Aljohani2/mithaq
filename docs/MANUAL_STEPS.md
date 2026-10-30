# MANUAL_STEPS — things only you can do

Everything here needs your accounts, your browser, or your credentials. Nothing
in this list has been done for you. Work top to bottom; (a) must come before (c).

Current state: nothing has been pushed anywhere. No remote exists, no database
has been created, no Vercel project exists.

---

## (a) Create the GitHub repository

The GitHub CLI is installed (`gh 2.102.0`) and you are logged in as
**`Khalid-Aljohani2`** with scopes `gist, read:org, repo, workflow` — enough to
create a repo and push, including the Actions workflow.

1. From the repo root `…\HUMAIN\PROJECT\ScopeGuardAi`, create the remote and push:

   ```powershell
   gh repo create mithaq --private --source=. --remote=origin --push
   ```

   Use `--public` instead of `--private` if the hackathon requires a public repo.
   Decide the name now — `mithaq` is suggested; the local folder stays
   `ScopeGuardAi` either way.

2. Confirm CI ran:

   ```powershell
   gh run list --limit 5
   gh run watch
   ```

   Expect three jobs: `backend (py3.11)`, `backend (py3.12)`, `frontend`.

3. **Check before you push:** `backend/.env` and `frontend/.env.local` are
   git-ignored and contain only local dev values. Verify nothing real is staged:

   ```powershell
   git status --short
   git ls-files | Select-String "\.env$|\.env\.local$"   # must return nothing
   ```

> If you want me to run step 1, say so — I stopped short deliberately because
> you said not to create or push to a remote yet.

---

## (b) Create the Postgres database (Supabase)

The database lives in **Supabase, AWS `eu-west-1` (Ireland)**. Pick that region
when you create the project — the Vercel function is pinned to Dublin to sit
beside it, and moving one without the other throws the latency away.

1. supabase.com → **New project**.
   - Region: **West EU (Ireland) / eu-west-1**
   - Set a strong database password and save it in your password manager. You
     cannot read it back later, only reset it.
2. Project → **Connect** (or Settings → Database → Connection string).

### You need BOTH pooler strings. They are not interchangeable.

Supabase offers two poolers on different ports, and this project uses each for
a different job:

| | Session pooler | Transaction pooler |
|---|---|---|
| Port | **5432** | **6543** |
| Used by | **you**, running migrations from your machine | **Vercel**, at runtime |
| Why | holds one session for the whole connection, which DDL and Alembic's advisory locks need | one short-lived server session per transaction, which is what a serverless function wants |
| IPv4 | yes — works on a normal home/office connection | yes |
| Prepared statements | supported | **not supported** — handled in code, see below |

Both look like:

```
postgresql://postgres.<project-ref>:<PASSWORD>@aws-0-eu-west-1.pooler.supabase.com:5432/postgres   # session
postgresql://postgres.<project-ref>:<PASSWORD>@aws-0-eu-west-1.pooler.supabase.com:6543/postgres   # transaction
```

> Do **not** use the "Direct connection" string. It is IPv6-only on the free
> tier, so it will usually fail from a home connection, and it is the wrong
> shape for serverless.

You do not need to rewrite the `postgresql://` prefix — `app/db/engine.py`
rewrites it to `postgresql+psycopg://` for you. Append `?sslmode=require` if
Supabase has not already.

### Run migrations and seed — from your machine, with the SESSION string (5432)

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
$env:DATABASE_URL = "postgresql://postgres.<ref>:<PASSWORD>@aws-0-eu-west-1.pooler.supabase.com:5432/postgres"
alembic upgrade head
python -m app.seed.load
Remove-Item Env:\DATABASE_URL     # don't leave a password in your shell
```

`python -m app.seed.load` is idempotent — running it twice inserts nothing the
second time.

> Migrations through the **transaction** pooler (6543) can fail or behave
> oddly: Alembic takes a session-level advisory lock and issues DDL, and the
> transaction pooler may hand each statement a different server session. Use
> 5432 for this and 6543 only for the running app.

### Prepared statements — already handled, nothing for you to do

The transaction pooler does not support prepared statements. `app/db/engine.py`
passes `prepare_threshold=None` to psycopg on every connection, which disables
them. There is a test that opens a real connection and asks Postgres whether
anything was prepared, with a control case proving the assertion is not
vacuous. You do not need to add anything to the connection string.

---

## (c) Create the Vercel projects

**Two separate projects from the same repository**, distinguished by their Root
Directory. Do (a) first — both import from GitHub.

### Project 1 — backend

| Setting | Value |
|---|---|
| Import from | your GitHub repo |
| **Root Directory** | `backend` |
| Framework Preset | Other / auto-detected (FastAPI) |
| Build Command | leave default |

Environment variables (Settings → Environment Variables):

| Name | Value | Notes |
|---|---|---|
| `DATABASE_URL` | the **transaction** pooler string, port **6543** | **required** — not the 5432 one |
| `ALLOWED_ORIGINS` | `https://<frontend-project>.vercel.app` | add `,http://localhost:3000` if you want to point a local frontend at prod |
| `DEMO_RESET_TOKEN` | a long random string you invent | omit entirely to disable `/api/demo/reset` (it 404s) |

Nothing else is needed: Vercel finds the FastAPI instance named `app` at
`backend/app/main.py` by convention. `backend/vercel.json` sets two things:

- `"regions": ["dub1"]` — Dublin, Ireland (`eu-west-1`), the same region as the
  Supabase database. Vercel Functions otherwise default to `iad1` (Washington
  D.C.), which would put every query on a transatlantic round trip.
  **Hobby allows a single region, so one entry is fine**; two or more would
  fail the deployment before the build step.
- `"maxDuration": 60` for the function.

**Python version:** `backend/.python-version` pins **3.12**. Vercel supports
3.12 / 3.13 / 3.14 only — **3.11 is not available there**, even though that is
what we develop on locally. CI tests both 3.11 and 3.12 for this reason.

After the first deploy, check:

```
https://<backend-project>.vercel.app/api/health     ->  {"status":"ok"}
https://<backend-project>.vercel.app/docs           ->  OpenAPI UI
```

### Project 2 — frontend

| Setting | Value |
|---|---|
| Import from | the same GitHub repo |
| **Root Directory** | `frontend` |
| Framework Preset | Next.js (auto-detected) |

Environment variables:

| Name | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://<backend-project>.vercel.app` — **no trailing slash** |

This is the **only** source of the backend URL. Outside development there is no
fallback: if the variable is missing the app says so instead of quietly calling
localhost.

### The ordering trap

`ALLOWED_ORIGINS` (backend) and `NEXT_PUBLIC_API_URL` (frontend) each need the
other project's URL, so:

1. Deploy the backend. Note its URL.
2. Create the frontend with `NEXT_PUBLIC_API_URL` = the backend URL. Deploy. Note its URL.
3. Go back to the backend and set `ALLOWED_ORIGINS` = the frontend URL.
4. **Redeploy the backend** — environment variable changes do not apply to an
   existing deployment.

If the page shows `unreachable`, this step is almost always why: open the
browser console and look for a CORS error naming the frontend origin.

---

## Quick reference — every secret and where it lives

| Secret | Local | Vercel backend | Vercel frontend | In git? |
|---|---|---|---|---|
| `DATABASE_URL` (6543 transaction) | `backend/.env` (local Docker) | ✅ | — | ❌ never |
| Supabase DB password | password manager | via `DATABASE_URL` | — | ❌ never |
| `DEMO_RESET_TOKEN` | `backend/.env` | ✅ | — | ❌ never |
| `ALLOWED_ORIGINS` | `backend/.env` | ✅ | — | not secret |
| `NEXT_PUBLIC_API_URL` | `frontend/.env.local` | — | ✅ | not secret, **public to the browser** |
| `LLM_API_KEY` | `backend/.env` (Step 4) | ✅ (Step 4) | — | ❌ never |

`backend/.env` and `frontend/.env.local` are git-ignored. Only the
`.env.example` / `.env.local.example` files are tracked, and both carry empty
values.
