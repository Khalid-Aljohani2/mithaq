# 0002 — Default model: `claude-opus-5-5` for every stage

Status: accepted
Date: 2026-10-30
Requirements: FR-17, FR-19, NFR-03, NFR-05, NFR-11

## Context

Step 4B built the evaluation set — 40 hand-constructed cases, 15 dev and 25
test, ground truth derived from the contract rather than from a model's
judgement. Step 4C tuned the prompts on the dev split only and then ran all
four models once against the held-out test split, with the default model
deliberately left unchanged so the choice could be made from the data rather
than from a preference formed while tuning.

`DEFAULT_MODEL` had been `claude-sonnet-5-5` since the provider was written.
That was a placeholder, not a finding.

## The measurement

25 test cases, generated `2026-10-30T19:26` from commit `48646d8`, prompt
versions `{INTAKE: v3, SCOPE_ANALYSIS: v2, TECHNICAL_ASSESSMENT: v2,
RISK_COMPLIANCE: v2, ORCHESTRATOR: v1, ISSUE_VO: v1}`. Cost is computed from
the recorded token counts at the per-model rates verified the same day and
recorded in `SOURCES.md`; Haiku 5.5 is published as *from* $0.10/$0.50, so its
figure is a floor.

| model | recommendation | scope | kind | matched lines | technical | injection | median ms | p95 ms | in tok | out tok | cost USD |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `claude-haiku-5-5` | 88.0% | 96.0% | 88.0% | 84.0% | 88.0% | 3/3 | 19318.7 | 30062.9 | 292086 | 53128 | $0.0558 |
| `claude-sonnet-5-5` | 88.0% | 88.0% | 80.0% | 84.0% | 88.0% | 3/3 | 24210.9 | 137250.6 | 283331 | 44386 | $1.0105 |
| **`claude-opus-5-5`** | **88.0%** | **96.0%** | **88.0%** | **88.0%** | **92.0%** | **3/3** | **24915.4** | **31644.2** | 288663 | 46478 | $2.0842 |
| `claude-fable-5-1` | 88.0% | 96.0% | 84.0% | 88.0% | 92.0% | 3/3 | 36923.3 | 47658.6 | 288763 | 56093 | $5.6923 |

## Decision

**`DEFAULT_MODEL = "claude-opus-5-5"`, for every stage.** No per-stage
overrides are configured; `LLM_MODEL_OVERRIDES` remains available and empty.

## Why

**The headline number does not separate them.** All four reach 88.0%
recommendation accuracy and all four turn away 3/3 prompt-injection attempts.
Choosing on the headline alone would be choosing on noise, so the decision
rests on the three things that do differ.

**1. Opus is best or joint-best on every per-stage field.** It is joint-best on
scope (96.0%) and kind (88.0%), and sole best on matched lines (88.0%) and the
technical flag (92.0%). Nothing beats it on any field. Sonnet — the incumbent —
is the *worst* of the four on kind (80.0%) and joint-worst on scope and matched
lines, which is the clearest argument that the existing default was never
chosen on evidence.

**2. Its tail latency is stable.** Sonnet's p95 of 137.3 s against a 24.2 s
median is a 5.7× spread: one case in twenty took over two minutes. Opus runs
31.6 s at p95 against a 24.9 s median, a 1.3× spread. For an interactive review
screen the tail is what a user actually experiences, and an occasional
two-minute wait reads as a hang, not as a slow answer.

**3. Its misses are conservative rather than wrong.** This is the one that
decided it. On a governance tool the cost of a mistake is not symmetrical:
sending a correct request to a human wastes a few minutes, while approving an
out-of-scope one puts a signature on something nobody checked.

- Opus's two genuine misses (`TEST-10`, `TEST-18`) both go the safe way: it
  returned `REQUEST_REVISION` where the label said `APPROVE`. It declined to
  act, and a person looks.
- Haiku's `TEST-01` fails in the opposite direction. The request is an in-scope
  one reworded; Haiku read it as a `PCR`, matched a line that is not involved,
  and recommended `APPROVE`. That is a change order recommended for approval on
  work the contract already covers — the exact failure this product exists to
  prevent. Fable fails the same way on `TEST-11`, recommending `APPROVE` on a
  request a careful reader cannot resolve.

A 15× cost multiple over Haiku on a 25-case run is $2.03. That is not a
material number here, and it does not outweigh a model that recommends
approving work the contract already paid for.

## What this is not

**Not a claim that Opus is more accurate.** On the headline it is not: 88.0%
across the board. The claim is narrower — equal accuracy, better per-stage
behaviour, a stable tail, and failures that fall on the safe side.

**Not tuned on this data.** No prompt, threshold or label was changed because
of the test split. `minimum_confidence` stays at 0.70. The prompts were frozen
before the split was opened.

**Not free of the label audit's influence, and this must be said plainly.**
One of Opus's four recorded failures above, `TEST-18`, is a case the subsequent
label audit corrected: Opus answered `SUBSTITUTION`, and `SUBSTITUTION` is now
the label. The audit therefore flatters Opus. Two things keep that honest:
the audit (`docs/eval_label_audit.md`) argues from the project's own glossary
and the contract rather than from Opus's answer, and every run is scored
against both label sets side by side, so the size of the effect is visible
rather than asserted. The decision above is made on the **original** labels —
the table in this record — and does not need the audit to hold.

## Consequences

- Every AI stage runs on Opus 5.5 unless `LLM_MODEL` or a per-stage override
  says otherwise. Both remain configuration; neither is hardcoded at a call
  site (NFR-11).
- A demo or a CI run with no key still uses the recorded outputs, so the model
  choice changes nothing about whether the system runs (FR-19).
- Running the whole 40-case set costs roughly $3.30 at these rates. Worth
  stating before anyone re-runs it casually.
- Revisit when the prompts change materially, or when a model in this lineup is
  replaced. The comparison script (`scripts/compare_models.py`) reproduces the
  table.
