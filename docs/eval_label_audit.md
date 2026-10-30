# Evaluation label audit

**Date:** 2026-10-30
**Split audited:** both (1 dev case, 3 test cases)
**Status:** applied — this document and the label change are one commit, made
**before** any re-run, so no number in `docs/eval_comparison.md` was produced
under the new labels by a run that had already been scored under the old ones.

## Why this exists

During Step 4C several cases were marked wrong by the harness where the model's
answer looked better than the label. The rule at the time was explicit: *do not
change a label silently; list it with the reasoning and wait.* This is that
list, resolved.

Changing a label after seeing a model's output is how an evaluation set gets
quietly tuned into agreeing with the model. Three things guard against it here:

1. **The original labels are not deleted.** Each corrected case keeps its
   `expected_*` fields exactly as they were and gains an `audit` object holding
   the correction. Both label sets live in `eval/cases.jsonl`.
2. **Every run is scored twice**, against the original labels and the audited
   ones, side by side. If the audit flattered the model, the gap says so.
3. **Each correction cites the project's own definitions**, not the model's
   answer. A label is wrong when it contradicts the glossary or the contract,
   not when a model disagrees with it.

## The corrections

### 1. A specification limit is a substitution, not a PCR

Affects **DEV-15** and **TEST-18**.

`ChangeKind` is defined in `backend/app/domain/enums.py`:

> `SUBSTITUTION` — Replaces an approved product, **specification** or method.
> `PCR` — Positive Change Request: adds work, quantity, cost or time.

Both cases change a *specification* recorded in the contract's own
`restrictions_ar`, and neither adds quantity:

| case | text (abridged) | line | restriction in the contract |
|---|---|---|---|
| DEV-15 | raise the permitted integration response time to five seconds | ITM-04 | ألا يتجاوز زمن الاستجابة ثانيتين |
| TEST-18 | cut the critical-fault response time from four hours to two | ITM-08 | زمن استجابة للأعطال الحرجة لا يتجاوز أربع ساعات |

The quantity on both lines is untouched — four integration points stay four,
twelve months of support stay twelve. What changes is the standard the line is
delivered to. Under the glossary that is a substitution; `PCR` was the wrong
label from the start, and would have stayed wrong whatever a model returned.

**Change:** `expected_kind` `PCR` → `SUBSTITUTION`.

Everything else on both cases is unchanged. `expected_changes_approved_product`
stays `true` — a restriction is the specification stage 4 is asked about, and
neither line carries an `approved_product_ar` that could be meant instead.
`expected_recommendation` stays as labelled, and both remain reachable: with the
harness's stub unit rate, TEST-18 prices inside every cap and still reaches
`APPROVE`, and DEV-15 still trips `CONFLICT_RESTRICTION` and reaches
`REQUEST_REVISION`.

### 2. Unclear does not mean unidentifiable

Affects **TEST-24**.

> نحتاج إضافة خادمين وتقليل عدد تراخيص قاعدة البيانات بترخيص واحد في نفس الطلب.
> *Add two servers and reduce the database licences by one, in the same request.*

The request is correctly `UNCLEAR`: it is two opposite changes in one envelope,
and the pipeline should send it back rather than net them off. **That label is
right and is kept.**

But `expected_matched_line_ids: []` was wrong. The request names both lines
plainly — servers are ITM-05, database licences are ITM-06 — and the empty list
scored a model as wrong *for reading the request correctly*. Being unable to
decide what to do with a request is not the same as being unable to tell which
lines it is about; conflating the two teaches the evaluation to reward a worse
answer.

**Change:** `expected_matched_line_ids` `[]` → `["ITM-05", "ITM-06"]`.
`expected_kind` stays `UNCLEAR`.

### 3. Reviewed and kept as labelled

**TEST-11.**

> نطلب تمديد الـ support window ليشمل الـ weekends ضمن اتفاقية مستوى الخدمة الحالية.
> *Extend the support window to cover weekends, under the existing SLA.*

This one is genuinely ambiguous, and the ambiguity is the point of the case.
"Under the existing SLA" can be read two ways — either the current agreement
already covers weekends, which makes it `IN_SCOPE`, or it does not and the
request changes the service standard, which makes it a `SUBSTITUTION`. The
contract does not say. `UNCLEAR` with `REQUEST_REVISION` is the correct
behaviour for a request a careful reader cannot resolve, so **no change**.

It is recorded here rather than left unmentioned so that the next reader knows
it was examined and kept, not overlooked.

## What was deliberately not changed

- **`minimum_confidence` stays at 0.70.** It was not tuned, and in particular
  it was not tuned against the test split.
- **No case was added, removed or reworded.** The audit touches labels only.
- **Nothing was changed on the basis of a model's answer.** Every correction
  above follows from the glossary or the contract breakdown, both of which
  predate every evaluation run.

## How the dual scoring works

`eval/cases.jsonl` carries the original `expected_*` fields unchanged. A
corrected case gains:

```json
"audit": { "expected_kind": "SUBSTITUTION", "reason": "..." }
```

`eval/run.py` scores each run twice — once against `expected_*`, once with the
`audit` overrides applied — and `docs/eval/summary.json` publishes both figures.
A reader who thinks the audit was self-serving can compare them directly.

## Cases affected

| case | split | field | before | after |
|---|---|---|---|---|
| DEV-15 | dev | `expected_kind` | `PCR` | `SUBSTITUTION` |
| TEST-18 | test | `expected_kind` | `PCR` | `SUBSTITUTION` |
| TEST-24 | test | `expected_matched_line_ids` | `[]` | `["ITM-05", "ITM-06"]` |
| TEST-11 | test | — | — | reviewed, unchanged |

3 of 40 cases carry a correction: 1 of 15 dev, 2 of 25 test.
