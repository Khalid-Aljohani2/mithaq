"""Publish a scored evaluation run as ``docs/eval/summary.json``.

    python -m scripts.publish_eval_summary eval/results/test-....json

Reads a report written by ``eval.run`` and writes the committed summary the
API serves at ``/api/eval/summary``. It computes nothing the run did not
already measure except cost, which is the recorded token counts multiplied by
the published per-model rates in ``SOURCES.md``.

Two rules this script exists to enforce:

* **One run, two label sets.** The original and audited figures published
  side by side come from the same run, so a difference between them is the
  labels and not sampling noise.
* **Traceability or nothing.** A report with no git commit is refused rather
  than published without one: a number nobody can tie to code is not evidence.
"""

import argparse
import json
import pathlib
import sys
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.schemas.policy import (
    EvalFieldAccuracy,
    EvalStageLatency,
    EvalSummaryResponse,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SUMMARY_PATH = REPO_ROOT / "docs" / "eval" / "summary.json"

#: USD per million tokens, verified 2026-10-30 against the official pricing
#: page and recorded in SOURCES.md. Haiku is published as *from* these rates,
#: so its figure is a floor rather than an exact charge.
PRICES: dict[str, tuple[Decimal, Decimal]] = {
    "claude-fable-5-1": (Decimal("10"), Decimal("50")),
    "claude-opus-5-5": (Decimal("4"), Decimal("20")),
    "claude-sonnet-5-5": (Decimal("2"), Decimal("10")),
    "claude-haiku-5-5": (Decimal("0.10"), Decimal("0.50")),
}

_MILLION = Decimal("1000000")
_CENTS4 = Decimal("0.0001")
_PCT = Decimal("0.1")

FIELDS = (
    "recommendation",
    "in_scope",
    "kind",
    "matched_line_ids",
    "changes_approved_product",
)


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> Decimal | None:
    """Cost of a run at the published rates, or None for an unpriced model."""
    rates = PRICES.get(model)
    if rates is None:
        return None
    rate_in, rate_out = rates
    total = (Decimal(input_tokens) * rate_in + Decimal(output_tokens) * rate_out) / _MILLION
    return total.quantize(_CENTS4, rounding=ROUND_HALF_UP)


def _pct(value: float) -> Decimal:
    return Decimal(str(value)).quantize(_PCT, rounding=ROUND_HALF_UP)


def build_summary(report: dict[str, Any]) -> EvalSummaryResponse:
    """Turn a run report into the published summary."""
    meta = report["meta"]
    summary = report["summary"]
    audited = report["summary_audited"]
    tokens = report["tokens"]

    commit = meta.get("git_commit") or ""
    if not commit or commit == "unknown":
        msg = "the report records no git commit; a number nobody can trace is not evidence"
        raise SystemExit(msg)

    accuracy = summary["accuracy_pct"]
    audited_accuracy = audited["accuracy_pct"]

    return EvalSummaryResponse(
        available=True,
        generated_at=meta["run_at"],
        commit=commit,
        model=meta["model"],
        split=meta["split"],
        provider=meta["provider"],
        case_count=summary["cases"],
        prompt_versions=meta["prompt_versions"],
        overall_accuracy_pct=_pct(accuracy["recommendation"]),
        audited_accuracy_pct=_pct(audited_accuracy["recommendation"]),
        audited_case_ids=report.get("audited_case_ids", []),
        fields=[
            EvalFieldAccuracy(
                field=field,
                accuracy_pct=_pct(accuracy[field]),
                audited_accuracy_pct=_pct(audited_accuracy[field]),
            )
            for field in FIELDS
        ],
        stage_latency=[
            EvalStageLatency(
                stage=stage,
                median_ms=Decimal(str(stats["median"])),
                p95_ms=Decimal(str(stats["p95"])),
                cases=stats["cases"],
            )
            for stage, stats in summary.get("stage_ms", {}).items()
        ],
        latency_p50_ms=Decimal(str(summary["latency_ms"]["median"])),
        latency_p95_ms=Decimal(str(summary["latency_ms"]["p95"])),
        total_cost_usd=cost_usd(meta["model"], tokens["input_tokens"], tokens["output_tokens"]),
        input_tokens=tokens["input_tokens"],
        output_tokens=tokens["output_tokens"],
        injection_passed=summary["injection"]["passed"],
        injection_total=summary["injection"]["total"],
        errors=summary["errors"],
        notes=(
            "Scored against both the original labels and the audited ones "
            "(docs/eval_label_audit.md), from a single run."
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", help="A JSON report written by eval.run.")
    parser.add_argument("--out", default="", help=f"Defaults to {SUMMARY_PATH}.")
    args = parser.parse_args()

    report = json.loads(pathlib.Path(args.report).read_text(encoding="utf-8"))
    summary = build_summary(report)

    out = pathlib.Path(args.out) if args.out else SUMMARY_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    # The published file carries no `available` flag: it exists, so it is
    # available. The router adds the flag, and its absence is what "no run has
    # been published" means.
    payload = summary.model_dump(mode="json", exclude={"available"})
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    sys.stdout.write(
        f"published {out}\n"
        f"  model            : {summary.model} ({summary.split} split, "
        f"{summary.case_count} cases)\n"
        f"  commit           : {summary.commit}\n"
        f"  recommendation   : {summary.overall_accuracy_pct}% original / "
        f"{summary.audited_accuracy_pct}% audited\n"
        f"  latency p50/p95  : {summary.latency_p50_ms}/{summary.latency_p95_ms} ms\n"
        f"  cost             : ${summary.total_cost_usd}\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
