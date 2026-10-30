# CLAUDE.md — Mithaq

## Product

**Mithaq** (ميثاق — Arabic for a binding covenant between two parties).

> One contract. Two parties. One record of every change.

Mithaq is an **Arabic-first change-order governance agent for Saudi government
contracts**. It serves **both parties of the same contract**:

- the **government entity**, which must keep change orders within the legal limits;
- the **contractor**, which must make sure every extra request is documented,
  priced and formally assigned before any work starts.

Both parties share **one change ledger per contract**. There is no second set of
books: the same cumulative totals, caps and headroom are shown to each side, and
each side sees only the actions its own role may take.

The name is the product thesis: the contract is the covenant, and every request
is judged against it rather than against memory or goodwill.

## Legal basis

The **Government Tenders and Procurement Law** (نظام المنافسات والمشتريات الحكومية),
published in Umm Al-Qura on **4 September 2026** (1448-03-22), replacing the law
issued by Royal Decree M/128 of 1440/11/13H, and effective **120 days after
publication** (Article 101).

Official source: <https://www.uqn.gov.sa/decisions-and-regulations/4001762>

The verbatim Arabic text of every article the engine relies on lives in
`backend/app/regulations/gtpl_2026.yaml`, copied programmatically from that page
and asserted to be a substring of it. Rules:

- **Never write legal text from memory.** Fetch it, copy it, verify it.
- **All percentages live in the YAML**, never in Python.
- Ambiguous articles carry `interpretation_note` and `needs_legal_review: true`.
- The executive regulations (اللائحة, Article 99) are not published yet, so no
  rule may depend on them (see WON'T in the requirements).

## Spec of record

**[docs/REQUIREMENTS.md](docs/REQUIREMENTS.md)** governs this build: FR-01 to FR-19
and NFR-01 to NFR-14, prioritised MUST / SHOULD / WON'T. Read it before starting any
step. Every later step must satisfy it, and work is judged against it — not against
what seems reasonable at the time. When a step is reported done, name the requirement
IDs it satisfies. If a requirement looks wrong or unachievable, say so and wait;
do not quietly reinterpret or drop it.

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
│   ├── app/dependencies.py    injected repository + limits
│   ├── app/domain/            enums, models, RuleResult types (no I/O)
│   ├── app/regulations/       gtpl_2026.yaml + loader - the only home for percentages
│   ├── app/repositories/      storage interface + in-memory impl (Postgres in Step 3)
│   ├── app/routers/           one module per resource (health, contracts, change_orders)
│   ├── app/schemas/           Pydantic request/response models
│   ├── app/seed/              fictional demo contract
│   ├── app/services/          rules_engine.py (pure) + change_orders.py (workflow)
│   ├── tests/                 pytest
│   ├── .venv/                 virtualenv (git-ignored)
│   ├── requirements.txt       runtime deps, exact pins
│   ├── requirements-dev.txt   dev deps, exact pins
│   ├── pyproject.toml         ruff + pytest config
│   └── .env.example           LLM_PROVIDER, LLM_API_KEY, LLM_MODEL
├── docs/
│   ├── REQUIREMENTS.md        spec of record - FR-01..19, NFR-01..14
│   └── decisions/             short decision records (NFR-11)
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
9. **`docs/REQUIREMENTS.md` is binding.** Every step must satisfy it. Cite the
   FR/NFR ids a step delivers when reporting it done. Requirements marked WON'T
   are out of scope — don't build them.
10. **The model never decides money, percentages or legal limits.** Those come
    from `rules_engine.py` reading the regulation YAML. An LLM may read, draft
    and classify; it may not compute a cap or price an existing item (NFR-03).
11. **Every legal assertion cites its article.** Violations, warnings and consent
    requirements all carry `article_ref_ar` and `article_ref_en` (NFR-02).

## Conventions

- Backend imports are absolute from the `app` package (`from app.config import ...`).
- Frontend fetches the backend from the **browser** (client components), so the
  production build never needs the API to be up.
- The API base URL comes from `NEXT_PUBLIC_API_URL`, never hardcoded in a component.
- CORS allows `http://localhost:3000` only; widen it deliberately, not by habit.
- Frontend types that mirror backend schemas live in `src/lib/api.ts` and are
  kept in sync by hand — if a Pydantic model changes, change the TS type too.
