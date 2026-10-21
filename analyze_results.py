"""Builds summary tables, gap analysis and charts from one run's loop logs.

Usage: python analyze_results.py [--run v1|v2] [Company ...]   (default run: v2)
Reads results/<run>/loop_logs, writes everything to results/<run>/.
"""
import os
import sys
import csv
import json
import glob
import math
from collections import Counter, defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import pandas as pd

import gap_analysis as ga

PILLARS = ["Environmental", "Social", "Governance"]
CRITERIA = ["Coverage", "Specificity", "Quantifiability", "Forward-Looking", "Transparency", "Compliance Alignment"]
THRESHOLD = 4.0
OUT_DIR = LOG_DIR = FIG_DIR = GAP_DIR = None


def set_run(run):
    global OUT_DIR, LOG_DIR, FIG_DIR, GAP_DIR
    OUT_DIR = os.path.join("results", run)
    LOG_DIR = os.path.join(OUT_DIR, "loop_logs")
    FIG_DIR = os.path.join(OUT_DIR, "figures")
    GAP_DIR = os.path.join(OUT_DIR, "gap_analysis")


set_run("v2")
MAPPING_FILE = "docs/industry_mapping.csv"

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
MARKERS = ["o", "s", "^", "D", "v", "P", "X", "*"]
TEXT, TEXT2, GRID, NEUTRAL = "#0b0b0b", "#52514e", "#e6e5e1", "#a8a7a1"
BLUE_RAMP = ["#ffffff", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

plt.rcParams.update({
    "font.size": 10, "text.color": TEXT, "axes.labelcolor": TEXT2, "axes.edgecolor": NEUTRAL,
    "xtick.color": TEXT2, "ytick.color": TEXT2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "axes.titlesize": 11, "axes.titleweight": "semibold", "axes.titlelocation": "left",
    "legend.frameon": False, "lines.linewidth": 2, "lines.markersize": 6,
    "savefig.dpi": 200, "savefig.bbox": "tight", "figure.facecolor": "white",
})


# ---------- loading ----------

def load_industries():
    """company -> broad industry (the part before '/' in docs/industry_mapping.csv)."""
    out = {}
    if os.path.exists(MAPPING_FILE):
        with open(MAPPING_FILE, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                out[row["company"].strip()] = row["industry"].split("/")[0].strip()
    return out


def load_logs(companies=None):
    """Load finished loop logs, in the order the companies were given."""
    logs = {}
    for path in glob.glob(os.path.join(LOG_DIR, "*_log.json")):
        with open(path, encoding="utf-8") as f:
            log = json.load(f)
        if not log.get("finished"):
            print(f"  Skipping {os.path.basename(path)}: run not finished")
            continue
        if companies and log["company"] not in companies:
            continue
        logs[log["company"]] = log
    order = [c for c in (companies or sorted(logs)) if c in logs]
    return [logs[c] for c in order]


def collect_gaps(round_record):
    """All gaps the assessor listed in one round: section-level + criterion-level, de-duplicated."""
    gaps = []
    for p in PILLARS:
        sec = round_record["sections"][p]
        items = list(sec.get("missing_elements", []))
        for c in sec.get("full_assessment", {}).get("criterion_scores", []):
            items += c.get("missing_elements", [])
        seen = set()
        for text in items:
            key = text.strip().lower()
            if key and key not in seen:
                seen.add(key)
                gaps.append({"pillar": p, "text": text.strip(), "topics": ga.classify(text)})
    return gaps


def top_gaps(round_record, n=3):
    """Top n gaps: the first-listed gap of each section, weakest section first."""
    secs = sorted(PILLARS, key=lambda p: round_record["sections"][p]["overall_score"])
    lists = [list(round_record["sections"][p].get("missing_elements", [])) for p in secs]
    out, i = [], 0
    while len(out) < n and any(i < len(l) for l in lists):
        for p, l in zip(secs, lists):
            if i < len(l) and len(out) < n:
                out.append(f"{p}: {l[i]}")
        i += 1
    return out


def last_attempt_words(rounds, pillar):
    """Words in the most recent attempt at a section (v2 logs keep attempts separately)."""
    for r in reversed(rounds):
        att = r["sections"][pillar].get("attempt")
        if att:
            return att["words"]
    return len(rounds[-1]["sections"][pillar]["draft"].split())


def build_records(logs, industries):
    records = []
    for log in logs:
        rounds = log["rounds"]
        r0, rf = rounds[0], rounds[-1]
        company = log["company"]
        final_text = "\n".join(rf["sections"][p]["draft"] for p in PILLARS)
        initial_gaps = collect_gaps(r0)
        gap_topics = {t for g in initial_gaps for t in g["topics"]}
        sasb_industry, sasb_rows = ga.sasb_crosscheck(company, gap_topics, final_text)
        records.append({
            "company": company,
            "industry": industries.get(company, "Unknown"),
            "sasb_industry": sasb_industry or "n/a",
            "rounds": len(rounds),
            "converged": bool(log.get("converged")),
            "progression": [r["overall_score"] for r in rounds],
            "section_progression": {p: [r["sections"][p]["overall_score"] for r in rounds] for p in PILLARS},
            "initial": r0["overall_score"], "final": rf["overall_score"],
            "best_sec": {p: max(r["sections"][p]["overall_score"] for r in rounds) for p in PILLARS},
            "words_initial": np.mean([len(r0["sections"][p]["draft"].split()) for p in PILLARS]),
            "words_final": np.mean([len(rf["sections"][p]["draft"].split()) for p in PILLARS]),
            "words_last_attempt": np.mean([last_attempt_words(rounds, p) for p in PILLARS]),
            "last_attempt": rf.get("attempt_overall_score", rf["overall_score"]),
            "keeps_best": bool(log.get("config", {}).get("keeps_best_version")),
            "pass_rule": (f"score ≥ {log.get('config', {}).get('threshold', THRESHOLD)} and ≤ "
                          f"{log['config']['max_inconsistencies']} inconsistency"
                          if "max_inconsistencies" in log.get("config", {})
                          else f"score ≥ {THRESHOLD} and no inconsistencies"),
            "initial_sec": {p: r0["sections"][p]["overall_score"] for p in PILLARS},
            "final_sec": {p: rf["sections"][p]["overall_score"] for p in PILLARS},
            "initial_crit": {p: r0["sections"][p]["criterion_scores"] for p in PILLARS},
            "final_crit": {p: rf["sections"][p]["criterion_scores"] for p in PILLARS},
            "incons_initial": sum(len(r0["sections"][p].get("inconsistencies", [])) for p in PILLARS),
            "incons_final": sum(len(rf["sections"][p].get("inconsistencies", [])) for p in PILLARS),
            "initial_gaps": initial_gaps,
            "final_gaps": collect_gaps(rf),
            "top3": top_gaps(rf),
            "sasb_rows": sasb_rows,
        })
    for r in records:
        r["best"] = round(float(np.mean([r["best_sec"][p] for p in PILLARS])), 2)
    return records


# ---------- tables ----------

def write_tables(records):
    os.makedirs(GAP_DIR, exist_ok=True)
    rows = []
    for r in records:
        row = {"company": r["company"], "industry": r["industry"], "sasb_industry": r["sasb_industry"],
               "initial_overall": r["initial"], "final_overall": r["final"],
               "change": round(r["final"] - r["initial"], 2),
               "best_version_overall": r["best"], "best_version_change": round(r["best"] - r["initial"], 2),
               "rounds": r["rounds"],
               "converged": r["converged"]}
        for p in PILLARS:
            row[f"initial_{p[0]}"] = r["initial_sec"][p]
            row[f"final_{p[0]}"] = r["final_sec"][p]
        row.update({"inconsistencies_initial": r["incons_initial"], "inconsistencies_final": r["incons_final"],
                    "gaps_initial": len(r["initial_gaps"]), "gaps_final": len(r["final_gaps"]),
                    "words_per_section_initial": round(r["words_initial"]), "words_per_section_final": round(r["words_final"])})
        for i in range(3):
            row[f"top_gap_{i + 1}"] = r["top3"][i] if i < len(r["top3"]) else ""
        rows.append(row)
    summary = pd.DataFrame(rows)
    summary.to_csv(os.path.join(OUT_DIR, "case_study_summary.csv"), index=False, encoding="utf-8-sig")

    md = ["# Case study summary\n",
          "| Company | Industry | Initial | Final | Change | Best version | Rounds | Converged | E (init→final) | S (init→final) | G (init→final) |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in records:
        sec = " | ".join(f"{r['initial_sec'][p]:.2f} → {r['final_sec'][p]:.2f}" for p in PILLARS)
        md.append(f"| {r['company']} | {r['industry']} | {r['initial']:.2f} | {r['final']:.2f} | "
                  f"{r['final'] - r['initial']:+.2f} | {r['best']:.2f} | {r['rounds']} | {'yes' if r['converged'] else 'no'} | {sec} |")
    md.append("\n## Top 3 disclosure gaps per company (final round)\n")
    for r in records:
        md.append(f"**{r['company']}**\n")
        md += [f"{i}. {g}" for i, g in enumerate(r["top3"], 1)]
        md.append("")
    with open(os.path.join(OUT_DIR, "case_study_summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    # Gap analysis outputs
    counts = []
    for topic in ga.ALL_LABELS:
        row = {"topic": topic, "pillar": ga.TOPIC_PILLAR.get(topic, "-"), "reference": ga.TOPIC_REF.get(topic, "-")}
        for r in records:
            row[r["company"]] = sum(topic in g["topics"] for g in r["initial_gaps"])
        row["total"] = sum(row[r["company"]] for r in records)
        counts.append(row)
    gap_counts = pd.DataFrame(counts)
    gap_counts.to_csv(os.path.join(GAP_DIR, "gap_topic_counts.csv"), index=False, encoding="utf-8-sig")

    sasb = []
    lines = ["# Gap analysis\n",
             "Gaps = items the Assessment Agent listed as missing in round 1, classified into GRI/TCFD topics "
             "(see gap_analysis.py for the keyword rules). SASB status: *addressed* = discussed in the final report, "
             "*flagged as gap* = the agent noticed it was missing, *blind spot* = neither.\n"]
    for r in records:
        with open(os.path.join(GAP_DIR, f"{r['company'].replace(' ', '_')}_gaps.json"), "w", encoding="utf-8") as f:
            json.dump({"company": r["company"], "industry": r["industry"], "sasb_industry": r["sasb_industry"],
                       "top3_final": r["top3"], "initial_gaps": r["initial_gaps"],
                       "remaining_gaps_final": r["final_gaps"], "sasb_crosscheck": r["sasb_rows"]},
                      f, indent=2, ensure_ascii=False)
        lines.append(f"## {r['company']} ({r['industry']})\n")
        by_pillar = defaultdict(list)
        for g in r["initial_gaps"]:
            by_pillar[g["pillar"]].append(g)
        for p in PILLARS:
            lines.append(f"**{p}** ({len(by_pillar[p])} gaps)\n")
            lines += [f"- {g['text']}  *[{', '.join(g['topics'])}]*" for g in by_pillar[p]]
            lines.append("")
        if r["sasb_rows"]:
            lines.append(f"**SASB cross-check: {r['sasb_industry']}**\n")
            lines.append("| SASB material topic | Status |\n|---|---|")
            lines += [f"| {s['sasb_topic']} | {s['status']} |" for s in r["sasb_rows"]]
            lines.append("")
            for s in r["sasb_rows"]:
                sasb.append({"company": r["company"], "sasb_industry": r["sasb_industry"], **s})
    with open(os.path.join(GAP_DIR, "gap_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    sasb_df = pd.DataFrame(sasb)
    if not sasb_df.empty:
        sasb_df.to_csv(os.path.join(GAP_DIR, "sasb_crosscheck.csv"), index=False, encoding="utf-8-sig")
    return summary, gap_counts, sasb_df


# ---------- charts ----------

def _colour(i):
    return SERIES[i % len(SERIES)], MARKERS[i % len(MARKERS)]


def fig_convergence(records):
    fig, ax = plt.subplots(figsize=(7.5, 4.3))
    max_r = max(r["rounds"] for r in records)
    for i, r in enumerate(records):
        col, mk = _colour(i)
        xs = list(range(1, r["rounds"] + 1))
        ax.plot(xs, r["progression"], color=col, marker=mk, label=f"{r['company']} ({r['industry']})")
        if len(records) <= 4:
            ax.annotate(r["company"], (xs[-1], r["progression"][-1]), xytext=(6, 0),
                        textcoords="offset points", va="center", color=TEXT2, fontsize=9)
    ax.axhline(THRESHOLD, ls="--", lw=1, color=NEUTRAL)
    ax.text(0.85, THRESHOLD + 0.05, f"pass threshold {THRESHOLD}", color=TEXT2, fontsize=8, va="bottom")
    ax.set_xticks(range(1, max_r + 1))
    ax.set_xlim(0.8, max_r + (0.6 if len(records) <= 4 else 0.2))
    ax.set_ylim(1, 5)
    ax.set_xlabel("Iteration (assessment round)")
    ax.set_ylabel("Overall report score (1–5)")
    ax.set_title("Convergence: overall report score by iteration")
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=9)
    path = os.path.join(FIG_DIR, "fig1_convergence.png")
    fig.savefig(path)
    plt.close(fig)
    return path


def fig_section_progression(records):
    n = len(records)
    cols = min(n, 3)
    rows = math.ceil(n / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(4.2 * cols, 3.2 * rows), sharey=True, squeeze=False)
    max_r = max(r["rounds"] for r in records)
    for idx, r in enumerate(records):
        ax = axes[idx // cols][idx % cols]
        for j, p in enumerate(PILLARS):
            ys = r["section_progression"][p]
            ax.plot(range(1, len(ys) + 1), ys, color=SERIES[j], marker=MARKERS[j], label=p)
        ax.axhline(THRESHOLD, ls="--", lw=1, color=NEUTRAL)
        ax.set_title(f"{r['company']}", fontsize=10)
        ax.set_xticks(range(1, max_r + 1))
        ax.set_xlim(0.8, max_r + 0.2)
        ax.set_ylim(1, 5)
        if idx % cols == 0:
            ax.set_ylabel("Section score (1–5)")
        if idx // cols == rows - 1:
            ax.set_xlabel("Iteration")
    for idx in range(n, rows * cols):
        axes[idx // cols][idx % cols].axis("off")
    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.02))
    fig.suptitle("Section score progression per company", x=0.01, ha="left", y=1.08,
                 fontsize=11, fontweight="semibold")
    fig.tight_layout()
    path = os.path.join(FIG_DIR, "fig2_section_progression.png")
    fig.savefig(path)
    plt.close(fig)
    return path


def fig_improvement(records):
    fig, ax = plt.subplots(figsize=(max(6, 1.5 * len(records) + 2), 4.2))
    x = np.arange(len(records))
    w = 0.36
    last = [r["last_attempt"] - r["initial"] for r in records]
    best = [r["best"] - r["initial"] for r in records]
    ax.bar(x - w / 2 - 0.01, last, w, color=SERIES[0], edgecolor="white", linewidth=2, label="Last attempt per section")
    ax.bar(x + w / 2 + 0.01, best, w, color=SERIES[1], edgecolor="white", linewidth=2, label="Best version per section")
    ax.axhline(0, color=NEUTRAL, lw=1)
    for xi, d in zip(x - w / 2, last):
        ax.annotate(f"{d:+.2f}", (xi, d), xytext=(0, 3 if d >= 0 else -3), textcoords="offset points",
                    ha="center", va="bottom" if d >= 0 else "top", fontsize=8, color=TEXT2)
    for xi, d in zip(x + w / 2, best):
        ax.annotate(f"{d:+.2f}", (xi, d), xytext=(0, 3 if d >= 0 else -3), textcoords="offset points",
                    ha="center", va="bottom" if d >= 0 else "top", fontsize=8, color=TEXT2)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{r['company']}\n{r['initial']:.2f} → {r['final']:.2f}" for r in records], fontsize=8.5)
    lo, hi = min(0, *last, *best), max(0, *last, *best)
    pad = max(0.1, (hi - lo) * 0.15)
    ax.set_ylim(lo - pad, hi + pad)
    ax.set_ylabel("Change vs iteration 1 (overall score)")
    ax.set_title("Score change from iteration 1: last version vs best version")
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1))
    ax.grid(axis="x", visible=False)
    path = os.path.join(FIG_DIR, "fig3_improvement.png")
    fig.savefig(path)
    plt.close(fig)
    return path


def industry_pillar_means(records, key):
    by_ind = defaultdict(list)
    for r in records:
        by_ind[r["industry"]].append(r)
    return {ind: [np.mean([r[key][p] for r in rs]) for p in PILLARS] for ind, rs in by_ind.items()}, by_ind


def fig_radar(records):
    init, by_ind = industry_pillar_means(records, "initial_sec")
    final, _ = industry_pillar_means(records, "final_sec")
    industries = list(init)
    angles = np.linspace(0, 2 * np.pi, len(PILLARS), endpoint=False).tolist()
    angles += angles[:1]
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 5.4), subplot_kw={"polar": True})
    fig.subplots_adjust(wspace=0.55, top=0.80, bottom=0.14)
    for ax, data, title in [(axes[0], init, "Initial (iteration 1)"), (axes[1], final, "Final (after loop)")]:
        for k, ind in enumerate(industries):
            col, mk = _colour(k)
            vals = data[ind] + data[ind][:1]
            n = len(by_ind[ind])
            ax.plot(angles, vals, color=col, marker=mk, label=f"{ind} (n={n})")
            ax.fill(angles, vals, color=col, alpha=0.06)
        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)
        ax.set_rlabel_position(180)
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(PILLARS, color=TEXT)
        ax.tick_params(axis="x", pad=10)
        ax.set_ylim(0, 5)
        ax.set_yticks([1, 2, 3, 4, 5])
        ax.set_yticklabels(["1", "2", "3", "4", "5"], fontsize=7, color=TEXT2)
        ax.set_title(title, loc="center", pad=30, fontsize=10)
        ax.grid(color=GRID)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=min(4, len(industries)), bbox_to_anchor=(0.5, 0.0))
    fig.suptitle("Average pillar scores by industry", x=0.01, y=0.99, ha="left", fontsize=11, fontweight="semibold")
    path = os.path.join(FIG_DIR, "fig4_radar_industry.png")
    fig.savefig(path)
    plt.close(fig)
    return path


def fig_gap_heatmap(records):
    by_ind = defaultdict(list)
    for r in records:
        by_ind[r["industry"]].append(r)
    industries = list(by_ind)
    topics = ga.ALL_LABELS
    mat = np.array([[np.mean([sum(t in g["topics"] for g in r["initial_gaps"]) for r in by_ind[ind]])
                     for ind in industries] for t in topics])
    cmap = LinearSegmentedColormap.from_list("blue_seq", BLUE_RAMP)
    fig, ax = plt.subplots(figsize=(2.2 + 1.5 * len(industries), 8.5))
    im = ax.imshow(mat, cmap=cmap, aspect="auto", vmin=0, vmax=max(1, mat.max()))
    ax.set_xticks(range(len(industries)))
    ax.set_xticklabels([f"{ind}\n(n={len(by_ind[ind])})" for ind in industries], fontsize=8.5)
    ax.xaxis.tick_top()
    ax.set_yticks(range(len(topics)))
    ax.set_yticklabels([f"{ga.TOPIC_PILLAR[t][0]} · {t}" if t in ga.TOPIC_PILLAR else t for t in topics], fontsize=8.5)
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    for i in range(len(topics)):
        for j in range(len(industries)):
            v = mat[i, j]
            if v > 0:
                ax.text(j, i, f"{v:.1f}".rstrip("0").rstrip("."), ha="center", va="center", fontsize=8,
                        color="white" if v > 0.55 * mat.max() else TEXT)
    # separators between pillars
    pillars = [ga.TOPIC_PILLAR.get(t, "Other") for t in topics]
    for i in range(1, len(topics)):
        if pillars[i] != pillars[i - 1]:
            ax.axhline(i - 0.5, color="white", lw=3)
    cbar = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
    cbar.set_label("Gaps flagged per company (round 1)", color=TEXT2)
    cbar.outline.set_visible(False)
    ax.set_title("Disclosure gaps by industry × ESG topic", pad=40)
    path = os.path.join(FIG_DIR, "fig5_gap_heatmap.png")
    fig.savefig(path)
    plt.close(fig)
    return path


def criterion_means(records, key):
    return [np.mean([r[key][p][c] for r in records for p in PILLARS]) for c in CRITERIA]


def fig_criteria(records):
    init, final = criterion_means(records, "initial_crit"), criterion_means(records, "final_crit")
    x = np.arange(len(CRITERIA))
    w = 0.36
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    b1 = ax.bar(x - w / 2 - 0.01, init, w, color=NEUTRAL, label="Initial (iteration 1)", edgecolor="white", linewidth=2)
    b2 = ax.bar(x + w / 2 + 0.01, final, w, color=SERIES[0], label="Final", edgecolor="white", linewidth=2)
    for bars in (b1, b2):
        for b in bars:
            ax.annotate(f"{b.get_height():.2f}", (b.get_x() + b.get_width() / 2, b.get_height()),
                        xytext=(0, 3), textcoords="offset points", ha="center", fontsize=8, color=TEXT2)
    ax.set_xticks(x)
    ax.set_xticklabels([c.replace(" ", "\n") for c in CRITERIA], fontsize=9)
    ax.set_ylim(0, 5.4)
    ax.set_ylabel("Mean score (all companies & pillars)")
    ax.set_title("Initial vs final scores per rubric criterion")
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1))
    ax.grid(axis="x", visible=False)
    path = os.path.join(FIG_DIR, "fig6_criteria_initial_vs_final.png")
    fig.savefig(path)
    plt.close(fig)
    return path, init, final


# ---------- citable summary ----------

def write_summary(records, gap_counts, sasb_df, crit_init, crit_final, figures):
    n = len(records)
    inds = sorted({r["industry"] for r in records})
    init = np.array([r["initial"] for r in records])
    final = np.array([r["final"] for r in records])
    improved = sum(f > i for i, f in zip(init, final))
    converged = [r for r in records if r["converged"]]
    rounds = [r["rounds"] for r in records]

    ind_init = defaultdict(list)
    for r in records:
        ind_init[r["industry"]].append(r["initial"])
    ind_rank = sorted(((np.mean(v), k, len(v)) for k, v in ind_init.items()), reverse=True)

    pillar_gaps = {p: sum(1 for r in records for g in r["initial_gaps"] if g["pillar"] == p) for p in PILLARS}
    pillar_init = {p: np.mean([r["initial_sec"][p] for r in records]) for p in PILLARS}
    pillar_final = {p: np.mean([r["final_sec"][p] for r in records]) for p in PILLARS}
    sections_total = 3 * n
    sections_passed_final = sum(1 for r in records for p in PILLARS if r["final_sec"][p] >= THRESHOLD)

    top_topics = gap_counts[gap_counts["topic"].isin(ga.TOPIC_NAMES)].sort_values("total", ascending=False).head(5)
    all_gaps = sum(len(r["initial_gaps"]) for r in records)
    practice = sum(1 for r in records for g in r["initial_gaps"] if g["topics"] == [ga.REPORTING_PRACTICE])
    other = sum(1 for r in records for g in r["initial_gaps"] if g["topics"] == ["Other"])
    crit_change = sorted(zip(CRITERIA, crit_init, crit_final), key=lambda t: t[2] - t[1], reverse=True)

    keeps_best = any(r["keeps_best"] for r in records)
    L = [f"# Results summary ({os.path.basename(OUT_DIR)})\n",
         f"Companies analysed: **{n}** ({', '.join(r['company'] for r in records)}) across **{len(inds)} industries** "
         f"({', '.join(inds)}). Generator and assessor: Qwen (see loop logs for model names). "
         f"Pass rule: {records[0]['pass_rule']}; max 3 rounds. The loop returns the "
         f"{'best-scoring' if keeps_best else 'latest'} version of each section.\n",
         "## Headline numbers\n",
         f"- Mean overall score went from **{init.mean():.2f}** (iteration 1) to **{final.mean():.2f}** (final), "
         f"a change of **{final.mean() - init.mean():+.2f}** points; {improved}/{n} companies improved.",
         (f"- Without best-keeping (taking each section's last attempt) the mean would be "
          f"**{np.mean([r['last_attempt'] for r in records]):.2f}** "
          f"({np.mean([r['last_attempt'] for r in records]) - init.mean():+.2f})."
          if keeps_best else
          f"- If the loop kept the best-scoring version of each section instead of the last one, the mean would be "
          f"**{np.mean([r['best'] for r in records]):.2f}** ({np.mean([r['best'] for r in records]) - init.mean():+.2f}). "
          f"This is an upper bound: picking the maximum of noisy scores inflates it."),
         f"- Words per section: **{np.mean([r['words_initial'] for r in records]):.0f}** in iteration 1, "
         f"**{np.mean([r['words_last_attempt'] for r in records]):.0f}** in the last attempts, "
         f"**{np.mean([r['words_final'] for r in records]):.0f}** in the returned versions (instruction: 400–700).",
         f"- Largest gain: {records[int(np.argmax(final - init))]['company']} "
         f"({(final - init).max():+.2f}); smallest: {records[int(np.argmin(final - init))]['company']} "
         f"({(final - init).min():+.2f}).",
         f"- Convergence (every section passing): **{len(converged)}/{n}** companies"
         + (f" ({', '.join(r['company'] + ' in ' + str(r['rounds']) + ' rounds' for r in converged)})" if converged else "")
         + f". Mean rounds used: **{np.mean(rounds):.1f}** (distribution: "
         + ", ".join(f"{k} round{'s' if k > 1 else ''}: {v}" for k, v in sorted(Counter(rounds).items())) + ").",
         f"- Sections at or above {THRESHOLD} after the loop: **{sections_passed_final}/{sections_total}**.",
         f"- Internal inconsistencies flagged by the assessor: **{sum(r['incons_initial'] for r in records)}** "
         f"in iteration 1 → **{sum(r['incons_final'] for r in records)}** in the final round.\n",
         "## Cross-industry comparison\n",
         f"**Best / worst initial disclosure quality.** Best: **{ind_rank[0][1]}** ({ind_rank[0][0]:.2f}, n={ind_rank[0][2]}); "
         f"worst: **{ind_rank[-1][1]}** ({ind_rank[-1][0]:.2f}, n={ind_rank[-1][2]}). Full ranking: "
         + "; ".join(f"{k} {m:.2f} (n={c})" for m, k, c in ind_rank) + ".\n",
         f"**Pillar with the most gaps.** Gaps flagged in iteration 1: "
         + ", ".join(f"{p} {pillar_gaps[p]}" for p in PILLARS)
         + f" → most: **{max(pillar_gaps, key=pillar_gaps.get)}**. Mean initial pillar scores: "
         + ", ".join(f"{p} {pillar_init[p]:.2f}" for p in PILLARS)
         + f" (lowest: **{min(pillar_init, key=pillar_init.get)}**); final: "
         + ", ".join(f"{p} {pillar_final[p]:.2f}" for p in PILLARS) + ".\n",
         f"**Iterations to converge.** Mean {np.mean(rounds):.1f} rounds; "
         f"{len(converged)}/{n} companies converged within the 3-round limit.\n",
         f"**Gaps flagged in iteration 1:** {all_gaps} in total. {practice} ({practice / all_gaps:.0%}) are about "
         f"reporting practice (missing baselines, targets, definitions or GRI references) rather than a specific topic; "
         f"{other} unclassified. Most common topics: "
         + "; ".join(f"{t} ({int(c)})" for t, c in zip(top_topics["topic"], top_topics["total"])) + ".\n",
         "**Rubric criteria (mean, iteration 1 → final).** Most improved: "
         + ", ".join(f"{c} {i:.2f}→{f:.2f}" for c, i, f in crit_change[:2])
         + "; least improved: "
         + ", ".join(f"{c} {i:.2f}→{f:.2f}" for c, i, f in crit_change[-2:])
         + f". Lowest final criterion: {min(zip(crit_final, CRITERIA))[1]} ({min(crit_final):.2f}).\n"]

    if not sasb_df.empty:
        st = sasb_df["status"].value_counts()
        tot = len(sasb_df)
        L += ["## SASB cross-check\n",
              f"Of {tot} SASB material topics across the companies: "
              + ", ".join(f"{k} {v} ({v / tot:.0%})" for k, v in st.items()) + ".",
              "Blind spots per company: " + "; ".join(
                  f"{c}: {', '.join(g['sasb_topic'] for _, g in grp[grp['status'] == 'blind spot'].iterrows()) or 'none'}"
                  for c, grp in sasb_df.groupby("company", sort=False)) + ".\n"]

    L += ["## Per-company results\n",
          "| Company | Industry | Initial | Final | Change | Rounds | Converged | Inconsistencies (init→final) |",
          "|---|---|---|---|---|---|---|---|"]
    L += [f"| {r['company']} | {r['industry']} | {r['initial']:.2f} | {r['final']:.2f} | {r['final'] - r['initial']:+.2f} | "
          f"{r['rounds']} | {'yes' if r['converged'] else 'no'} | {r['incons_initial']}→{r['incons_final']} |" for r in records]
    L += ["\n## Figures\n"] + [f"- `{p}`" for p in figures]
    L += ["\n## Caveats\n",
          "- Scores come from a single LLM judge (Qwen) that also shares a model family with the generator; "
          "human calibration on one company (Apple) showed a mean absolute difference of about 0.4–0.8 points.",
          *(["- Keeping the best of several noisy scores biases the returned score upwards (selection effect); "
             "compare gains with the assessor's re-scoring variation (assessor_noise.py)."] if keeps_best else []),
          "- Improvement is measured by the same assessor that gives the feedback, so part of the gain may be the "
          "generator learning what the assessor rewards rather than better disclosure.",
          "- Gap topics are assigned by keyword rules (gap_analysis.py); some gaps fit several topics or none ('Other').",
          "- The SASB topic lists are a simplified mapping and should be checked on materiality.sasb.org.",
          f"- Small sample: {n} companies, mostly one per industry, so industry comparisons are indicative only.",
          "- 'Gaps' mean information not found in the retrieved chunks of one report, not necessarily that the "
          "company never discloses it."]
    with open(os.path.join(OUT_DIR, "analysis_summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))


def main(companies=None, run="v2"):
    set_run(run)
    os.makedirs(FIG_DIR, exist_ok=True)
    logs = load_logs(companies)
    if not logs:
        raise SystemExit(f"No finished logs found in {LOG_DIR}.")
    records = build_records(logs, load_industries())
    summary, gap_counts, sasb_df = write_tables(records)
    figures = [fig_convergence(records), fig_section_progression(records), fig_improvement(records),
               fig_radar(records), fig_gap_heatmap(records)]
    p6, crit_init, crit_final = fig_criteria(records)
    figures.append(p6)
    write_summary(records, gap_counts, sasb_df, crit_init, crit_final, figures)
    print(f"\nAnalysed {len(records)} companies: {', '.join(r['company'] for r in records)}")
    print(f"  {OUT_DIR}/analysis_summary.md   <- key numbers to cite")
    print(f"  {OUT_DIR}/case_study_summary.csv / .md")
    print(f"  {GAP_DIR}/ (gap_report.md, gap_topic_counts.csv, sasb_crosscheck.csv, <Company>_gaps.json)")
    for p in figures:
        print(f"  {p}")
    return records


if __name__ == "__main__":
    args = sys.argv[1:]
    run = "v2"
    if "--run" in args:
        i = args.index("--run")
        run = args[i + 1]
        args = args[:i] + args[i + 2:]
    main(args or None, run)
