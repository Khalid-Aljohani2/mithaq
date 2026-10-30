# Model comparison and final run - TEST split

## Final run (Step 4D)

One run of the held-out TEST split with the configuration that ships: default
model `claude-opus-5-5`, prompts unchanged since Step 4C, `minimum_confidence`
0.70. Run at **commit `0f9d437`**, `2026-10-30T21:00Z`, 25 cases, prompt
versions `{INTAKE: v3, SCOPE_ANALYSIS: v2, TECHNICAL_ASSESSMENT: v2,
RISK_COMPLIANCE: v2, ORCHESTRATOR: v1, ISSUE_VO: v1}`. Published as
`docs/eval/summary.json` and served at `/api/eval/summary`.

**Scored twice, from the same run** — once against the original labels and once
with the corrections in [`eval_label_audit.md`](eval_label_audit.md) applied.
One run, two label sets: any difference between the columns is the labels, not
sampling noise.

| field | original labels | audited labels |
|---|---|---|
| recommendation | **92.0%** | **92.0%** |
| scope decision (`in_scope`) | 100.0% | 100.0% |
| kind | 92.0% | 96.0% |
| matched lines | 92.0% | 96.0% |
| technical flag | 96.0% | 96.0% |

| | |
|---|---|
| prompt injection turned away | 3 / 3 |
| pipeline errors | **0** |
| latency median / p95 | 25,054.5 ms / 31,950.9 ms |
| tokens in / out | 291,919 / 46,746 |
| cost | $2.1026 |

### What the audit did and did not do

**It did not move the headline.** Recommendation accuracy is 92.0% under both
label sets. The audit changed `kind` and `matched lines` by 4.0 points each —
one case apiece, exactly the two cases it corrected — and nothing else.

**It did not correct away a failure.** TEST-11 is wrong under both label sets.
That is the case the audit examined and deliberately left alone, and it is
still counted as a miss. An audit that existed to flatter the model would have
changed that one too.

### Change against the Step 4C run of the same model and split

| field | 4C (`48646d8`) | 4D (`0f9d437`) | delta |
|---|---|---|---|
| recommendation | 88.0% | 92.0% | +4.0 |
| scope decision | 96.0% | 100.0% | +4.0 |
| kind | 88.0% | 92.0% | +4.0 |
| matched lines | 88.0% | 92.0% | +4.0 |
| technical flag | 92.0% | 96.0% | +4.0 |
| errors | 1 | 0 | -1 |
| median latency | 24,915.4 ms | 25,054.5 ms | +0.6% |
| cost | $2.0842 | $2.1026 | +0.9% |

Every field moved by exactly 4.0 points, which is exactly one case in 25, and
that is the whole story: **TEST-17 no longer crashes.** In 4C it raised
`CostingError: a decrease must name the breakdown line it reduces` and an
errored case scores zero on all five fields. The Step 4D fix prices a
whole-line removal from the line's contract total, so the case now completes
and is scored normally.

Nothing else changed. No prompt was edited, no threshold was tuned, and the
model is the same. Attributing the improvement to anything but that one bug fix
would be reading more into these numbers than they contain.

### Remaining failures

| id | category | field | expected | got |
|---|---|---|---|---|
| `TEST-10` | code_switching | recommendation | `APPROVE` | `REQUEST_REVISION` |
| `TEST-11` | ambiguous | kind | `UNCLEAR` | `PCR` |
| `TEST-11` | ambiguous | matched_line_ids | `[]` | `['ITM-08']` |
| `TEST-11` | ambiguous | changes_approved_product | `False` | `True` |
| `TEST-18` | spec_change | recommendation | `APPROVE` | `REQUEST_REVISION` |

Two of the three failures are conservative: the pipeline asked a human where
the label said approve. The third, TEST-11, is the opposite and is the one
worth attention — the model resolved an ambiguous request into a confident
`PCR` where the correct answer is to admit it cannot tell.

### Per-stage latency

Recorded for the first time in this run, over the 25 cases that reached each
stage.

| stage | actor | median ms | p95 ms |
|---|---|---|---|
| 1 Intake | AI | 3,705.0 | 7,233.9 |
| 2 Document validation | code | 0.0 | 0.0 |
| 3 Scope analysis | AI | 4,411.0 | 7,322.5 |
| 4 Technical assessment | AI | 3,980.0 | 10,296.3 |
| 5 Cost & schedule | code | 0.0 | 0.7 |
| 6 Risk & compliance | AI | 6,212.0 | 11,103.5 |
| 7 Orchestrator | code + AI narrative | 5,027.0 | 10,302.7 |

The five AI stages account for 23,335 ms of the 25,054 ms median — 93% of wall
time. The deterministic stages are free: stage 2 and stage 5 together are under
a millisecond, which is what computing a cap in code rather than asking a model
buys.

---

# Four-model comparison (Step 4C)

The run the default model was chosen from. Kept for the record; see
[`decisions/0002-default-model.md`](decisions/0002-default-model.md) for the
argument.

Generated 2026-10-30T19:26:44.431511+00:00 from `48646d8`, prompts {'INTAKE': 'v3', 'SCOPE_ANALYSIS': 'v2', 'TECHNICAL_ASSESSMENT': 'v2', 'RISK_COMPLIANCE': 'v2', 'ORCHESTRATOR': 'v1', 'ISSUE_VO': 'v1'}.

25 test cases. Prompts were tuned on the dev split only; this split was not opened until every prompt change was final, and nothing was changed after it ran.

Cost is computed from the token counts below at the per-model rates verified on 2026-10-30 and recorded in SOURCES.md (Haiku 5.5 is listed as *from* $0.10/$0.50, so its figure is a floor).

| model | recommendation | scope | kind | matched lines | technical | injection | median ms | p95 ms | in tok | out tok | cost USD |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `claude-haiku-5-5` | 88.0% | 96.0% | 88.0% | 84.0% | 88.0% | 3/3 | 19318.7 | 30062.9 | 292086 | 53128 | $0.0558 |
| `claude-sonnet-5-5` | 88.0% | 88.0% | 80.0% | 84.0% | 88.0% | 3/3 | 24210.9 | 137250.6 | 283331 | 44386 | $1.0105 |
| `claude-opus-5-5` | 88.0% | 96.0% | 88.0% | 88.0% | 92.0% | 3/3 | 24915.4 | 31644.2 | 288663 | 46478 | $2.0842 |
| `claude-fable-5-1` | 88.0% | 96.0% | 84.0% | 88.0% | 92.0% | 3/3 | 36923.3 | 47658.6 | 288763 | 56093 | $5.6923 |

## Failures, with the model's answer beside the expected one

A failure here is not automatically a model error - check the label too. Three cases below are flagged as suspected label errors in the step report.

### claude-haiku-5-5 - failures

| id | category | field | expected | got |
|---|---|---|---|---|
| `TEST-01` | in_scope_reworded | in_scope | `True` | `False` |
| `TEST-01` | in_scope_reworded | kind | `IN_SCOPE` | `PCR` |
| `TEST-01` | in_scope_reworded | matched_line_ids | `['ITM-07']` | `['ITM-03', 'ITM-07']` |
| `TEST-01` | in_scope_reworded | recommendation | `CLOSE_IN_SCOPE` | `APPROVE` |
| `TEST-10` | code_switching | matched_line_ids | `['ITM-05']` | `[]` |
| `TEST-10` | code_switching | recommendation | `APPROVE` | `REQUEST_REVISION` |
| `TEST-11` | ambiguous | kind | `UNCLEAR` | `PCR` |
| `TEST-11` | ambiguous | matched_line_ids | `[]` | `['ITM-08']` |
| `TEST-11` | ambiguous | changes_approved_product | `False` | `True` |
| `TEST-11` | ambiguous | recommendation | `REQUEST_REVISION` | `APPROVE` |

### claude-sonnet-5-5 - failures

| id | category | field | expected | got |
|---|---|---|---|---|
| `TEST-10` | code_switching | - | - | ERROR: NoProviderAvailableError: stage TECHNICAL_ASSESSMENT could not be analysed: AI_STAGE_FAILED. The live provider is unavailable and there is no recorded answer for this request text. |
| `TEST-17` | ncr_reduction | - | - | ERROR: CostingError: a decrease must name the breakdown line it reduces |
| `TEST-19` | in_scope_reworded | in_scope | `True` | `False` |
| `TEST-19` | in_scope_reworded | kind | `IN_SCOPE` | `UNCLEAR` |
| `TEST-19` | in_scope_reworded | recommendation | `CLOSE_IN_SCOPE` | `REQUEST_REVISION` |

### claude-opus-5-5 - failures

| id | category | field | expected | got |
|---|---|---|---|---|
| `TEST-10` | code_switching | recommendation | `APPROVE` | `REQUEST_REVISION` |
| `TEST-17` | ncr_reduction | - | - | ERROR: CostingError: a decrease must name the breakdown line it reduces |
| `TEST-18` | spec_change | kind | `PCR` | `SUBSTITUTION` |
| `TEST-18` | spec_change | recommendation | `APPROVE` | `REQUEST_REVISION` |

### claude-fable-5-1 - failures

| id | category | field | expected | got |
|---|---|---|---|---|
| `TEST-10` | code_switching | recommendation | `APPROVE` | `REQUEST_REVISION` |
| `TEST-11` | ambiguous | kind | `UNCLEAR` | `PCR` |
| `TEST-11` | ambiguous | matched_line_ids | `[]` | `['ITM-08']` |
| `TEST-11` | ambiguous | changes_approved_product | `False` | `True` |
| `TEST-11` | ambiguous | recommendation | `REQUEST_REVISION` | `APPROVE` |
| `TEST-17` | ncr_reduction | - | - | ERROR: CostingError: a decrease must name the breakdown line it reduces |
