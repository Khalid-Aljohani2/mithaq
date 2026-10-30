# Mithaq

**ميثاق** — Arabic for a binding covenant between two parties.

> One contract. Two parties. One record of every change.

Reads a project's Statement of Work (SOW), checks each incoming client request
against it, and — when a request falls outside the agreed scope — drafts a
change request with a cost quote.

Hackathon MVP. Next.js front end, FastAPI back end, talking only over HTTP JSON.

## Requirements

**[docs/REQUIREMENTS.md](docs/REQUIREMENTS.md)** is the spec of record — **v2**,
built around an 11-step change-order workflow reviewed with a senior project
manager. 22 functional requirements (FR-01 to FR-22) and 16 non-functional ones
(NFR-01 to NFR-16), split into MUST / SHOULD / WON'T.

Its control principle governs the whole system: **AI analyses, validates,
recommends and drafts; authorised people approve every contractual or financial
commitment.** The agent never decides.

[docs/REQUIREMENTS_v1.md](docs/REQUIREMENTS_v1.md) is kept for history. Where the
two disagree, v2 wins.

## Layout

```
ScopeGuardAi/
├── frontend/   Next.js 16 (App Router, TypeScript, Tailwind v4, shadcn/ui, Motion)
├── backend/    FastAPI + Pydantic v2
├── docs/       REQUIREMENTS.md (spec of record, v2), decisions/, MANUAL_STEPS.md
├── CLAUDE.md   Working rules for this repo
├── SOURCES.md  Every dependency, its pinned version, and the doc it came from
└── README.md
```

## Prerequisites

| Tool   | Version used |
| ------ | ------------ |
| Node   | 22.14.0 (Next.js 16 requires >= 20.9) |
| npm    | 10.9.2 |
| Python | 3.11.9 |
| git    | 2.55.0 |

## Setup

```powershell
# Backend
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env

# Frontend
cd ..\frontend
npm install
Copy-Item .env.local.example .env.local
```

## Run (two terminals, Windows PowerShell)

```powershell
# Terminal 1 - backend on http://localhost:8000
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000

# Terminal 2 - frontend on http://localhost:3000
cd frontend
npm run dev
```

Open http://localhost:3000 — the card shows the backend health status.
API docs are at http://localhost:8000/docs.

## Checks

```powershell
# Backend
cd backend; .\.venv\Scripts\Activate.ps1; ruff check .; ruff format --check .; pytest

# Frontend
cd frontend; npm run lint; npm run typecheck; npm run build
```
