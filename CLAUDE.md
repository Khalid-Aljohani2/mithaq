# CLAUDE.md — Mithaq

## Product

**Mithaq** (ميثاق — Arabic for a binding covenant between two parties).

> One contract. Two parties. One record of every change.

Mithaq reads a project's **Statement of Work (SOW)**, checks each incoming
client request against it, and — when a request is **out of scope** — drafts a
**change request with a cost quote**.

The name is the product thesis: the SOW is the covenant, and every request is
judged against it rather than against memory or goodwill.

24-hour hackathon MVP. Optimise for a working demo, not for completeness.

## Architecture

Two processes that talk **only over HTTP JSON**. No shared code, no RPC, no
server-side rendering of backend data at build time.

```
ScopeGuardAi/
├── frontend/                  Next.js 16, App Router, TypeScript, Tailwind v4
│   ├── src/app/               routes (page.tsx, layout.tsx, globals.css)
│   ├── src/components/ui/     shadcn/ui components (button, card, input, textarea, badge)
│   ├── src/lib/               api.ts (typed backend client), utils.ts (cn)
│   ├── .env.local.example     NEXT_PUBLIC_API_URL
│   └── components.json        shadcn config (style: radix-nova)
├── backend/                   FastAPI + Pydantic v2
│   ├── app/main.py            app factory, CORS, router wiring
│   ├── app/config.py          pydantic-settings Settings + get_settings()
│   ├── app/routers/           one module per resource (health.py)
│   ├── app/schemas/           Pydantic request/response models
│   ├── app/services/          business logic (SOW parsing, scope checks, quoting)
│   ├── tests/                 pytest
│   ├── .venv/                 virtualenv (git-ignored)
│   ├── requirements.txt       runtime deps, exact pins
│   ├── requirements-dev.txt   dev deps, exact pins
│   ├── pyproject.toml         ruff + pytest config
│   └── .env.example           LLM_PROVIDER, LLM_API_KEY, LLM_MODEL
├── CLAUDE.md
├── README.md
├── SOURCES.md
└── .gitignore
```

## Run commands — Windows 11, PowerShell 5.1

Backend (terminal 1):

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

Frontend (terminal 2):

```powershell
cd frontend
npm run dev
```

Quality gates:

```powershell
# backend
cd backend; .\.venv\Scripts\Activate.ps1; ruff check .; ruff format --check .; pytest

# frontend
cd frontend; npm run lint; npm run typecheck; npm run build
```

Hit the API without a browser (PowerShell aliases `curl` to `Invoke-WebRequest`,
so call the real binary):

```powershell
curl.exe http://localhost:8000/api/health
```

## Rules

1. **One step at a time.** Do the current step, stop, report, wait. Never start
   the next step unprompted.
2. **Official sources only.** Install commands and setup flags come from the
   tool's own docs (nextjs.org, ui.shadcn.com, fastapi.tiangolo.com,
   pydantic.dev, motion.dev, docs.astral.sh). Record the URL in `SOURCES.md`.
   If something can't be verified from an official source, say so — don't guess.
3. **No new dependency without asking first.** Name the package, the version,
   why it's needed, and wait for a yes.
4. **Versions are checked, not remembered.** Query the npm registry or PyPI at
   install time. Pin exact versions — no `^`, no `~`, no ranges.
5. **Secrets stay out of git.** Real keys live only in `backend/.env` and
   `frontend/.env.local`, both git-ignored. Example files carry empty values.
   Never write a real key into any tracked file.
6. **TypeScript strict stays on.** No `any`, no `@ts-ignore`, no disabling
   `strict` in `tsconfig.json`.
7. **A Pydantic model for every API request and response.** Routes declare
   `response_model=`; no bare dicts crossing the HTTP boundary.
8. **Run lint, type check and tests before reporting a step done.** Show the
   real output. Never summarise a check you didn't run.

## Conventions

- Backend imports are absolute from the `app` package (`from app.config import ...`).
- Frontend fetches the backend from the **browser** (client components), so the
  production build never needs the API to be up.
- The API base URL comes from `NEXT_PUBLIC_API_URL`, never hardcoded in a component.
- CORS allows `http://localhost:3000` only; widen it deliberately, not by habit.
- Frontend types that mirror backend schemas live in `src/lib/api.ts` and are
  kept in sync by hand — if a Pydantic model changes, change the TS type too.
