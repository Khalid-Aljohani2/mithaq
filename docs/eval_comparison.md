# Model comparison - TEST split

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
