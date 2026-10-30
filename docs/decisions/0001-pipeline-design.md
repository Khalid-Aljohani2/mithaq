# 0001 — Pipeline design: 11 named stages, AI only where language is

Status: accepted
Date: 2026-10-30
Requirements: FR-03..FR-15, FR-18, NFR-03, NFR-06, NFR-15, NFR-16

## Context

Requirements v2 describes an 11-step change-order workflow. We have to decide
how much of it an LLM runs, and where the boundary sits between a model's
opinion and the system's decisions.

## Decision

**An 11-stage pipeline. Each stage appears in the trace as a named agent** with
its own inputs, outputs, decision, actor type and duration (FR-15, FR-18), so a
reviewer can see which component said what rather than one opaque answer.

**AI is used only where language understanding is actually needed:**

| # | Stage | Actor | Why |
|---|---|---|---|
| 1 | Intake | **AI** | free Arabic prose → structured fields |
| 2 | Document validation | code | a checklist is a set comparison |
| 3 | Contract & scope analysis | **AI** | matching prose to breakdown lines is semantic |
| 4 | Technical assessment | **AI** | comparing a request to a spec is semantic |
| 5 | Cost & schedule impact | code | arithmetic over contract unit rates |
| 6 | Risk & compliance | **AI** narrative over code findings | the legal/policy results are computed; the prose summarising them is not |
| 7 | Orchestrator | code decides, **AI** narrates | the recommendation and approval chain are rules; the explanation is prose |
| 8 | Human approval gate | code | role and order checks; only humans decide |
| 9 | Issue VO | code assembles, **AI** drafts prose | values and citations are computed; the Arabic wording is drafted |
| 10 | Update project records | code | ledger and baseline arithmetic |
| 11 | Execution & follow-up | code | recording actuals and deviations |

**Money, thresholds, routing and state changes are deterministic code.** No
model output is ever summed, compared against a cap, or used to move a state.

## Reasons

**NFR-06 — latency.** Agent analysis must stay under 15s at p95. Four AI stages
with bounded prompts fit; eleven do not, and the seven code stages return in
microseconds. Stage 5 in particular would be the slowest possible way to
multiply two numbers.

**FR-17 — measurable accuracy.** The evaluation set reports accuracy *per step*
against ≥80% on the recommendation. That is only meaningful if each stage has a
separately checkable output, which the named-stage structure gives us. It also
localises a regression: if scope classification degrades, stage 3's number moves
and the others do not.

**NFR-15 — decision boundary.** The requirement is that no code path lets an AI
stage change approval status, issue a VO, or alter contract values. The cheapest
way to guarantee that is for the AI stages to be *incapable* of it: they are
pure functions returning Pydantic models, they receive no repository and no
session, and the orchestrator reads their output as evidence rather than
instruction. A test asserts the AI stage signatures take no writable dependency.

**NFR-16 — configurability.** Thresholds live in configuration tagged with their
source — `law` (Article 67, in `gtpl_2026.yaml`), `organization_policy` (the 20%
cost and time rules, the unit-rate deviation), or `default` (reminder delays).
Code reads them; code never spells a number.

## Consequences

- Swapping the model changes four stages, not eleven.
- A model outage degrades narrative quality; it cannot corrupt a figure or a
  state. The `ScriptedProvider` fallback (FR-19) serves recorded outputs
  labelled `recorded: true` and the deterministic stages are unaffected.
- The two hybrid stages (7 and 9) need care: their code path must produce a
  complete result on its own, with AI prose as an addition that can be absent.
  Both are written so a missing narrative degrades the wording, never the
  decision or the numbers.
- Article 67 keeps its own engine, untouched, at 100% branch coverage. The
  pipeline maps a CR onto it rather than reimplementing it.

## Alternatives rejected

**One large agent with tools.** Fewer moving parts, but per-step accuracy
becomes unmeasurable, latency is unbounded, and the decision boundary turns into
a prompt instruction rather than a property of the code. Rejected on FR-17 and
NFR-15.

**All eleven stages in code.** Deterministic and fast, but stages 1, 3 and 4 are
genuinely language problems — deciding whether Arabic prose describes work
already covered by a breakdown line is not a string match. Rejected as unable to
meet FR-05.
