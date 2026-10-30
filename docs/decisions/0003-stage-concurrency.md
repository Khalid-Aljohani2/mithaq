# 0003 — Stages 3 and 4 stay sequential

Status: accepted
Date: 2026-10-30
Requirements: FR-05, FR-06, FR-15, NFR-05

## Context

Stages 3 (contract and scope analysis) and 4 (technical assessment) are the two
slowest AI calls in the pipeline and run one after the other. The question put
was: do they depend only on stage 1? If so, run them concurrently and measure
the saving; if not, say so and change nothing.

## Finding

**They are not siblings. Stage 4 consumes stage 3's output, so it cannot start
until stage 3 has finished.**

From `backend/app/pipeline/runner.py`:

```python
# ---- Stage 3: Contract and scope analysis (AI) ---------------------
scope: ScopeOutput = provider.scope_analysis(
    ScopeInput(cr_id=request.id, body_ar=request.body_ar,
               breakdown=_breakdown_views(contract))
)

# ---- Stage 4: Technical assessment (AI) ----------------------------
affected = tuple(
    view for view in _breakdown_views(contract) if view.id in scope.matched_line_ids
)
technical: TechnicalOutput = provider.technical_assessment(
    TechnicalInput(cr_id=request.id, body_ar=request.body_ar, affected_lines=affected)
)
```

`TechnicalInput.affected_lines` is derived from `scope.matched_line_ids` —
stage 3's answer. The dependency is in the input schema, not merely in the
order of two statements.

A second observation, incidental to the question but worth recording: **neither
stage depends on stage 1 either.** Both read `request.body_ar` and the contract
directly. Stage 1's output feeds stage 2 (the document checklist is keyed on
the impact type it extracts) and the stored request, not stages 3 or 4. So the
premise is off in both directions — the pair are not peers hanging off stage 1,
they are a chain.

## Decision

**No change.** Stages 3 and 4 run sequentially, as they did.

## Why not restructure them so they could run concurrently

It is possible: hand stage 4 the *whole* breakdown instead of the lines stage 3
matched, and the dependency disappears. That was rejected, for three reasons.

1. **It changes what the model is asked.** Stage 4's question today is "does
   this request change the approved product or specification *on these lines*".
   Given all eight lines it becomes "find the lines and then judge them" —
   stage 3's job, asked a second way. Two stages answering overlapping
   questions is how they start disagreeing, and `detect_conflicts` exists
   because disagreements between stages are already a thing that happens.

2. **It would invalidate the comparison this step rests on.** Every number in
   `docs/eval_comparison.md` and `docs/decisions/0002-default-model.md` was
   produced with stage 4 scoped to the matched lines. Changing the prompt input
   and re-running would mean the model choice was made on one pipeline and the
   published accuracy measured on another.

3. **The saving is bounded and the cost is not the latency.** Stages 3 and 4
   are two of the four AI calls in a run. Even a perfect overlap removes one of
   them from the critical path — roughly a quarter of AI wall time, and less of
   the total. The per-stage medians the harness now records
   (`summary.stage_ms`) make the real ceiling checkable rather than assumed.

## What was done instead

The evaluation report now records per-stage wall time —
`summary.stage_ms[stage].median` and `.p95`, over the cases that actually
reached each stage. That is measurement, not a pipeline change: the runner
already timed every stage for the trace, and this only carries the numbers into
the report. It means the next person to ask this question can answer it from
data rather than from a reading of the control flow.

### The measured ceiling

From the final TEST-split run (25 cases, `claude-opus-5-5`, commit `0f9d437`):

| stage | median ms |
|---|---|
| 1 Intake | 3,705.0 |
| 3 Scope analysis | 4,411.0 |
| 4 Technical assessment | 3,980.0 |
| 6 Risk & compliance | 6,212.0 |
| 7 Orchestrator | 5,027.0 |
| whole run (median) | 25,054.5 |

If stages 3 and 4 ran perfectly in parallel, the pair would cost
`max(4411, 3980) = 4,411 ms` instead of `8,391 ms`. The saving is **3,980 ms,
about 15.9% of the median run** — and that is a ceiling, assuming zero
scheduling overhead and no retry.

That is not nothing. It is also not enough to buy with two stages answering
overlapping questions and a re-run of every published number, which is what
reason 1 and reason 2 above would cost. The ratio is now on the record, so the
trade is a judgement about a measured 16% rather than about a guess.

## Revisit if

- Stage 4 is ever given the full breakdown for an unrelated reason, at which
  point the dependency is already gone and concurrency is free.
- The measured stage medians show stages 3 and 4 dominating total latency by
  enough that the ceiling above is worth the coupling.
