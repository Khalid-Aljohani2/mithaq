# Mithaq: Requirements v2

Process source: an 11-step change order workflow reviewed with a senior project manager from a large company.
Control principle: AI agents analyze, validate, recommend and prepare documents. Authorized people approve every contractual or financial commitment. The agent never decides; it recommends, explains why, and states the next actions.

## Glossary
CR (Change Request): any request to change the contract work.
PCR (Positive Change Request): adds work, quantity, cost or time.
NCR (Negative Change Request): removes work or reduces quantity or cost.
Substitution: replaces an approved product, specification or method. Counted as an NCR for what is removed plus a PCR for what is added.
VO (Variation Order): the formal instruction issued only after the full approval chain approves a CR.
In-scope request: covered by an existing line in the contract breakdown. It is not a change and counts toward no limit.
The UI shows each abbreviation with its full name on first appearance on every screen, because NCR commonly means Non-Conformance Report in construction quality.

## Functional requirements (MUST)
FR-01 Contract baseline: a breakdown (BOQ/WBS) of line items, each with deliverable description, unit, quantity, contract unit rate, approved product or specification, and restrictions. Plus contract value, start date, end date, and contract type (government or private).
FR-02 Organization setup: each party (government entity, contractor) defines its roles and approval matrix: which role approves which kind of change, in what order, and the thresholds that escalate approval. Default approver: Project Manager. Defaults are seeded and editable.
FR-03 Step 1 Intake: receive a CR (pasted Arabic text plus a list of attachments), create a unique CR ID, identify the requester, extract the requested change and its impact type (cost, time, or both).
FR-04 Step 2 Document validation: check the CR against a required-documents checklist for its type. If incomplete, the agent sends the requester a structured gap list and the CR waits for resubmission. This is a non-commitment action the agent may take on its own.
FR-05 Step 3 Contract and scope analysis: compare the CR with the contract breakdown and deliverables. Explicit yes or no: already in scope? If yes, recommend closing it as in scope, citing the matching breakdown lines. If no, classify it as PCR, NCR or substitution and continue.
FR-06 Step 4 Technical assessment: does the CR change an approved product or specification? Check it against the initial requirements and restrictions. A change to an approved product adds a technical approval step to the chain. A conflict with a restriction is flagged.
FR-07 Step 5 Cost and schedule impact: every CR states its impact on cost, time, or both. Cost is computed by code from quantities and contract unit rates. A proposed unit rate deviating from the contract rate by more than 20% (configurable) is flagged. Time impact is recorded in days.
Company policy: a cumulative cost increase above 20% of the original contract value, or a cumulative time extension above 20% of the original duration, is not allowed by default. It can pass only as an exception with CEO approval added to the chain. Exactly 20% is allowed without the exception.
Law: for government contracts, the existing Article 67 rules engine applies on top and its caps stay blocking. CEO approval cannot lift a legal cap. The recommendation states this and flags the CR for legal review.
FR-08 Step 6 Risk and compliance: delivery, operational, commercial and compliance risks, including the legal and policy check results.
FR-09 Step 7 Orchestrator: consolidate all step results, flag conflicts between them, apply decision rules, and produce a recommendation (approve, reject, or request revision) with reasons, confidence and next actions. Build this CR's approval chain from the approval matrix.
FR-10 Step 8 Human approval gate: approvers act in chain order. Each can approve, reject, or request revision with a reason. Only humans move a CR through this gate. Rejection or revision notifies the requester.
FR-11 Notifications and reminders: every role affected by a CR is notified according to the approval matrix. Pending approvals generate reminders after a configurable delay. In-app only.
FR-12 Step 9 Issue VO: after the final approval, generate the VO in Arabic with scope, value, duration, cited breakdown lines and articles, and approval signatures. Printable to PDF.
FR-13 Step 10 Update project records: contract value, budget, schedule baseline and the cumulative ledger.
FR-14 Step 11 Execution and follow-up: actual completion, actual cost, dates and deviations per VO. Close-out records verification against acceptance criteria.
FR-15 Agent trace: every step's inputs, outputs, decision, actor type (code or AI) and duration, per CR.
FR-16 Audit log: append only, every state change (existing).
FR-17 Evaluation: a labeled set of 30 to 50 synthetic Arabic CRs with expected scope decision, change type and recommendation. Report accuracy per step and a confusion matrix. Target: at least 80% recommendation accuracy, measured, not assumed.
FR-18 Cycle time metrics: record the time each CR spends in every step.
FR-19 Demo reset and fallback mode (existing).

## SHOULD
FR-20 Lessons learned note at close-out.
FR-21 Contract upload with AI extraction of the breakdown, followed by mandatory human review.
FR-22 English toggle for UI labels.

## WON'T
Real authentication or national identity login, procurement portal integration, real email, legal advice, executive-regulation rules until published.

## Non-functional requirements
NFR-01 to NFR-14 from v1 stay unchanged. Additions:
NFR-15 Decision boundary: no code path lets an AI step change a CR's approval status, issue a VO, or change contract values. Enforced in the backend and covered by tests.
NFR-16 Configurability: every threshold (unit rate deviation, policy escalation, reminder delays, legal limits) lives in configuration, each tagged with its source: law, organization policy, or default.

## Open question
Q1 Base of the unit rate comparison when a PCR adds a new item with no matching contract line: compare with the closest similar line, or require a human-entered market rate? Default until answered: human-entered rate, flagged.
