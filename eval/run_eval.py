"""Measure how well the extractor finds requirements.

Usage:
    python -m eval.run_eval                  # rule mode
    python -m eval.run_eval --mode llm       # needs OPENAI_API_KEY
    python -m eval.run_eval --write          # also save eval/results.md
    python -m eval.run_eval --min-f1 0.7     # exit 1 if auto-accepted F1 is lower

How scoring works (per case, per category):
  TP  the category was found AND the expected value appears in the extracted text
  FP  the category was found but it was not expected, or the value was wrong
  FN  the category was expected but not found (or found with a wrong value)

Two views are reported:
  auto-accepted  only items the tool did NOT flag for review (what goes straight to estimating)
  all items      every item, including those flagged for review
"""
import argparse
import json
import sys
from pathlib import Path

from app import config
from app.extractor import extract_with_llm, extract_with_rules
from app.schemas import CATEGORIES

DATA = Path(__file__).parent / "dataset.jsonl"
OUT = Path(__file__).parent / "results.md"


def load_cases():
    return [json.loads(line) for line in DATA.read_text(encoding="utf-8").splitlines() if line.strip()]


def run(cases, mode):
    fn = extract_with_llm if mode == "llm" else extract_with_rules
    return [fn(c["text"]) for c in cases]


def score(cases, results, confident_only):
    stats = {c: {"tp": 0, "fp": 0, "fn": 0} for c in CATEGORIES}
    for case, res in zip(cases, results):
        for cat in CATEGORIES:
            reqs = [r for r in res.requirements if r.category == cat and not (confident_only and r.needs_review)]
            exp = case["expected"].get(cat)
            hit = bool(exp) and any(exp in (r.detail + " " + r.source_sentence).lower() for r in reqs)
            if hit:
                stats[cat]["tp"] += 1
            else:
                if reqs:
                    stats[cat]["fp"] += 1
                if exp:
                    stats[cat]["fn"] += 1
    return stats


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def table(stats):
    lines = ["| Category | Precision | Recall | F1 | TP | FP | FN |", "|---|---|---|---|---|---|---|"]
    total = {"tp": 0, "fp": 0, "fn": 0}
    for cat in CATEGORIES:
        s = stats[cat]
        p, r, f = prf(**s)
        lines.append(f"| {cat} | {p:.2f} | {r:.2f} | {f:.2f} | {s['tp']} | {s['fp']} | {s['fn']} |")
        for k in total:
            total[k] += s[k]
    p, r, f = prf(**total)
    lines.append(f"| **All (micro)** | **{p:.2f}** | **{r:.2f}** | **{f:.2f}** | {total['tp']} | {total['fp']} | {total['fn']} |")
    return "\n".join(lines), f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["rules", "llm"], default="rules")
    ap.add_argument("--min-f1", type=float, default=None)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    if args.mode == "llm" and not config.get("OPENAI_API_KEY"):
        sys.exit("OPENAI_API_KEY is not set, so LLM mode cannot run.")

    cases = load_cases()
    results = run(cases, args.mode)
    flagged = sum(r.needs_review for res in results for r in res.requirements)
    total = sum(len(res.requirements) for res in results)

    t_auto, f_auto = table(score(cases, results, True))
    t_all, f_all = table(score(cases, results, False))
    report = (
        f"# Evaluation ({args.mode} mode, {len(cases)} made-up cases)\n\n"
        f"## Auto-accepted items (not flagged for review)\n\n{t_auto}\n\n"
        f"## All items (including flagged)\n\n{t_all}\n\n"
        f"Items flagged for review: {flagged} of {total}.\n"
    )
    print(report)
    if args.write:
        OUT.write_text(report, encoding="utf-8")
    if args.min_f1 is not None and f_auto < args.min_f1:
        sys.exit(f"Auto-accepted F1 {f_auto:.2f} is below the minimum {args.min_f1:.2f}")


if __name__ == "__main__":
    main()
