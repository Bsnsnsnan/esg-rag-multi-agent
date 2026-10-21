"""
Compares two loop runs (default v1 vs v2) company by company.

Usage: python compare_runs.py [v1 v2]
Out:   results/comparison/comparison.md, results/comparison/fig7_v1_vs_v2.png
Needs analyze_results.py to have been run for both runs.
"""
import os
import sys
import json

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from analyze_results import SERIES, NEUTRAL, TEXT2

OUT = "results/comparison"


def load(run):
    path = os.path.join("results", run, "case_study_summary.csv")
    if not os.path.exists(path):
        raise SystemExit(f"{path} not found. Run: python analyze_results.py --run {run}")
    return pd.read_csv(path, encoding="utf-8-sig").set_index("company")


def main():
    a, b = (sys.argv[1:3] if len(sys.argv) >= 3 else ["v1", "v2"])
    A, B = load(a), load(b)
    companies = [c for c in A.index if c in B.index]
    os.makedirs(OUT, exist_ok=True)

    # chart: change vs iteration 1, per company + mean
    labels = companies + ["Mean"]
    ca = [A.loc[c, "change"] for c in companies]
    cb = [B.loc[c, "change"] for c in companies]
    ca.append(float(np.mean(ca)))
    cb.append(float(np.mean(cb)))
    x = np.arange(len(labels))
    w = 0.36
    fig, ax = plt.subplots(figsize=(max(6.5, 1.4 * len(labels) + 2), 4.2))
    ax.bar(x - w / 2 - 0.01, ca, w, color=NEUTRAL, edgecolor="white", linewidth=2, label=f"{a}")
    ax.bar(x + w / 2 + 0.01, cb, w, color=SERIES[0], edgecolor="white", linewidth=2, label=f"{b}")
    for xs, vals in ((x - w / 2, ca), (x + w / 2, cb)):
        for xi, d in zip(xs, vals):
            ax.annotate(f"{d:+.2f}", (xi, d), xytext=(0, 3 if d >= 0 else -3), textcoords="offset points",
                        ha="center", va="bottom" if d >= 0 else "top", fontsize=8, color=TEXT2)
    ax.axhline(0, color=NEUTRAL, lw=1)
    ax.axvline(len(companies) - 0.5, color="#e6e5e1", lw=1)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    lo, hi = min(0, *ca, *cb), max(0, *ca, *cb)
    pad = max(0.1, (hi - lo) * 0.15)
    ax.set_ylim(lo - pad, hi + pad)
    ax.set_ylabel("Change in overall score vs iteration 1")
    ax.set_title(f"Feedback loop {a} vs {b}: score change from iteration 1 to final")
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1))
    ax.grid(axis="x", visible=False)
    fig_path = os.path.join(OUT, f"fig7_{a}_vs_{b}.png")
    fig.savefig(fig_path)
    plt.close(fig)

    def mean(df, col):
        return df.loc[companies, col].mean()

    def count(df, col):
        return int(df.loc[companies, col].astype(str).str.lower().eq("true").sum())

    metrics = [
        ("Mean initial score", f"{mean(A, 'initial_overall'):.2f}", f"{mean(B, 'initial_overall'):.2f}"),
        ("Mean final score", f"{mean(A, 'final_overall'):.2f}", f"{mean(B, 'final_overall'):.2f}"),
        ("Mean change", f"{mean(A, 'change'):+.2f}", f"{mean(B, 'change'):+.2f}"),
        ("Companies improved", f"{int((A.loc[companies, 'change'] > 0).sum())}/{len(companies)}",
         f"{int((B.loc[companies, 'change'] > 0).sum())}/{len(companies)}"),
        ("Companies converged", f"{count(A, 'converged')}/{len(companies)}", f"{count(B, 'converged')}/{len(companies)}"),
        ("Mean rounds", f"{mean(A, 'rounds'):.1f}", f"{mean(B, 'rounds'):.1f}"),
        ("Inconsistencies (final, total)", f"{int(A.loc[companies, 'inconsistencies_final'].sum())}",
         f"{int(B.loc[companies, 'inconsistencies_final'].sum())}"),
        ("Words per section (final)", f"{mean(A, 'words_per_section_final'):.0f}", f"{mean(B, 'words_per_section_final'):.0f}"),
    ]
    md = [f"# Loop comparison: {a} vs {b}\n", f"| Metric | {a} | {b} |", "|---|---|---|"]
    md += [f"| {m} | {x1} | {x2} |" for m, x1, x2 in metrics]
    md += ["", f"| Company | {a} initial → final | {a} change | {b} initial → final | {b} change |", "|---|---|---|---|---|"]
    md += [f"| {c} | {A.loc[c, 'initial_overall']:.2f} → {A.loc[c, 'final_overall']:.2f} | {A.loc[c, 'change']:+.2f} | "
           f"{B.loc[c, 'initial_overall']:.2f} → {B.loc[c, 'final_overall']:.2f} | {B.loc[c, 'change']:+.2f} |"
           for c in companies]

    noise_path = "results/assessor_noise.json"
    if os.path.exists(noise_path):
        n = json.load(open(noise_path))
        md += ["", "## Is the difference bigger than the assessor's own variation?\n",
               f"Re-scoring the same text changes a report score by **{n['report_mean_abs_diff']}** on average "
               f"(section: {n['section_mean_abs_diff']}, {n['n_sections']} sections re-scored). "
               f"Changes smaller than this are within measurement noise."]
    md += ["", f"![comparison]({os.path.basename(fig_path)})"]
    with open(os.path.join(OUT, "comparison.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print("\n".join(md[:12]))
    print(f"\nSaved {OUT}/comparison.md and {fig_path}")


if __name__ == "__main__":
    main()
