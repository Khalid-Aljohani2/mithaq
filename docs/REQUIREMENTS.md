# Mithaq: Requirements

Deadline: deployed and publicly reachable within 20 hours. Code on GitHub. Hosting on Vercel (frontend and FastAPI backend).
Priority: MUST is required for submission. SHOULD only if time remains. WON'T is explicitly out of scope.

## Functional requirements

### MUST
FR-01 Contract workspace: show the seeded contract (parties, value, dates, items with Arabic descriptions) in an RTL Arabic layout.
FR-02 Two roles: switch between Government Entity and Contractor views. Both read the same ledger; each sees only the actions its role may take. Acceptance: an action from the wrong role is rejected by the backend, not only hidden in the UI.
FR-03 Request intake: an inbox where a user pastes an Arabic request (sender, date, body). Stored with timestamp.
FR-04 AI analysis: the agent maps the request to contract items and classifies it as IN_SCOPE, NEW_ITEM, INCREASE_EXISTING, DECREASE_EXISTING, NON_FINANCIAL, or UNCLEAR. Output is schema-validated JSON with confidence, matched item ids, extracted quantities, and the exact phrase from the request that supports the decision.
FR-05 Clarification: when confidence is below a configurable threshold or the class is UNCLEAR, the agent drafts a clarification question to the requester instead of guessing.
FR-06 Pricing: increases and decreases of existing items are priced by code from contract unit prices. New items are priced by a human on the contractor side; any AI price is labeled "suggestion" and must be confirmed by a human.
FR-07 Rules evaluation: the deterministic engine (Step 2) checks every proposed order against Article 67 using the cumulative ledger and shows before and after percentages, warnings, blocking violations, consent requirements, and article references.
FR-08 Change order draft: a formal Arabic change order document with affected items, values, cited articles, and required signatures. Printable to PDF from the browser.
FR-09 Approval workflow: contractor consent step and authority approval step, approve or reject with a reason. Nothing is ever auto-approved.
FR-10 Ledger dashboard: cumulative usage per category against each cap, list of orders with status, and the remaining headroom in SAR.
FR-11 Time extension flag: approved orders that add work show eligibility for a proportional extension (Article 72 paragraph 1).
FR-12 Agent trace: for every analyzed request, show the steps the agent took, the tools it called, and a summary of each result.
FR-13 Audit log: every state change records actor role, timestamp, previous state, and new state. Append only.
FR-14 Evaluation: a labeled set of 30 to 50 synthetic Arabic requests with expected class and items. A command and a page that run it and report accuracy and a confusion matrix.
FR-15 Demo reset: one action restores the seed state.
FR-16 Fallback mode: if the AI provider is unreachable, the app serves recorded agent responses for the demo requests and labels them clearly as recorded.

### SHOULD
FR-17 Contract upload: upload a PDF or DOCX contract and extract items with AI, followed by mandatory human review before use.
FR-18 English toggle for UI labels. Contract content stays Arabic.
FR-19 Notification feed per role (pending consents, pending approvals, approaching caps).

### WON'T (out of scope for the MVP)
Real authentication or national identity login, integration with the government procurement portal, real email ingestion, legal advice, multi-contract portfolio analytics, rules from the executive regulations of the new law until they are published.

## Non-functional requirements

NFR-01 Correctness: all money uses Decimal. The rules module has boundary tests at, below, and above every cap, and full branch coverage of the rules module.
NFR-02 Traceability: every legal rule references its article and the verbatim source file with the official URL. Ambiguous rules carry needs_legal_review.
NFR-03 AI boundaries: the model never computes money, percentages, or legal limits. Model output is validated against Pydantic schemas, retried once on failure, then marked failed. Prompts are versioned files in the repo.
NFR-04 Prompt injection: request text is treated as data inside clear delimiters. Nothing in a request can change state; state changes only happen through role-checked endpoints and human approval.
NFR-05 Measured quality: report the measured classification accuracy from FR-14. The first run sets the baseline; improvements are reported against it.
NFR-06 Performance targets: rules evaluation under 200 ms. Agent analysis under 15 s at p95, with visible progress in the UI while it runs.
NFR-07 Persistence: a managed Postgres database. No state depends on server memory, because Vercel Functions do not keep memory between requests.
NFR-08 Security: secrets live only in Vercel and local env files, never in git. CORS allows only the production frontend domain and localhost. Request body size limits. Simple rate limit on AI endpoints to protect API credits. Synthetic data only, no real people or real entities.
NFR-09 Deployment: frontend and backend deployed on Vercel from GitHub. Every push to main deploys automatically. A health endpoint for the backend. A warm-up call before the demo.
NFR-10 CI: GitHub Actions on every push and pull request runs ruff, pytest, eslint, tsc, and next build. Main must stay green.
NFR-11 Maintainability: TypeScript strict, Pydantic everywhere on the backend, layered backend (routers, services, repositories, domain). Short decision records in docs/decisions/ for each significant choice.
NFR-12 Observability: structured logs with a request id. For each AI call, log model, latency, token usage, and validation result.
NFR-13 Accessibility and language: correct RTL layout, an Arabic web font with a real fallback stack, WCAG AA contrast, keyboard navigable main flows.
NFR-14 Documentation: README with architecture overview, local setup, environment variables, deployment steps, a demo script, and a legal disclaimer that Mithaq assists and does not give legal advice.
