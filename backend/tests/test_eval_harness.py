"""The evaluation harness (FR-17), exercised without a model.

Two stub providers do the work a model would: one that answers every case
correctly and one that answers every case the same wrong way. A harness that
cannot tell those two apart would report numbers that mean nothing, so both
directions are asserted.
"""

import json
from decimal import Decimal
from typing import Any

import pytest

from app.analysis.provider import AnalysisProvider
from app.analysis.schemas import (
    IntakeInput,
    IntakeOutput,
    NarrativeInput,
    NarrativeOutput,
    RiskInput,
    RiskOutput,
    ScopeInput,
    ScopeOutput,
    TechnicalInput,
    TechnicalOutput,
    VODraftInput,
    VODraftOutput,
)
from app.domain.enums import ChangeKind, ImpactType
from eval.run import CASES_PATH, load_cases, run, summarise

CASES = load_cases(None)
BY_ID = {c["id"]: c for c in CASES}


class StubProvider(AnalysisProvider):
    """Answers from the labels, so the harness can be scored against itself."""

    name = "stub"
    recorded = False

    def __init__(self, *, correct: bool = True) -> None:
        self.correct = correct

    def _case(self, cr_id: str) -> dict[str, Any]:
        return BY_ID[cr_id]

    def intake(self, request: IntakeInput) -> IntakeOutput:
        return IntakeOutput(
            provider=self.name,
            recorded=False,
            confidence=Decimal("0.9"),
            requester_name_ar="م. مُقيِّم",
            requested_change_ar="طلب",
            impact_type=ImpactType.COST,
            quoted_phrase_ar="طلب",
        )

    def scope_analysis(self, request: ScopeInput) -> ScopeOutput:
        case = self._case(request.cr_id)
        if not self.correct:
            # Always the same wrong answer, whatever the case says.
            return ScopeOutput(
                provider=self.name,
                recorded=False,
                confidence=Decimal("0.9"),
                in_scope=False,
                kind=ChangeKind.NCR,
                matched_line_ids=("ITM-01",),
                quantity_delta=Decimal("1"),
            )
        kind = ChangeKind(case["expected_kind"])
        matched = tuple(case["expected_matched_line_ids"])
        needs_quantity = kind in {ChangeKind.PCR, ChangeKind.NCR, ChangeKind.SUBSTITUTION}
        return ScopeOutput(
            provider=self.name,
            recorded=False,
            confidence=Decimal("0.9"),
            in_scope=case["expected_in_scope"],
            kind=kind,
            matched_line_ids=matched,
            quantity_delta=Decimal("1") if (needs_quantity and matched) else None,
            substitute_product_ar="بديل" if kind is ChangeKind.SUBSTITUTION else None,
        )

    def technical_assessment(self, request: TechnicalInput) -> TechnicalOutput:
        case = self._case(request.cr_id)
        flag = case["expected_changes_approved_product"] if self.correct else True
        # A faithful stub reports the conflict a restriction_conflict case was
        # built around; without it the recommendation could never be right.
        conflicts = (
            ("قيد تعاقدي",) if self.correct and case["category"] == "restriction_conflict" else ()
        )
        return TechnicalOutput(
            provider=self.name,
            recorded=False,
            confidence=Decimal("0.9"),
            changes_approved_product=flag,
            affected_line_ids=tuple(case["expected_matched_line_ids"]),
            restriction_conflicts_ar=conflicts,
        )

    def risk_assessment(self, request: RiskInput) -> RiskOutput:
        return RiskOutput(
            provider=self.name, recorded=False, confidence=Decimal("0.9"), overall_risk_level="LOW"
        )

    def recommendation_narrative(self, request: NarrativeInput) -> NarrativeOutput:
        return NarrativeOutput(
            provider=self.name, recorded=False, confidence=Decimal("0.9"), summary_ar="ملخص"
        )

    def vo_draft(self, request: VODraftInput) -> VODraftOutput:
        return VODraftOutput(
            provider=self.name, recorded=False, confidence=Decimal("0.9"), scope_ar="نطاق"
        )


@pytest.fixture
def stub(monkeypatch: pytest.MonkeyPatch):  # noqa: ANN201
    def install(correct: bool) -> None:
        monkeypatch.setattr(
            "eval.run.build_provider", lambda _settings: StubProvider(correct=correct)
        )

    return install


# ---------------------------------------------------------------------------
# The case file itself
# ---------------------------------------------------------------------------


def test_case_file_has_forty_cases_split_fifteen_twenty_five() -> None:
    assert len(CASES) == 40
    assert sum(1 for c in CASES if c["split"] == "dev") == 15
    assert sum(1 for c in CASES if c["split"] == "test") == 25


def test_every_case_declares_its_split() -> None:
    assert all(c["split"] in {"dev", "test"} for c in CASES)


def test_case_ids_are_unique() -> None:
    assert len({c["id"] for c in CASES}) == len(CASES)


def test_required_coverage_is_present() -> None:
    """Every category the requirement names has at least one case."""
    categories = {c["category"] for c in CASES}
    for required in (
        "in_scope_reworded",
        "pcr_new_item",
        "pcr_quantity_increase",
        "ncr_reduction",
        "substitution",
        "restriction_conflict",
        "ambiguous",
        "dialect",
        "code_switching",
        "prompt_injection",
    ):
        assert required in categories, required


def test_at_least_three_injection_cases() -> None:
    assert sum(1 for c in CASES if c["category"] == "prompt_injection") >= 3


def test_labels_are_internally_consistent() -> None:
    """in_scope and kind must agree, and in-scope must close as in scope."""
    for case in CASES:
        assert case["expected_in_scope"] == (case["expected_kind"] == "IN_SCOPE"), case["id"]
        if case["expected_kind"] == "IN_SCOPE":
            assert case["expected_recommendation"] == "CLOSE_IN_SCOPE", case["id"]


def test_matched_line_ids_exist_in_the_contract() -> None:
    from app.seed.demo_contract import build_private_contract

    known = {line.id for line in build_private_contract().breakdown}
    for case in CASES:
        for line_id in case["expected_matched_line_ids"]:
            assert line_id in known, (case["id"], line_id)


def test_the_file_is_valid_jsonl() -> None:
    for line in CASES_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            json.loads(line)


# ---------------------------------------------------------------------------
# The scorer
# ---------------------------------------------------------------------------


def test_a_correct_provider_scores_high(stub) -> None:  # noqa: ANN001
    stub(True)
    report = run("dev", "claude-sonnet-5-5", None)
    accuracy = report["summary"]["accuracy_pct"]
    # The labelled stage outputs are reproduced exactly.
    assert accuracy["in_scope"] == 100.0
    assert accuracy["kind"] == 100.0
    assert accuracy["matched_line_ids"] == 100.0
    assert accuracy["changes_approved_product"] == 100.0
    assert report["summary"]["errors"] == 0
    # A stub that reproduces every labelled field should also land the
    # recommendation, since the recommendation is derived from those fields.
    assert accuracy["recommendation"] == 100.0


def test_a_wrong_provider_scores_low(stub) -> None:  # noqa: ANN001
    """If this passed too, the harness would be measuring nothing."""
    stub(False)
    report = run("dev", "claude-sonnet-5-5", None)
    accuracy = report["summary"]["accuracy_pct"]
    assert accuracy["kind"] < 50.0
    assert accuracy["in_scope"] < 100.0


def test_report_records_model_split_commit_and_prompt_versions(stub) -> None:  # noqa: ANN001
    stub(True)
    meta = run("dev", "claude-opus-5-5", 3)["meta"]
    assert meta["model"] == "claude-opus-5-5"
    assert meta["split"] == "dev"
    assert meta["git_commit"]
    assert meta["prompt_versions"]["INTAKE"] == "v1"
    assert meta["run_at"]


def test_only_the_requested_split_runs(stub) -> None:  # noqa: ANN001
    stub(True)
    report = run("test", "claude-sonnet-5-5", None)
    assert report["summary"]["cases"] == 25
    assert all(c["split"] == "test" for c in report["cases"])


def test_confusion_matrix_is_reported(stub) -> None:  # noqa: ANN001
    stub(False)
    matrix = run("dev", "claude-sonnet-5-5", None)["summary"]["kind_confusion"]
    # Everything was answered NCR, so every expected row points at NCR.
    assert all(set(row) == {"NCR"} for row in matrix.values())


def test_injection_cases_are_counted_separately(stub) -> None:  # noqa: ANN001
    stub(True)
    injection = run("test", "claude-sonnet-5-5", None)["summary"]["injection"]
    assert injection["total"] == 3
    assert injection["passed"] == 3
    assert injection["failed_ids"] == []


def test_latency_and_token_fields_are_present(stub) -> None:  # noqa: ANN001
    stub(True)
    report = run("dev", "claude-sonnet-5-5", 3)
    assert report["summary"]["latency_ms"]["median"] >= 0
    assert report["summary"]["latency_ms"]["p95"] >= 0
    assert "input_tokens" in report["tokens"]
    assert "output_tokens" in report["tokens"]


def test_a_failing_case_is_recorded_not_crashed(stub, monkeypatch) -> None:  # noqa: ANN001
    """One broken case must not take the whole run down."""
    stub(True)

    def explode(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("stage blew up")

    monkeypatch.setattr("eval.run.run_analysis", explode)
    report = run("dev", "claude-sonnet-5-5", 2)
    assert report["summary"]["errors"] == 2
    assert all(c["error"] for c in report["cases"])
    assert report["summary"]["accuracy_pct"]["recommendation"] == 0.0


def test_summarise_handles_an_empty_run() -> None:
    summary = summarise([], [])
    assert summary["cases"] == 0
    assert summary["accuracy_pct"]["recommendation"] == 0.0
