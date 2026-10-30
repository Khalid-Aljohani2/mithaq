"""Fills the model-answer column in ``docs/eval_sample.md``.

    python scripts/fill_eval_sample.py [--model claude-sonnet-5-5]

Reads the most recent TEST-split result for the model and rewrites the
``_pending_`` cells with what that model actually answered. The expected
column is never touched - the point of the table is to compare them.
"""

import argparse
import json
import pathlib
import re
import sys

BACKEND = pathlib.Path(__file__).parent.parent
RESULTS = BACKEND / "eval" / "results"
SAMPLE = BACKEND.parent / "docs" / "eval_sample.md"

ROW = re.compile(r"^\| (\d+) \| `([A-Z0-9-]+)` \|(.*)\| _pending_ \|$")


def latest_result(model: str) -> pathlib.Path | None:
    candidates = sorted(RESULTS.glob(f"test-{model}-*.json"))
    return candidates[-1] if candidates else None


def cell(case: dict) -> str:
    """One model answer, in the same shape as the expected cell.

    A field that disagrees with the label is bolded, so a reviewer's eye lands
    on exactly the cells worth arguing about.
    """

    def mark(field: str, text: str) -> str:
        return text if case[field]["ok"] else f"**{text}**"

    if case["error"]:
        return f"ERROR: {case['error'][:80]}"

    in_scope = str(case["in_scope"]["got"]).lower()
    kind = case["kind"]["got"]
    lines = ",".join(case["matched_line_ids"]["got"] or []) or "-"
    product = str(case["changes_approved_product"]["got"]).lower()
    recommendation = case["recommendation"]["got"]

    return "<br>".join(
        (
            mark("in_scope", f"in_scope={in_scope}"),
            mark("kind", f"kind={kind}"),
            mark("matched_line_ids", f"lines={lines}"),
            mark("changes_approved_product", f"product={product}"),
            mark("recommendation", f"**{recommendation}**"),
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="claude-sonnet-5-5")
    args = parser.parse_args()

    path = latest_result(args.model)
    if path is None:
        sys.stderr.write(
            f"no TEST-split result for {args.model} in {RESULTS}.\n"
            f"Run:  python -m eval.run --split test --model {args.model}\n"
        )
        return 1

    report = json.loads(path.read_text(encoding="utf-8"))
    by_id = {c["id"]: c for c in report["cases"]}

    out_lines = []
    filled = 0
    for line in SAMPLE.read_text(encoding="utf-8").splitlines():
        match = ROW.match(line)
        if match and match.group(2) in by_id:
            out_lines.append(line.replace("| _pending_ |", f"| {cell(by_id[match.group(2)])} |"))
            filled += 1
        else:
            out_lines.append(line)

    SAMPLE.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    sys.stdout.write(f"filled {filled} rows in {SAMPLE} from {path.name}\n")
    sys.stdout.write("bold = disagrees with the label; check which one is wrong\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
