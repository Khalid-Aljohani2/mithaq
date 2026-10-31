# Mithaq · ميثاق

> **One contract. Two parties. One record of every change.**

Mithaq is an Arabic-first change-order governance agent for Saudi government
contracts. Both sides of the same contract — the government entity and the
contractor — work from **one shared change ledger**. A change request arrives as
free Arabic prose; eleven named stages read it, match it against the contract's
priced breakdown, price it from the contract's own unit rates, check it against
both the organisation's policy and Article 67 of the new procurement law, and
produce a recommendation with the article it rests on. **The agent never
decides.** Authorised people approve every commitment, and the system refuses an
approval that would take the contract past a statutory cap — even when every
individual request looked fine on its own.

---

## The problem

Change orders are where construction contracts quietly go wrong. Not because
anyone acts in bad faith, but because the paperwork moves slower than the work,
and nobody is adding it up.

The 2021 joint study by the **U.S. Army Corps of Engineers and the Associated
General Contractors of America** measured the gap on federal construction
contracts:

| Finding | Figure |
|---|---|
| Contractor's time to submit a proposal after a request | **~30 days** on average |
| Government's time to issue the modification after receiving it | **~90 days** on average, **55 days** median |
| Difference between the two sides' recorded start date **for the same change** | **~30 days** on average |

Source: [*Construction Contract Modifications: A Joint Study by USACE and
AGC*](https://www.agc.org/sites/default/files/USACE-AGC%20Joint%20Study%20on%20Construction%20Contract%20Modifications.pdf)
(February 2021). The first two rows were verified against the primary PDF,
page 2: a contractor submitted a proposal in about 30 days from the request for
proposal on average, and the Government issued the modification within 90 days
of proposal receipt on average, with a median of 55 days. The third row has not
yet been checked against the PDF; see
[`SOURCES.md`](SOURCES.md#problem-statement-figures-checked-2026-10-31).

That last row is the one Mithaq is built around. The two parties did not
disagree about the money — they disagreed about **when the change began**,
because each kept its own record. Months of work proceed while a change is
undocumented, and the cumulative position is known to nobody until an audit.

### Why now

Saudi Arabia's **Government Tenders and Procurement Law** (نظام المنافسات
والمشتريات الحكومية) was published in Umm Al-Qura on **4 September 2026** and
takes effect **120 days after publication** (Article 101).

**[Article 67](backend/app/regulations/gtpl_2026.yaml)** caps change orders
cumulatively:

| Cap | Limit | Nature |
|---|---|---|
| New items — Article 67(1)(a) | 10% of contract value | blocking |
| Increases to existing items — 67(1)(b) | 20% | blocking |
| Decreases — 67(1)(c) | 20% | blocking |
| New items and increases together — 67(2) | 20% | blocking |

Blocking means what it says: **no internal approval lifts a legal cap.** A
cumulative cap is only a cap if somebody is keeping the running total — which is
exactly the thing the 30-day record gap above makes impossible on paper.

The verbatim Arabic of every article the engine relies on is stored in
[`gtpl_2026.yaml`](backend/app/regulations/gtpl_2026.yaml), copied
programmatically from the official page and asserted to be a substring of it.
**No legal text in this repository was written from memory.**

---

## What it looks like

**The shared workspace** — the same ledger, the same totals, for both parties.

![Workspace](docs/design/screens/workspace-government-1440-light.png)

**The case file**, with the eleven-stage agent trace. Every stage shows who
produced it: 🤖 a model, 📋 deterministic code, or ✍️ a person.

![Case file with the agent trace](docs/design/screens/case-vo-issued-1440-light.png)

**The approval seal.** A signature is a person's act, stamped with their name
and the time.

![Approval chain and seal](docs/design/screens/case-in-approval-my-step-1440-light.png)

**The variation order**, assembled by code and printable to a single A4 page,
citing the articles it rests on.

![Variation order document](docs/design/screens/vo-document-government-1440-light.png)

**The limits page near the ceiling** — 945,000 approved against a 960,000
Article 67 cap, with 135,000 more pending and 15,000 of headroom left.

![Limits page near the Article 67 cap](docs/design/screens/limits-near-cap-1440-light.png)

**The refusal.** The final signature on the eighth request is refused, in
Arabic, naming Article 67(1)(b) and Article 67(2).

![Final approval refused under Article 67](docs/design/screens/case-refused-at-final-1440-light.png)

**The evaluation page**, served from a committed measurement — not a claim.

![Evaluation results](docs/design/screens/evaluation-1440-light.png)

> Every screen above is captured by an automated Playwright run against a real
> backend ([`SCREENSHOTS.md`](docs/design/SCREENSHOTS.md)), at 1440 px and
> 390 px, light and dark. Nothing here is a mockup.

---

## How it works

Eleven stages, each a named agent in the trace with its own inputs, outputs,
actor and duration.

| # | Stage | Who does it | Why |
|---|---|---|---|
| 1 | Intake | **AI** | free Arabic prose → structured fields |
| 2 | Document validation | code | a checklist is a set comparison |
| 3 | Contract & scope analysis | **AI** | matching prose to breakdown lines is semantic |
| 4 | Technical assessment | **AI** | comparing a request to a specification is semantic |
| 5 | Cost & schedule impact | **code** | arithmetic over contract unit rates |
| 6 | Risk & compliance | code finds, **AI** narrates | the legal and policy results are computed; the prose is not |
| 7 | Orchestrator | **code decides**, AI narrates | the recommendation and the approval chain are rules |
| 8 | Human approval gate | **people** | role and order checks; only humans decide |
| 9 | Issue variation order | code assembles, AI drafts | values and citations are computed; the Arabic wording is drafted |
| 10 | Update project records | code | ledger and baseline arithmetic |
| 11 | Execution & follow-up | code | recording actuals and deviations |

AI is used at four stages and narrates two more. Everything that touches money,
a percentage or a legal limit is deterministic code reading a configuration
file. See [decision 0001](docs/decisions/0001-pipeline-design.md).

### The design principle

> **AI reads. Code decides money and law. People approve.**

This is not a slogan in a document — it is enforced structurally, as NFR-15:

- **AI output schemas contain no money, status or state fields.** A model
  *cannot* return a cost impact or an approval status, because there is nowhere
  in the schema to put one.
- **Provider methods take a schema and nothing else** — no repository, no
  session, no clock. An AI stage has no route to storage.
- **The state machine refuses committing transitions from an `AI` actor.**
  Entering approval, approving, issuing a VO: every one is in
  `COMMITTING_TRANSITIONS` and restricted to `HUMAN` or `CODE`, whatever a model
  returns.
- **Prompt injection** (NFR-04): request text is wrapped in explicit delimiters,
  markers inside the text are neutralised, and the text never enters the system
  prompt. 3 of 3 injection attempts in the evaluation set were turned away.

A missing AI narrative changes the *wording* of a recommendation and nothing
else. That is the test of whether the boundary is real.

---

## The cumulative protection

A 25% increase refused as one request can be waved through as five requests of
5% if nobody is adding them up. That evasion is the reason Article 67's caps are
cumulative, and it is what Mithaq is for.

The end-to-end test
([`test_ledger_accumulation.py`](backend/tests/test_ledger_accumulation.py))
drives it over HTTP on the government contract, whose value is 4,800,000 SAR:

1. **Eight requests of 135,000 SAR each** are submitted and analysed *before any
   is approved* — so every one is judged against the ledger as it stood, and
   every one is recommended for approval. **No single request ever looks wrong.**
2. **Seven are approved**, reaching **945,000 of the 960,000 cap** (19.69%).
   Each is a real approval by a real chain, each with its variation order
   issued.
3. **The eighth is refused at its final signature.** 1,080,000 would be 22.5%.
   The response is `409 LEGAL_CAP_EXCEEDED`, citing **Article 67(1)(b)** and
   **Article 67(2)**.

```
slice 7: approved. cumulative INCREASE_EXISTING = 945000
slice 8: REFUSED at final approval
    code     : LEGAL_CAP_EXCEEDED
    articles : ('Article 67(1)(b)', 'Article 67(2)')
```

The check runs at the **final** approval, not the first, because that is the
moment the commitment is made — and between analysis and the last signature,
other requests may have been approved against the same contract. Nothing is
recorded as approved, nothing is committed, and the request goes to legal
review. There is deliberately no override, because no internal approval lifts a
legal cap. See [decision 0004](docs/decisions/0004-ledger-lifecycle.md).

You can reproduce this state in the running product in one call:
`POST /api/demo/reset?preset=salami`.

---

## Evaluation

40 hand-built cases — **15 dev, 25 test**. Ground truth comes from
*construction*: every case was written against a known contract line with an
intended outcome, so its answer is what it was built to be, not what a model
said about it. Prompts were tuned on the dev split only; the test split was not
opened until every prompt change was final, and nothing was changed after it
ran.

**Final run: `claude-opus-5-5`, test split, commit `0f9d437`.** Scored twice
against both label sets — from the **same run**, so any difference is the
labels and not sampling noise.

| | Original labels | Audited labels |
|---|---|---|
| **Recommendation accuracy** | **92.0%** | **92.0%** |
| Scope decision | 100.0% | 100.0% |
| Change kind | 92.0% | 96.0% |
| Matched contract lines | 92.0% | 96.0% |
| Technical flag | 96.0% | 96.0% |

| | |
|---|---|
| Prompt injection turned away | **3 / 3** |
| Pipeline errors | **0** |
| Latency, median / p95 | 25.1 s / 32.0 s |
| Cost for the 25-case run | $2.10 |

The label audit moved two per-field numbers by one case each and **did not move
the headline**. It also did not correct away a failure: TEST-11 is wrong under
both label sets, and it is the case the audit examined and deliberately left
alone.

- [`docs/eval/summary.json`](docs/eval/summary.json) — the published
  measurement, traceable to the commit and the prompt versions
- [`docs/eval_comparison.md`](docs/eval_comparison.md) — the four-model
  comparison the default was chosen from, and the per-stage latency
- [`docs/eval_label_audit.md`](docs/eval_label_audit.md) — every label
  correction, argued from the glossary and the contract, never from a model's
  answer
- [`docs/eval_sample.md`](docs/eval_sample.md) — worked examples
- [decision 0002](docs/decisions/0002-default-model.md) — why `claude-opus-5-5`
  over three cheaper models that scored the same

---

## Architecture

Two processes that talk **only over HTTP JSON**.

```mermaid
flowchart TB
    subgraph browser["Browser"]
        FE["Next.js 16 · App Router<br/>Arabic-first, RTL<br/>types generated from OpenAPI"]
    end

    subgraph backend["FastAPI backend"]
        API["Routers<br/>Pydantic in, Pydantic out"]
        PIPE["11-stage pipeline<br/>stages 1·3·4·6 call a model"]
        RULES["Rules engine<br/>Article 67 · policy caps<br/>Decimal only, never a float"]
        REG[("gtpl_2026.yaml<br/>verbatim legal text<br/>every percentage")]
        REPO["Repository interface"]
    end

    PG[("PostgreSQL<br/>NUMERIC money<br/>append-only audit log")]
    CLAUDE["Claude API<br/>claude-opus-5-5"]
    REC["Recorded outputs<br/>keyed by text fingerprint"]

    FE -->|HTTP JSON| API
    API --> PIPE
    API --> REPO
    PIPE --> RULES
    RULES --> REG
    PIPE -->|"schema in, schema out<br/>no money, no state"| CLAUDE
    CLAUDE -. "unavailable, no key,<br/>or invalid response" .-> REC
    REC --> PIPE
    REPO --> PG

    classDef ai fill:#eef4ff,stroke:#5b7fc4
    classDef code fill:#eefaf2,stroke:#4c9a73
    class CLAUDE,REC ai
    class RULES,REG code
```

The **recorded fallback** is why the whole product runs with no API key: every
seeded request has recorded AI outputs keyed by a fingerprint of its text, and
the UI labels them as recorded rather than passing them off as live analysis.

---

## Engineering quality

| | |
|---|---|
| Backend tests | **633 passing**, 1 skipped (an opt-in live-API test) |
| Browser tests & screenshots | **95 passing** Playwright checks |
| Rules engine coverage | **100%**, enforced as a gate |
| CI | ruff, format, pytest on **Python 3.11 and 3.12**, eslint, typegen, tsc, next build — actions pinned to commit SHAs |
| Database | every money column `NUMERIC`; a float never touches money, a percentage or a legal limit |
| Audit log | append-only by construction: there is an `append_audit` and a `list_audit`, and **no update or delete path exists anywhere in the code** |
| Migrations | Alembic; CI asserts they apply cleanly and that seeding is idempotent |
| Sourcing | every dependency version checked against the live registry and pinned exactly; every install command and legal citation recorded in [`SOURCES.md`](SOURCES.md) with its URL |
| Decision records | [0001 pipeline](docs/decisions/0001-pipeline-design.md) · [0002 default model](docs/decisions/0002-default-model.md) · [0003 stage concurrency](docs/decisions/0003-stage-concurrency.md) · [0004 ledger lifecycle](docs/decisions/0004-ledger-lifecycle.md) |
| Spec of record | [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) — FR-01..22, NFR-01..16 |

Both repositories (in-memory and PostgreSQL) run the same test suite, because
the API must behave identically whichever is behind it.

---

## Run it locally

**Prerequisites:** Python 3.11+ and Node 20.9+. No API key, no database and no
Docker are needed for the quick start.

### Quick start: in memory, recorded AI outputs

The backend seeds the two demo contracts and their requests into memory on
start, and with no `LLM_PROVIDER` it uses recorded AI outputs (see
[No API key? It still runs.](#no-api-key-it-still-runs)). Do not create
`backend/.env` for this path.

**Terminal 1, backend.** Windows PowerShell, from the repository root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:DEMO_MODE = "true"; .\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

macOS or Linux:

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
DEMO_MODE=true .venv/bin/python -m uvicorn app.main:app --port 8000
```

**Terminal 2, frontend.** The same on every system, from the repository root:

```bash
cd frontend
npm ci
npm run dev
```

Open <http://localhost:3000>. In development the frontend calls
`http://localhost:8000` when `NEXT_PUBLIC_API_URL` is not set, so no
`.env.local` is needed. `DEMO_MODE=true` turns on the demo reset and the salami
preset on the `/demo` page, for requests from this machine only; the guided
demo is in [`docs/DEMO.md`](docs/DEMO.md).

To use other ports, start the backend with `--port 8070`, set
`ALLOWED_ORIGINS=http://localhost:3070` for the backend and
`NEXT_PUBLIC_API_URL=http://localhost:8070` in `frontend/.env.local`, then run
`npx next dev --port 3070` (Windows PowerShell 5.1 drops the `--` in
`npm run dev -- --port 3070`).

### With PostgreSQL

Uses the backend's virtual environment from the quick start, plus Docker. From
the repository root, start the database, then create the backend's settings
file:

```bash
docker compose up -d                 # PostgreSQL 18 on localhost:5433
cd backend
cp .env.example .env                 # Windows PowerShell: Copy-Item .env.example .env
```

Edit `backend/.env` before running anything else:

```ini
DATABASE_URL=postgresql://mithaq:mithaq_local_dev@localhost:5433/mithaq
DEMO_MODE=true
REMINDER_PENDING_APPROVAL_HOURS=24
REMINDER_AWAITING_DOCUMENTS_HOURS=48
```

The two `REMINDER_*` lines must be a number or be deleted: left empty, as in
the example file, every backend command stops with `Input should be a valid
integer`. 24 and 48 are the policy defaults; 0 shows reminders at once. The
database credentials are the local ones from `docker-compose.yml`.

Then, in `backend/`, on Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.seed.load
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

or on macOS or Linux:

```bash
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m app.seed.load
.venv/bin/python -m uvicorn app.main:app --port 8000
```

Start the frontend as in the quick start. To run the backend tests, also
install `requirements-dev.txt`; they use a separate `mithaq_test` database on
the same server.

### Environment variables

Names only — real values belong in `backend/.env` and `frontend/.env.local`,
both git-ignored. The example files ship with empty values.

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string. Unset or empty falls back to the in-memory store. |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins. Defaults to `http://localhost:3000`; must include the frontend's origin. |
| `DEMO_MODE` | `true` lets requests from this machine reset the demo and apply the salami preset without a token. Local only; never on a deployed instance. |
| `LLM_PROVIDER` | `anthropic` for the live provider; anything else uses recorded outputs. |
| `LLM_API_KEY` | Anthropic API key. Never logged, echoed, or included in an error. |
| `LLM_MODEL` | Overrides the default model. Leave empty to use `claude-opus-5-5`. |
| `LLM_MODEL_OVERRIDES` | Optional per-stage models, e.g. `INTAKE=claude-haiku-5-5`. |
| `DEMO_RESET_TOKEN` | Guards `POST /api/demo/reset`. Empty disables the endpoint entirely (404). |
| `REMINDER_PENDING_APPROVAL_HOURS` | Overrides the policy reminder delay. `0` for demos. A number or absent; an empty value stops the backend. |
| `REMINDER_AWAITING_DOCUMENTS_HOURS` | The same, for documents. |
| `NEXT_PUBLIC_API_URL` | The backend origin. The only source; no hardcoded fallback outside development. |

Environment variables override `backend/.env`. In PowerShell,
`$env:DATABASE_URL = ""` removes the variable instead of emptying it, so the
value in `.env` wins; to force the in-memory store over a `.env` that sets a
database, use a single space: `$env:DATABASE_URL = " "`.

### No API key? It still runs.

Leave `LLM_PROVIDER` empty and the whole product works on recorded AI outputs —
every seeded request, the full pipeline, the ledger, the approvals, the
variation orders. That is how CI runs it, how the screenshots are captured, and
how the demo preset is built. Nothing is mocked out; the recorded outputs go
through exactly the same stages.

---

## Limitations, and what comes next

Honest list. This is a hackathon build.

- **No retrieval over full contract documents.** Today the contract is a
  structured priced breakdown. Real contracts are hundreds of pages of
  specifications, and matching a request against *those* needs retrieval over
  the document set — the obvious next step, with an open-source RAG stack
  (embeddings + a vector store) so the contract text never leaves the tenant.
- **No contract upload.** Contracts are seeded. Ingesting a real one — parsing
  a bill of quantities into priced lines — is the gate to any pilot.
- **The executive regulations are not published yet** (Article 99), so no rule
  depends on them. Several Article 67 readings are flagged
  `needs_legal_review: true` in the YAML rather than guessed at.
- **Latency is not where it needs to be.** 25 s median, 32 s p95. Stages 3 and 4
  cannot be parallelised as the pipeline stands ([decision
  0003](docs/decisions/0003-stage-concurrency.md) measures the ceiling at
  15.9%); getting to a few seconds means streaming partial results to the UI and
  a smaller model on the cheaper stages.
- **The approval race is open.** The cumulative re-check reads the ledger and
  then writes, without a lock, so two final approvals racing on one contract
  could each see the other as still pending. Recorded in [decision
  0004](docs/decisions/0004-ledger-lifecycle.md) rather than hidden. A
  transaction or row lock closes it; the demo is single-user.
- **Two parties, one tenant.** There is no authentication: a persona switcher
  stands in for sign-in. Real deployment needs identity, and the role checks —
  which are enforced in the backend, not just hidden in the UI — need to hang
  off it.

---

## How it was built

**Claude Code** was the coding assistant throughout: the implementation, the
tests, the decision records and this README were written with it, one reviewed
step at a time.

That is separate from the product. **The running system calls the Claude API**
(`claude-opus-5-5` by default, configurable per stage) for the four stages where
language understanding is genuinely needed, behind a provider interface with a
recorded fallback.

---

## Legal disclaimer

Mithaq **assists with** contract administration. It does **not** give legal
advice, and nothing it produces is a legal opinion. Every recommendation is
advisory and requires a human decision by an authorised person; findings that
turn on an ambiguous provision are flagged for legal review rather than
resolved.

All contracts, parties, people and figures in this repository are **synthetic**
and were written for the demonstration. Any resemblance to a real contract,
entity or person is coincidental.

The legal text in
[`gtpl_2026.yaml`](backend/app/regulations/gtpl_2026.yaml) is reproduced from
the official Umm Al-Qura publication for reference. It is not a certified
translation, and the Arabic original governs.
