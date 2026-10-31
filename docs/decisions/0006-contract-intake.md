# 0006 - Contract intake and the AI draft boundary

Status: accepted
Date: 2026-10-31
Requirements: FR-01, FR-13, NFR-01, NFR-03, NFR-04, NFR-08, NFR-15

## Context

Contracts existed only as seed data. A real user needs to enter one, and most
contracts arrive as a PDF. Reading a PDF is a job for the model; deciding what
the contract says, in money, is not (NFR-03, NFR-15).

## Decision

Two routes, two trust levels.

- `POST /api/contracts` (person). Body `ContractCreateInput`. Only the
  government entity's `PROJECT_MANAGER` or `CEO` may call it (403 `WRONG_ROLE`
  otherwise; constant `CONTRACT_CREATOR_ROLES` in `app/services/contracts.py`,
  because it is a permission and `policy.yaml` holds thresholds). The server
  assigns line ids (`ITM-01`...), computes each total as `quantity * unit_rate`
  in `Decimal`, refuses a product needing more than 2 decimal places rather than
  rounding it, and refuses unless the lines sum exactly to `original_value`.
  Every problem is returned at once as 422 `CONTRACT_INVALID` with
  `problems[{field, code, message_ar, message_en}]`; Pydantic type errors on the
  two intake routes use the same shape, other routes keep FastAPI's default.
  Ids are `CT-<start year>-NNNN`, unique among stored contracts. Writes go
  through `ContractRepository.add_contract`, and one `CONTRACT_CREATED` audit
  row (entity_type `CONTRACT`) records the person, role and party. No schema
  migration was needed: `audit_log.action` is a string column and
  `contract_id` is the new contract's own id.
- `POST /api/contracts/draft` (AI). Same role check. Exactly one of `text`
  (<= 200,000 chars) or `pdf_base64` (<= 10 MB decoded, must start `%PDF`). The
  document goes to the model as its own content block under prompt
  `contract_draft.v1`, which states the document is data and forbids inventing
  numbers. The model returns numbers as strings, converted to `Decimal` in
  code; anything unparseable becomes null plus a note. The route takes no
  repository: it stores nothing and audits nothing. Without the live provider
  it answers 409 `DRAFT_NEEDS_LIVE_PROVIDER`; a failed model call is 502
  `DRAFT_FAILED`. It is rate limited with the other model routes.

## Consequences

The AI can save a person typing, never commit a contract: a draft only
becomes a contract when a person submits it to the first route, where every
total is recomputed. The demo reset restores the seed and so deletes
contracts created here; their audit rows remain.
