"""
Generate -> Assess -> Revise loop (LangGraph), v2.

    GENERATE ──► ASSESS ──► all sections pass or max rounds? ──yes──► END
                   ▲                 │ no
                   └──── REVISE ◄────┘

v2 changes (v1 is kept in feedback_loop_v1.py):
- Keeps the best-scoring version of each section; a revision only replaces it if it scores higher.
- Revisions edit the best version (not the latest) and must stay within the word limit;
  an over-long revision gets one extra "shorten" pass.
- Shorter feedback: inconsistencies + the two weakest criteria + top priorities.
- Pass rule: score >= 4.0 and at most 1 inconsistency.

Usage: python feedback_loop.py "Company" ["Company 2" ...]
Out:   results/v2/loop_logs/<Company>_log.json, results/v2/final/<Company>_final_report.md
"""
import os
import sys
import json
import time
from datetime import datetime, date
from typing import TypedDict

from langgraph.graph import StateGraph, END

from generative_agent import generate_section, PILLARS, MODEL as GEN_MODEL
from assessment_agent import assess_section, MODEL as ASSESS_MODEL

VERSION = "v2"
MAX_ITERATIONS = 3
THRESHOLD = 4.0
MAX_INCONSISTENCIES = 1
EXTRA_QUERIES_FROM_FEEDBACK = 2
WORD_LIMIT = 700
SHORTEN_ABOVE = 800

RUN_DIR = os.path.join("results", VERSION)
LOG_DIR = os.path.join(RUN_DIR, "loop_logs")
FINAL_DIR = os.path.join(RUN_DIR, "final")


class LoopState(TypedDict):
    company: str
    iteration: int
    candidates: dict    # pillar -> {"text", "sources"} written this round
    to_assess: list     # pillars with a new candidate this round
    best: dict          # pillar -> {"text", "sources", "assessment", "iteration"}
    latest_attempt: dict  # pillar -> score of the most recent attempt
    passed: dict
    history: list
    converged: bool


def with_retry(fn, *args, retries=5, **kwargs):
    for attempt in range(retries):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if "429" not in str(e) or attempt == retries - 1:
                raise
            wait = 15 * (attempt + 1)
            print(f"    Rate limited, waiting {wait}s...")
            time.sleep(wait)


def word_count(text):
    return len(text.split())


def section_passes(assessment):
    return (assessment["overall_score"] >= THRESHOLD
            and len(assessment.get("inconsistencies", [])) <= MAX_INCONSISTENCIES)


def is_better(new, old):
    """Higher score wins; on a tie, fewer inconsistencies wins."""
    if new["overall_score"] != old["overall_score"]:
        return new["overall_score"] > old["overall_score"]
    return len(new.get("inconsistencies", [])) < len(old.get("inconsistencies", []))


def format_feedback(assessment, draft_words):
    lines = [f"Current score: {assessment['overall_score']} / 5 (target: {THRESHOLD})."]
    if assessment.get("inconsistencies"):
        lines.append("\nInconsistencies to fix (check each figure against the context; correct it or remove it):")
        lines += [f"- {x}" for x in assessment["inconsistencies"]]

    weakest = sorted(assessment["criterion_scores"], key=lambda c: c["score"])[:2]
    lines.append("\nWeakest criteria:")
    for c in weakest:
        lines.append(f"- {c['criterion']} ({c['score']}/5): {c['justification']}")
        lines += [f"    * {s}" for s in c["improvement_suggestions"][:2]]

    if assessment.get("improvement_suggestions"):
        lines.append("\nTop priorities:")
        lines += [f"- {s}" for s in assessment["improvement_suggestions"][:3]]

    lines.append(
        f"\nHow to revise:\n"
        f"- EDIT the previous draft; do not rewrite it from scratch. Keep content and citations that are correct.\n"
        f"- The previous draft is {draft_words} words. The revised section must be at most {WORD_LIMIT} words: "
        f"if you add something, cut something less important.\n"
        f"- Only use information from the Provided Context. If a suggestion needs data that is not there, do not "
        f"invent it; mention it briefly under '### Not covered in source material'."
    )
    return "\n".join(lines)


def save_log(state, finished=False):
    os.makedirs(LOG_DIR, exist_ok=True)
    rounds = state["history"]
    log = {
        "company": state["company"],
        "config": {
            "version": VERSION,
            "generator_model": GEN_MODEL,
            "assessor_model": ASSESS_MODEL,
            "max_iterations": MAX_ITERATIONS,
            "threshold": THRESHOLD,
            "max_inconsistencies": MAX_INCONSISTENCIES,
            "extra_queries_from_feedback": EXTRA_QUERIES_FROM_FEEDBACK,
            "word_limit": WORD_LIMIT,
            "keeps_best_version": True,
        },
        "finished": finished,
        "converged": state.get("converged", False),
        "num_rounds": len(rounds),
        "score_progression": [r["overall_score"] for r in rounds],
        "attempt_score_progression": [r["attempt_overall_score"] for r in rounds],
        "section_score_progression": {p: [r["sections"][p]["overall_score"] for r in rounds] for p in PILLARS},
        "rounds": rounds,
    }
    path = os.path.join(LOG_DIR, f"{state['company'].replace(' ', '_')}_log.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
    return path


def generate_node(state: LoopState):
    print(f"\n[Round 1] GENERATE: {state['company']}")
    candidates = {}
    for pillar in PILLARS:
        print(f"  Writing {pillar}...")
        text, src = with_retry(generate_section, state["company"], pillar)
        if not src:
            raise SystemExit(f"No chunks found for '{state['company']}'. Check the exact company name.")
        candidates[pillar] = {"text": text, "sources": src}
    return {"iteration": 1, "candidates": candidates, "to_assess": list(PILLARS),
            "best": {}, "latest_attempt": {}, "passed": {p: False for p in PILLARS}}


def assess_node(state: LoopState):
    it = state["iteration"]
    print(f"[Round {it}] ASSESS: {', '.join(state['to_assess'])}")
    best, latest, passed = dict(state["best"]), dict(state["latest_attempt"]), dict(state["passed"])
    attempts = {}

    for pillar in state["to_assess"]:
        cand = state["candidates"][pillar]
        a = with_retry(assess_section, state["company"], pillar, cand["text"])
        latest[pillar] = a["overall_score"]
        kept = pillar not in best or is_better(a, best[pillar]["assessment"])
        if kept:
            best[pillar] = {"text": cand["text"], "sources": cand["sources"], "assessment": a, "iteration": it}
        passed[pillar] = section_passes(best[pillar]["assessment"])
        attempts[pillar] = {"score": a["overall_score"], "kept": kept, "words": word_count(cand["text"]),
                            "inconsistencies": a.get("inconsistencies", []),
                            "draft": cand["text"], "assessment": a}
        print(f"  {pillar:<14} attempt {a['overall_score']:.2f} ({word_count(cand['text'])} words, "
              f"{len(a.get('inconsistencies', []))} incons.) -> {'kept' if kept else 'discarded'}; "
              f"best {best[pillar]['assessment']['overall_score']:.2f} {'PASS' if passed[pillar] else ''}")

    sections = {}
    for p in PILLARS:
        b = best[p]
        sections[p] = {
            "revised_this_round": p in attempts,
            "attempt": attempts.get(p),
            "best_from_iteration": b["iteration"],
            "passed": passed[p],
            "overall_score": b["assessment"]["overall_score"],
            "criterion_scores": {c["criterion"]: c["score"] for c in b["assessment"]["criterion_scores"]},
            "inconsistencies": b["assessment"].get("inconsistencies", []),
            "missing_elements": b["assessment"].get("missing_elements", []),
            "improvement_suggestions": b["assessment"].get("improvement_suggestions", []),
            "full_assessment": b["assessment"],
            "draft": b["text"],
            "sources": b["sources"],
        }
    record = {
        "iteration": it,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "overall_score": round(sum(sections[p]["overall_score"] for p in PILLARS) / len(PILLARS), 2),
        "attempt_overall_score": round(sum(latest[p] for p in PILLARS) / len(PILLARS), 2),
        "sections": sections,
    }
    converged = all(passed.values())
    print(f"  Report score (best versions): {record['overall_score']:.2f}"
          + ("  -> CONVERGED" if converged else ""))
    update = {"best": best, "latest_attempt": latest, "passed": passed,
              "history": state["history"] + [record], "converged": converged}
    save_log({**state, **update})
    return update


def revise_node(state: LoopState):
    it = state["iteration"] + 1
    to_revise = [p for p in PILLARS if not state["passed"][p]]
    print(f"\n[Round {it}] REVISE: {', '.join(to_revise)}")
    candidates = {}
    for pillar in to_revise:
        b = state["best"][pillar]
        a = b["assessment"]
        extra = a.get("missing_elements", [])[:EXTRA_QUERIES_FROM_FEEDBACK]
        text, src = with_retry(generate_section, state["company"], pillar,
                               previous_draft=b["text"],
                               feedback=format_feedback(a, word_count(b["text"])),
                               extra_queries=extra)
        n = word_count(text)
        if n > SHORTEN_ABOVE:
            print(f"  {pillar}: {n} words, shortening...")
            text, src = with_retry(generate_section, state["company"], pillar,
                                   previous_draft=text,
                                   feedback=(f"The draft is {n} words; the limit is {WORD_LIMIT}. Shorten it to at most "
                                             f"{WORD_LIMIT} words by removing the least important content. Keep the "
                                             f"citations of the claims you keep. Do not add new information."),
                                   extra_queries=extra)
        print(f"  Revised {pillar} ({word_count(text)} words)")
        candidates[pillar] = {"text": text, "sources": src}
    return {"iteration": it, "candidates": candidates, "to_assess": to_revise}


def should_continue(state: LoopState):
    if state["converged"]:
        return "end"
    if state["iteration"] >= MAX_ITERATIONS:
        print(f"  Reached max iterations ({MAX_ITERATIONS}).")
        return "end"
    return "revise"


def build_graph():
    workflow = StateGraph(LoopState)
    workflow.add_node("generate", generate_node)
    workflow.add_node("assess", assess_node)
    workflow.add_node("revise", revise_node)
    workflow.set_entry_point("generate")
    workflow.add_edge("generate", "assess")
    workflow.add_conditional_edges("assess", should_continue, {"revise": "revise", "end": END})
    workflow.add_edge("revise", "assess")
    return workflow.compile()


def write_final_report(state):
    os.makedirs(FINAL_DIR, exist_ok=True)
    company = state["company"]
    progression = " → ".join(f"{r['overall_score']:.2f}" for r in state["history"])
    toc = "\n".join(f"{i}. [{p}](#{p.lower()})" for i, p in enumerate(PILLARS, 1))
    body = "\n\n".join(
        f"## {p}\n\n*Assessment score: {state['best'][p]['assessment']['overall_score']:.2f} / 5 "
        f"(version from iteration {state['best'][p]['iteration']})*\n\n{state['best'][p]['text']}"
        for p in PILLARS)
    sources = "\n".join(f"- {s}" for s in dict.fromkeys(s for p in PILLARS for s in state["best"][p]["sources"]))
    report = (f"# {company} ESG Report\n\n"
              f"*Generated {date.today()} | generator: {GEN_MODEL}, assessor: {ASSESS_MODEL} | loop {VERSION} | "
              f"rounds: {len(state['history'])} | score: {progression} | "
              f"{'converged' if state['converged'] else 'stopped at max iterations'}*\n\n"
              f"## Table of Contents\n\n{toc}\n\n{body}\n\n## Sources (retrieved chunks)\n\n{sources}\n")
    path = os.path.join(FINAL_DIR, f"{company.replace(' ', '_')}_final_report.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(report)
    return path


def run_loop(app, company):
    start = time.time()
    initial = {"company": company, "iteration": 0, "candidates": {}, "to_assess": [], "best": {},
               "latest_attempt": {}, "passed": {}, "history": [], "converged": False}
    final = app.invoke(initial)
    log_path = save_log(final, finished=True)
    report_path = write_final_report(final)
    print(f"\n=== {company}: {len(final['history'])} round(s), scores "
          f"{[r['overall_score'] for r in final['history']]}, "
          f"{'CONVERGED' if final['converged'] else 'not converged'}, {(time.time() - start) / 60:.1f} min")
    print(f"    Log: {log_path}\n    Report: {report_path}")


def main():
    companies = sys.argv[1:]
    if not companies:
        raise SystemExit('Usage: python feedback_loop.py "Company" ["Company 2" ...]')
    app = build_graph()
    try:
        os.makedirs(RUN_DIR, exist_ok=True)
        with open(os.path.join(RUN_DIR, "loop_graph.mmd"), "w") as f:
            f.write(app.get_graph().draw_mermaid())
    except Exception:
        pass
    for company in companies:
        try:
            run_loop(app, company)
        except (Exception, SystemExit) as e:
            print(f"!! {company} failed: {e!r}. Continuing with the next company.")


if __name__ == "__main__":
    main()
