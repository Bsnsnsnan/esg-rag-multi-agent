"""
Measures how much the Assessment Agent's score varies when it re-scores the exact same text.
Re-assesses the iteration-1 drafts from a run's logs and compares with the logged scores.

Usage: python assessor_noise.py [--run v2] [--repeats 1]
Out:   results/assessor_noise.json, results/assessor_noise.md
"""
import os
import sys
import json
import glob
import time

import numpy as np

from assessment_agent import assess_section, CRITERIA

PILLARS = ["Environmental", "Social", "Governance"]


def with_retry(fn, *args, retries=5):
    for attempt in range(retries):
        try:
            return fn(*args)
        except Exception as e:
            if "429" not in str(e) or attempt == retries - 1:
                raise
            time.sleep(15 * (attempt + 1))


def main():
    args = sys.argv[1:]
    run = args[args.index("--run") + 1] if "--run" in args else "v2"
    repeats = int(args[args.index("--repeats") + 1]) if "--repeats" in args else 1

    rows = []
    for path in sorted(glob.glob(os.path.join("results", run, "loop_logs", "*_log.json"))):
        log = json.load(open(path, encoding="utf-8"))
        r0 = log["rounds"][0]
        for p in PILLARS:
            sec = r0["sections"][p]
            att = sec.get("attempt")
            text = att["draft"] if att else sec["draft"]
            original = att["assessment"] if att else sec["full_assessment"]
            for k in range(repeats):
                print(f"{log['company']} / {p} (repeat {k + 1})")
                a = with_retry(assess_section, log["company"], p, text)
                orig_c = {c["criterion"]: c["score"] for c in original["criterion_scores"]}
                new_c = {c["criterion"]: c["score"] for c in a["criterion_scores"]}
                rows.append({"company": log["company"], "pillar": p,
                             "original": original["overall_score"], "rescore": a["overall_score"],
                             "diff": round(a["overall_score"] - original["overall_score"], 2),
                             "criteria_same": sum(orig_c[c] == new_c[c] for c in CRITERIA),
                             "incons_original": len(original.get("inconsistencies", [])),
                             "incons_rescore": len(a.get("inconsistencies", []))})

    diffs = np.array([r["diff"] for r in rows])
    by_company = {}
    for r in rows:
        by_company.setdefault(r["company"], []).append(r["diff"])
    report_diffs = np.array([np.mean(v) for v in by_company.values()])
    summary = {
        "run": run, "repeats": repeats, "n_sections": len(rows),
        "section_mean_abs_diff": round(float(np.abs(diffs).mean()), 2),
        "section_sd_diff": round(float(diffs.std(ddof=1)), 2) if len(diffs) > 1 else None,
        "section_max_abs_diff": round(float(np.abs(diffs).max()), 2),
        "report_mean_abs_diff": round(float(np.abs(report_diffs).mean()), 2),
        "criterion_exact_agreement": round(sum(r["criteria_same"] for r in rows) / (6 * len(rows)), 2),
        "inconsistency_count_agreement": round(sum(r["incons_original"] == r["incons_rescore"] for r in rows) / len(rows), 2),
        "rows": rows,
    }
    os.makedirs("results", exist_ok=True)
    with open("results/assessor_noise.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    md = [f"# Assessor re-scoring variation ({run}, {len(rows)} sections)\n",
          f"- Mean absolute change in a section score when the same text is re-scored: **{summary['section_mean_abs_diff']}** "
          f"(max {summary['section_max_abs_diff']}, SD {summary['section_sd_diff']}).",
          f"- Mean absolute change in a report score (mean of 3 sections): **{summary['report_mean_abs_diff']}**.",
          f"- Criterion scores identical on re-scoring: **{summary['criterion_exact_agreement']:.0%}**.",
          f"- Same number of inconsistencies found: **{summary['inconsistency_count_agreement']:.0%}** of sections.\n",
          "| Company | Pillar | Original | Re-score | Diff |", "|---|---|---|---|---|"]
    md += [f"| {r['company']} | {r['pillar']} | {r['original']:.2f} | {r['rescore']:.2f} | {r['diff']:+.2f} |" for r in rows]
    with open("results/assessor_noise.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print("\n".join(md[:6]))


if __name__ == "__main__":
    main()
