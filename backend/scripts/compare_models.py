"""Runs the TEST split on each model and prints the comparison table.

    python scripts/compare_models.py

Needs a working LLM_API_KEY and LLM_PROVIDER=anthropic. Every run costs money:
25 cases x 4 AI stages x 4 models = 400 model calls.

It never touches the dev split and never changes a prompt, so running it does
not tune anything on the test set.
"""

import json
import pathlib
import subprocess
import sys
from datetime import UTC, datetime

BACKEND = pathlib.Path(__file__).parent.parent
RESULTS = BACKEND / "eval" / "results"

MODELS = [
    "claude-haiku-5-5",
    "claude-sonnet-5-5",
    "claude-opus-5-5",
    "claude-fable-5-1",
]


def run_one(model: str) -> pathlib.Path:
    """Run the test split on one model and return its result file."""
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = RESULTS / f"test-{model}-{stamp}.json"
    sys.stderr.write(f"\n=== {model} ===\n")
    subprocess.run(
        [sys.executable, "-m", "eval.run", "--split", "test", "--model", model, "--out", str(out)],
        cwd=BACKEND,
        check=True,
    )
    return out


def comparison_table(reports: list[dict]) -> str:
    """The table the comparison is for."""
    header = (
        "| model | recommendation | scope | kind | matched lines | technical | "
        "injection | median ms | p95 ms | in tok | out tok |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|"
    )
    rows = []
    for report in reports:
        accuracy = report["summary"]["accuracy_pct"]
        injection = report["summary"]["injection"]
        latency = report["summary"]["latency_ms"]
        tokens = report["tokens"]
        rows.append(
            f"| `{report['meta']['model']}` "
            f"| {accuracy['recommendation']}% "
            f"| {accuracy['in_scope']}% "
            f"| {accuracy['kind']}% "
            f"| {accuracy['matched_line_ids']}% "
            f"| {accuracy['changes_approved_product']}% "
            f"| {injection['passed']}/{injection['total']} "
            f"| {latency['median']} "
            f"| {latency['p95']} "
            f"| {tokens['input_tokens']} "
            f"| {tokens['output_tokens']} |"
        )
    return header + "\n" + "\n".join(rows)


def failure_list(report: dict) -> str:
    """Every failed case with the model's answer next to the expected one."""
    lines = [f"\n### {report['meta']['model']} - failures\n"]
    failures = [c for c in report["cases"] if not c["recommendation"]["ok"] or c["error"]]
    if not failures:
        lines.append("None.")
        return "\n".join(lines)
    lines.append("| id | category | field | expected | got |")
    lines.append("|---|---|---|---|---|")
    for case in failures:
        if case["error"]:
            lines.append(
                f"| `{case['id']}` | {case['category']} | - | - | ERROR: {case['error']} |"
            )
            continue
        for field in (
            "in_scope",
            "kind",
            "matched_line_ids",
            "changes_approved_product",
            "recommendation",
        ):
            entry = case[field]
            if not entry["ok"]:
                lines.append(
                    f"| `{case['id']}` | {case['category']} | {field} "
                    f"| `{entry['expected']}` | `{entry['got']}` |"
                )
    return "\n".join(lines)


def main() -> int:
    RESULTS.mkdir(parents=True, exist_ok=True)
    reports = []
    for model in MODELS:
        path = run_one(model)
        reports.append(json.loads(path.read_text(encoding="utf-8")))

    out = BACKEND.parent / "docs" / "eval_comparison.md"
    body = [
        "# Model comparison - TEST split",
        "",
        f"Generated {datetime.now(UTC).isoformat()} from "
        f"`{reports[0]['meta']['git_commit']}`, "
        f"prompts {reports[0]['meta']['prompt_versions']}.",
        "",
        "25 test cases. Prompts were not tuned on this split.",
        "",
        comparison_table(reports),
        "",
        "## Failures, with the model's answer beside the expected one",
        "",
        "A failure here is not automatically a model error - check the label too.",
    ]
    for report in reports:
        body.append(failure_list(report))
    out.write_text("\n".join(body) + "\n", encoding="utf-8")

    sys.stdout.write("\n" + comparison_table(reports) + "\n")
    sys.stdout.write(f"\nwritten to {out}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
