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

## (b) Create the Postgres database

You need a **managed** Postgres that Vercel Functions can reach, with a
**pooled** connection string and SSL. The local Docker container is for
development only and is not reachable from Vercel.

Pick one provider:

| Provider | Where | Notes |
|---|---|---|
| **Vercel Postgres / Neon** (simplest) | Vercel dashboard → Storage → Create Database | Integrates with the project and sets the env var for you |
| **Neon** direct | neon.tech | Free tier, serverless-friendly pooler |
| **Supabase** | supabase.com | Use the **Session pooler** string, not the direct one |

### What to copy

Take the **pooled / connection-pooling** string, not the direct one. Serverless
functions open many short connections, which is exactly what a direct
connection is bad at. It will look roughly like:

```
postgresql://USER:PASSWORD@HOST-pooler.REGION.provider.tech/DBNAME?sslmode=require
```

You do **not** need to rewrite the prefix — `postgres://` and `postgresql://`
are both rewritten to `postgresql+psycopg://` automatically in
`backend/app/db/engine.py`.

### Where to put it

| Where | Variable | Value |
|---|---|---|
| Vercel **backend** project | `DATABASE_URL` | the pooled string |
| Your machine (optional) | `backend/.env` → `DATABASE_URL` | already points at local Docker |

### Then create the schema and seed it — once

From your machine, with `DATABASE_URL` temporarily set to the **production**
string:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
$env:DATABASE_URL = "postgresql://...pooled...?sslmode=require"
alembic upgrade head
python -m app.seed.load
Remove-Item Env:\DATABASE_URL     # don't leave it in your shell
```

`python -m app.seed.load` is idempotent — running it twice inserts nothing the
second time, so it is safe to re-run.

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
| `DATABASE_URL` | pooled Postgres string from (b) | **required** |
| `ALLOWED_ORIGINS` | `https://<frontend-project>.vercel.app` | add `,http://localhost:3000` if you want to point a local frontend at prod |
| `DEMO_RESET_TOKEN` | a long random string you invent | omit entirely to disable `/api/demo/reset` (it 404s) |

Nothing else is needed: Vercel finds the FastAPI instance named `app` at
`backend/app/main.py` by convention, and `backend/vercel.json` only raises
`maxDuration` to 60s.

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
| `DATABASE_URL` | `backend/.env` | ✅ | — | ❌ never |
| `DEMO_RESET_TOKEN` | `backend/.env` | ✅ | — | ❌ never |
| `ALLOWED_ORIGINS` | `backend/.env` | ✅ | — | not secret |
| `NEXT_PUBLIC_API_URL` | `frontend/.env.local` | — | ✅ | not secret, **public to the browser** |
| `LLM_API_KEY` | `backend/.env` (Step 4) | ✅ (Step 4) | — | ❌ never |

`backend/.env` and `frontend/.env.local` are git-ignored. Only the
`.env.example` / `.env.local.example` files are tracked, and both carry empty
values.
