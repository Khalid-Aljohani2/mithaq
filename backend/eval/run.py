"""Runs an evaluation split through the pipeline and scores it (FR-17, NFR-05).

    python -m eval.run --split test --model claude-sonnet-5-5
    python -m eval.run --split dev  --model claude-haiku-5-5 --limit 5

Scores the four stage outputs that have labels, plus the recommendation, and
reports latency and token usage. Results are written to ``eval/results/`` with
the model, the date, the prompt versions and the git commit, so a number can
always be traced to what produced it.

The split matters: ``dev`` is for tuning prompts, ``test`` is not. Nothing here
enforces that - it is a discipline - but recording the split in every result
file makes a violation visible afterwards.
"""

import argparse
import json
import logging
import pathlib
import statistics
import subprocess
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.analysis.fallback import build_provider
from app.analysis.provider import AnalysisError
from app.config import Settings
from app.domain.change_request import ChangeRequest
from app.domain.enums import Party
from app.domain.models import ChangeLedger
from app.pipeline.runner import PipelineResult, run_analysis
from app.prompts import all_versions
from app.seed.demo_contract import build_government_contract, build_private_contract

EVAL_DIR = pathlib.Path(__file__).parent
CASES_PATH = EVAL_DIR / "cases.jsonl"
RESULTS_DIR = EVAL_DIR / "results"

#: Human-entered figures the harness supplies so costing can run. These are not
#: part of the labelled ground truth - they stand in for what a person would
#: type on the intake form, and keep money off the model's path (NFR-03).
STUB_AMOUNT = Decimal("150000")
STUB_UNIT_RATE = Decimal("50000")
STUB_DAYS = 0

#: A large amount for the one case built to breach a legal cap.
LEGAL_CAP_AMOUNT = Decimal("1008000")


class TokenCollector(logging.Handler):
    """Captures the token counts the provider logs (NFR-12 feeding NFR-05)."""

    def __init__(self) -> None:
        super().__init__(level=logging.INFO)
        self.input_tokens = 0
        self.output_tokens = 0
        self.calls = 0

    def emit(self, record: logging.LogRecord) -> None:
        if record.getMessage() != "ai_call":
            return
        self.calls += 1
        self.input_tokens += getattr(record, "input_tokens", None) or 0
        self.output_tokens += getattr(record, "output_tokens", None) or 0


def load_cases(split: str | None) -> list[dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in CASES_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return [r for r in rows if split is None or r["split"] == split]


def git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=EVAL_DIR.parent.parent,
        ).stdout.strip()
    except Exception:
        return "unknown"


def build_request(case: dict[str, Any]) -> ChangeRequest:
    """Turn a labelled case into a change request the pipeline can run."""
    amount = LEGAL_CAP_AMOUNT if case["category"] == "legal_cap" else STUB_AMOUNT
    return ChangeRequest(
        id=case["id"],
        contract_id=case["contract_id"],
        requester_name="م. مُقيِّم",
        requester_party=Party.CONTRACTOR,
        submitted_at=datetime.now(UTC),
        body_ar=case["text"],
        # Complete documents, so stage 2 never short-circuits the run. What is
        # being measured is the analysis, not the checklist.
        attachments=("طلب تغيير رسمي", "عرض سعر أو تحليل تكلفة", "برنامج زمني محدّث"),
        human_entered_amount=amount,
        human_entered_unit_rate=STUB_UNIT_RATE,
        human_entered_days=STUB_DAYS,
    )


#: Label fields an audit entry is allowed to override. Anything else in an
#: ``audit`` object is prose for a human and is ignored here, so a typo in a
#: field name cannot silently change what is scored.
AUDITABLE_FIELDS = (
    "expected_in_scope",
    "expected_kind",
    "expected_matched_line_ids",
    "expected_changes_approved_product",
    "expected_recommendation",
)


def audited(case: dict[str, Any]) -> dict[str, Any]:
    """The case as the label audit corrected it (docs/eval_label_audit.md).

    Returns the case unchanged when it carries no audit, so an un-audited case
    is scored identically by both passes and contributes no difference.
    """
    overrides = {k: v for k, v in case.get("audit", {}).items() if k in AUDITABLE_FIELDS}
    return {**case, **overrides} if overrides else case


def score_case(case: dict[str, Any], result: PipelineResult) -> dict[str, Any]:
    """Compare one run against its label."""
    request = result.request
    scope_stage = next((s for s in result.stages if s.stage.value == "SCOPE_ANALYSIS"), None)
    tech_stage = next((s for s in result.stages if s.stage.value == "TECHNICAL_ASSESSMENT"), None)

    got_in_scope = bool(scope_stage.payload.get("in_scope")) if scope_stage else None
    got_kind = request.kind.value if request.kind else None
    got_matched = sorted(request.matched_line_ids)
    got_product = bool(tech_stage.payload.get("changes_approved_product")) if tech_stage else None
    got_rec = request.recommendation.value if request.recommendation else None

    expected_matched = sorted(case["expected_matched_line_ids"])

    return {
        "id": case["id"],
        # Per-stage wall time, so a latency figure can be attributed rather
        # than just reported. The runner already times every stage; this only
        # carries the numbers out.
        "stage_ms": {stage.stage.value: stage.duration_ms for stage in result.stages},
        "split": case["split"],
        "category": case["category"],
        "difficulty": case["difficulty"],
        "text": case["text"],
        "in_scope": {
            "expected": case["expected_in_scope"],
            "got": got_in_scope,
            "ok": got_in_scope == case["expected_in_scope"],
        },
        "kind": {
            "expected": case["expected_kind"],
            "got": got_kind,
            "ok": got_kind == case["expected_kind"],
        },
        "matched_line_ids": {
            "expected": expected_matched,
            "got": got_matched,
            "ok": got_matched == expected_matched,
        },
        "changes_approved_product": {
            "expected": case["expected_changes_approved_product"],
            "got": got_product,
            "ok": got_product == case["expected_changes_approved_product"],
        },
        "recommendation": {
            "expected": case["expected_recommendation"],
            "got": got_rec,
            "ok": got_rec == case["expected_recommendation"],
        },
        "error": None,
    }


def failed_case(case: dict[str, Any], error: str) -> dict[str, Any]:
    """A case the pipeline could not complete scores zero on every field."""
    blank = {"expected": None, "got": None, "ok": False}
    return {
        "id": case["id"],
        "split": case["split"],
        "category": case["category"],
        "difficulty": case["difficulty"],
        "text": case["text"],
        "in_scope": {**blank, "expected": case["expected_in_scope"]},
        "kind": {**blank, "expected": case["expected_kind"]},
        "matched_line_ids": {**blank, "expected": case["expected_matched_line_ids"]},
        "changes_approved_product": {
            **blank,
            "expected": case["expected_changes_approved_product"],
        },
        "recommendation": {**blank, "expected": case["expected_recommendation"]},
        "stage_ms": {},
        "error": error,
    }


def stage_latencies(scored: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """Median and p95 per stage, over the cases that reached each stage.

    A stage a case never reached contributes nothing rather than a zero: an
    analysis that stopped at stage 2 did not run stage 3 in 0 ms.
    """
    per_stage: dict[str, list[float]] = {}
    for case in scored:
        for stage, ms in case.get("stage_ms", {}).items():
            per_stage.setdefault(stage, []).append(float(ms))
    return {
        stage: {
            "median": round(statistics.median(values), 1),
            "p95": round(
                statistics.quantiles(values, n=20)[-1] if len(values) > 1 else values[0], 1
            ),
            "cases": len(values),
        }
        for stage, values in sorted(per_stage.items())
    }


def percent(hits: int, total: int) -> float:
    return round(100.0 * hits / total, 1) if total else 0.0


def summarise(scored: list[dict[str, Any]], latencies: list[float]) -> dict[str, Any]:
    total = len(scored)
    fields = ("in_scope", "kind", "matched_line_ids", "changes_approved_product", "recommendation")
    accuracy = {field: percent(sum(1 for s in scored if s[field]["ok"]), total) for field in fields}

    # Confusion matrix for kind: expected -> got -> count.
    matrix: dict[str, Counter[str]] = {}
    for s in scored:
        expected = str(s["kind"]["expected"])
        got = str(s["kind"]["got"])
        matrix.setdefault(expected, Counter())[got] += 1

    injection = [s for s in scored if s["category"] == "prompt_injection"]
    injection_passed = [s for s in injection if s["kind"]["ok"] and s["recommendation"]["ok"]]

    return {
        "cases": total,
        "accuracy_pct": accuracy,
        "kind_confusion": {k: dict(v) for k, v in sorted(matrix.items())},
        "injection": {
            "total": len(injection),
            "passed": len(injection_passed),
            "failed_ids": [s["id"] for s in injection if s not in injection_passed],
        },
        "errors": sum(1 for s in scored if s["error"]),
        "latency_ms": {
            "median": round(statistics.median(latencies), 1) if latencies else 0.0,
            "p95": round(
                statistics.quantiles(latencies, n=20)[-1]
                if len(latencies) > 1
                else (latencies[0] if latencies else 0.0),
                1,
            ),
            "min": round(min(latencies), 1) if latencies else 0.0,
            "max": round(max(latencies), 1) if latencies else 0.0,
        },
        "stage_ms": stage_latencies(scored),
        "accuracy_by_difficulty": {
            level: percent(
                sum(1 for s in scored if s["difficulty"] == level and s["recommendation"]["ok"]),
                sum(1 for s in scored if s["difficulty"] == level),
            )
            for level in ("easy", "medium", "hard")
        },
    }


def run(split: str | None, model: str, limit: int | None) -> dict[str, Any]:
    cases = load_cases(split)
    if limit:
        cases = cases[:limit]

    settings = Settings(llm_model=model) if model else Settings()
    provider = build_provider(settings)

    collector = TokenCollector()
    ai_logger = logging.getLogger("mithaq.ai")
    ai_logger.addHandler(collector)
    # Without this the logger inherits WARNING from root and the ai_call records
    # never reach the collector, so every run reported zero tokens.
    previous_level = ai_logger.level
    ai_logger.setLevel(logging.INFO)

    contracts = {c.id: c for c in (build_private_contract(), build_government_contract())}

    # The same run, scored against two label sets. Never two runs: a difference
    # between the columns has to be the labels, not sampling noise.
    scored: list[dict[str, Any]] = []
    scored_audited: list[dict[str, Any]] = []
    latencies: list[float] = []

    for index, case in enumerate(cases, start=1):
        contract = contracts[case["contract_id"]]
        request = build_request(case)
        started = time.perf_counter()
        try:
            result = run_analysis(
                contract,
                ChangeLedger(contract_id=contract.id),
                request,
                provider,
                Decimal("0"),
                0,
            )
            latencies.append((time.perf_counter() - started) * 1000)
            scored.append(score_case(case, result))
            scored_audited.append(score_case(audited(case), result))
            mark = "ok " if scored[-1]["recommendation"]["ok"] else "MISS"
        except (AnalysisError, Exception) as error:  # noqa: B014 - report, never crash the run
            latencies.append((time.perf_counter() - started) * 1000)
            message = f"{type(error).__name__}: {error}"
            scored.append(failed_case(case, message))
            scored_audited.append(failed_case(audited(case), message))
            mark = "ERR "
        sys.stderr.write(f"  [{index:>2}/{len(cases)}] {mark} {case['id']}\n")

    ai_logger.removeHandler(collector)
    ai_logger.setLevel(previous_level)

    return {
        "meta": {
            "model": settings.default_model,
            "split": split or "all",
            "provider": provider.name,
            "recorded": getattr(provider, "recorded", False),
            "run_at": datetime.now(UTC).isoformat(),
            "git_commit": git_commit(),
            "prompt_versions": all_versions(),
            "cases_file": CASES_PATH.name,
        },
        "summary": summarise(scored, latencies),
        "summary_audited": summarise(scored_audited, latencies),
        "audited_case_ids": [c["id"] for c in cases if c.get("audit")],
        "tokens": {
            "ai_calls": collector.calls,
            "input_tokens": collector.input_tokens,
            "output_tokens": collector.output_tokens,
        },
        "cases": scored,
        "cases_audited": scored_audited,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Mithaq evaluation set.")
    parser.add_argument("--split", choices=["dev", "test", "all"], default="test")
    parser.add_argument("--model", default="", help="Model id; defaults to settings.")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--out", default="", help="Output path; defaults to eval/results/.")
    args = parser.parse_args()

    split = None if args.split == "all" else args.split
    report = run(split, args.model, args.limit)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    model_slug = report["meta"]["model"].replace("/", "-")
    out = (
        pathlib.Path(args.out)
        if args.out
        else RESULTS_DIR / f"{args.split}-{model_slug}-{stamp}.json"
    )
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = report["summary"]
    audited_summary = report["summary_audited"]
    accuracy = summary["accuracy_pct"]
    audited_accuracy = audited_summary["accuracy_pct"]
    injection = summary["injection"]
    latency = summary["latency_ms"]
    tokens = report["tokens"]

    lines = [
        "",
        f"{report['meta']['model']}  split={report['meta']['split']}  "
        f"provider={report['meta']['provider']}",
        "                            original  audited",
        f"  recommendation accuracy : {accuracy['recommendation']:>7}% "
        f"{audited_accuracy['recommendation']:>7}%",
        f"  scope decision          : {accuracy['in_scope']:>7}% "
        f"{audited_accuracy['in_scope']:>7}%",
        f"  kind                    : {accuracy['kind']:>7}% {audited_accuracy['kind']:>7}%",
        f"  matched lines           : {accuracy['matched_line_ids']:>7}% "
        f"{audited_accuracy['matched_line_ids']:>7}%",
        f"  technical flag          : {accuracy['changes_approved_product']:>7}% "
        f"{audited_accuracy['changes_approved_product']:>7}%",
        f"  injection passed        : {injection['passed']}/{injection['total']}",
        f"  latency ms median/p95   : {latency['median']}/{latency['p95']}",
        f"  tokens in/out           : {tokens['input_tokens']}/{tokens['output_tokens']}",
        f"  errors                  : {summary['errors']}",
        f"  written to              : {out}",
        "",
    ]
    sys.stdout.write(chr(10).join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
