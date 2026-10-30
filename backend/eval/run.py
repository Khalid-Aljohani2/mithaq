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
        "error": error,
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
    logging.getLogger("mithaq.ai").addHandler(collector)

    contracts = {c.id: c for c in (build_private_contract(), build_government_contract())}

    scored: list[dict[str, Any]] = []
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
            mark = "ok " if scored[-1]["recommendation"]["ok"] else "MISS"
        except (AnalysisError, Exception) as error:  # noqa: B014 - report, never crash the run
            latencies.append((time.perf_counter() - started) * 1000)
            scored.append(failed_case(case, f"{type(error).__name__}: {error}"))
            mark = "ERR "
        sys.stderr.write(f"  [{index:>2}/{len(cases)}] {mark} {case['id']}\n")

    logging.getLogger("mithaq.ai").removeHandler(collector)

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
        "tokens": {
            "ai_calls": collector.calls,
            "input_tokens": collector.input_tokens,
            "output_tokens": collector.output_tokens,
        },
        "cases": scored,
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
    accuracy = summary["accuracy_pct"]
    injection = summary["injection"]
    latency = summary["latency_ms"]
    tokens = report["tokens"]

    lines = [
        "",
        f"{report['meta']['model']}  split={report['meta']['split']}  "
        f"provider={report['meta']['provider']}",
        f"  recommendation accuracy : {accuracy['recommendation']}%",
        f"  scope decision          : {accuracy['in_scope']}%",
        f"  kind                    : {accuracy['kind']}%",
        f"  matched lines           : {accuracy['matched_line_ids']}%",
        f"  technical flag          : {accuracy['changes_approved_product']}%",
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
