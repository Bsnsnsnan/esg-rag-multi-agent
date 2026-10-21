import os
import sys
import json
import time
from datetime import datetime, date
from typing import TypedDict

from langgraph.graph import StateGraph, END

from generative_agent import generate_section, PILLARS, MODEL as GEN_MODEL
from assessment_agent import assess_section, CRITERIA, MODEL as ASSESS_MODEL

MAX_ITERATIONS = 3      # maximum number of assessment rounds
THRESHOLD = 4.0         # a section passes at >= 4.0 out of 5 ...
REQUIRE_NO_INCONSISTENCIES = True   # ... and only if the assessor found no internal contradictions
EXTRA_QUERIES_FROM_FEEDBACK = 3     # how many 'missing_elements' to turn into extra retrieval queries

LOG_DIR = "results/v1/loop_logs"
FINAL_DIR = "results/v1/final"


class LoopState(TypedDict):
    company: str
    iteration: int
    sections: dict      # pillar -> current section text
    sources: dict       # pillar -> list of chunk ids used as context
    assessments: dict   # pillar -> latest assessment JSON
    passed: dict        # pillar -> bool
    to_assess: list     # pillars written or revised in the current round
    history: list       # one record per assessment round (this becomes the log)
    converged: bool


# ---------- helpers ----------

def with_retry(fn, *args, retries=5, **kwargs):
    """Retry an API call if DashScope rate-limits us (HTTP 429)."""
    for attempt in range(retries):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if "429" not in str(e) or attempt == retries - 1:
                raise
            wait = 15 * (attempt + 1)
            print(f"    Rate limited, waiting {wait}s...")
            time.sleep(wait)


def section_passes(assessment):
    ok = assessment["overall_score"] >= THRESHOLD
    if REQUIRE_NO_INCONSISTENCIES:
        ok = ok and not assessment.get("inconsistencies")
    return ok


def format_feedback(assessment):
    """Turn the Assessment Agent's JSON into clear revision instructions for the Generative Agent."""
    lines = [f"Overall score: {assessment['overall_score']} / 5 (target: {THRESHOLD})."]

    if assessment.get("inconsistencies"):
        lines.append("\nInternal inconsistencies you MUST fix (re-check each figure against the context):")
        lines += [f"- {x}" for x in assessment["inconsistencies"]]

    weak = [c for c in assessment["criterion_scores"] if c["score"] < 4]
    if weak:
        lines.append("\nWeak criteria:")
        for c in weak:
            lines.append(f"- {c['criterion']} ({c['score']}/5): {c['justification']}")
            lines += [f"    * {s}" for s in c["improvement_suggestions"][:3]]

    if assessment.get("improvement_suggestions"):
        lines.append("\nTop priorities:")
        lines += [f"- {s}" for s in assessment["improvement_suggestions"][:5]]

    lines.append(
        "\nIMPORTANT: Only add information that appears in the Provided Context. If a suggestion needs "
        "data that is not in the context, do NOT invent it. List it under "
        "'### Not covered in source material' instead. Keep all correct content and citations."
    )
    return "\n".join(lines)


def save_log(state, finished=False):
    os.makedirs(LOG_DIR, exist_ok=True)
    rounds = state["history"]
    log = {
        "company": state["company"],
        "config": {
            "generator_model": GEN_MODEL,
            "assessor_model": ASSESS_MODEL,
            "max_iterations": MAX_ITERATIONS,
            "threshold": THRESHOLD,
            "require_no_inconsistencies": REQUIRE_NO_INCONSISTENCIES,
            "extra_queries_from_feedback": EXTRA_QUERIES_FROM_FEEDBACK,
        },
        "finished": finished,
        "converged": state.get("converged", False),
        "num_rounds": len(rounds),
        "score_progression": [r["overall_score"] for r in rounds],
        "section_score_progression": {p: [r["sections"][p]["overall_score"] for r in rounds]
                                      for p in PILLARS},
        "rounds": rounds,
    }
    path = os.path.join(LOG_DIR, f"{state['company'].replace(' ', '_')}_log.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
    return path


# ---------- graph nodes ----------

def generate_node(state: LoopState):
    print(f"\n[Round 1] GENERATE: writing all sections for {state['company']}")
    sections, sources = {}, {}
    for pillar in PILLARS:
        print(f"  Writing {pillar}...")
        text, src = with_retry(generate_section, state["company"], pillar)
        if not src:
            raise SystemExit(f"No chunks found for '{state['company']}'. Check the exact company name.")
        sections[pillar], sources[pillar] = text, src
    return {"iteration": 1, "sections": sections, "sources": sources,
            "to_assess": list(PILLARS), "passed": {p: False for p in PILLARS}}


def assess_node(state: LoopState):
    it = state["iteration"]
    print(f"[Round {it}] ASSESS: {', '.join(state['to_assess'])}")
    assessments, passed = dict(state.get("assessments") or {}), dict(state["passed"])
    start = time.time()

    for pillar in state["to_assess"]:
        a = with_retry(assess_section, state["company"], pillar, state["sections"][pillar])
        assessments[pillar], passed[pillar] = a, section_passes(a)
        flag = "PASS" if passed[pillar] else "revise"
        print(f"  {pillar:<14} {a['overall_score']:.2f}  "
              f"inconsistencies={len(a.get('inconsistencies', []))}  -> {flag}")

    # One log record per round. Sections that already passed keep their earlier score.
    round_record = {
        "iteration": it,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "assess_seconds": round(time.time() - start, 1),
        "overall_score": round(sum(assessments[p]["overall_score"] for p in PILLARS) / len(PILLARS), 2),
        "sections": {
            p: {
                "revised_this_round": p in state["to_assess"],
                "passed": passed[p],
                "overall_score": assessments[p]["overall_score"],
                "criterion_scores": {c["criterion"]: c["score"] for c in assessments[p]["criterion_scores"]},
                "inconsistencies": assessments[p].get("inconsistencies", []),
                "missing_elements": assessments[p].get("missing_elements", []),
                "improvement_suggestions": assessments[p].get("improvement_suggestions", []),
                "full_assessment": assessments[p],
                "draft": state["sections"][p],
                "sources": state["sources"][p],
            }
            for p in PILLARS
        },
    }
    history = state["history"] + [round_record]
    converged = all(passed.values())
    print(f"  Report overall score: {round_record['overall_score']:.2f}"
          + ("  -> CONVERGED" if converged else ""))

    update = {"assessments": assessments, "passed": passed, "history": history, "converged": converged}
    save_log({**state, **update})   # save after every round, so nothing is lost if it crashes
    return update


def revise_node(state: LoopState):
    it = state["iteration"] + 1
    to_revise = [p for p in PILLARS if not state["passed"][p]]
    print(f"\n[Round {it}] REVISE: {', '.join(to_revise)}")
    sections, sources = dict(state["sections"]), dict(state["sources"])

    for pillar in to_revise:
        a = state["assessments"][pillar]
        extra = a.get("missing_elements", [])[:EXTRA_QUERIES_FROM_FEEDBACK]
        print(f"  Revising {pillar} (+{len(extra)} extra retrieval queries from feedback)...")
        text, src = with_retry(generate_section, state["company"], pillar,
                               previous_draft=sections[pillar],
                               feedback=format_feedback(a),
                               extra_queries=extra)
        sections[pillar], sources[pillar] = text, src

    return {"iteration": it, "sections": sections, "sources": sources, "to_assess": to_revise}


def should_continue(state: LoopState):
    if state["converged"]:
        return "end"
    if state["iteration"] >= MAX_ITERATIONS:
        print(f"  Reached max iterations ({MAX_ITERATIONS}), stopping.")
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


# ---------- output ----------

def write_final_report(state):
    os.makedirs(FINAL_DIR, exist_ok=True)
    company = state["company"]
    last = state["history"][-1]
    progression = " → ".join(f"{r['overall_score']:.2f}" for r in state["history"])

    toc = "\n".join(f"{i}. [{p}](#{p.lower()})" for i, p in enumerate(PILLARS, 1))
    body = "\n\n".join(
        f"## {p}\n\n*Assessment score: {last['sections'][p]['overall_score']:.2f} / 5*\n\n{state['sections'][p]}"
        for p in PILLARS)
    all_sources = []
    for p in PILLARS:
        all_sources += state["sources"][p]
    sources = "\n".join(f"- {s}" for s in dict.fromkeys(all_sources))

    report = (f"# {company} ESG Report (Final, after feedback loop)\n\n"
              f"*Generated {date.today()} | generator: {GEN_MODEL}, assessor: {ASSESS_MODEL} | "
              f"rounds: {len(state['history'])} | score progression: {progression} | "
              f"{'converged' if state['converged'] else 'stopped at max iterations'}*\n\n"
              f"## Table of Contents\n\n{toc}\n\n{body}\n\n## Sources (retrieved chunks)\n\n{sources}\n")
    path = os.path.join(FINAL_DIR, f"{company.replace(' ', '_')}_final_report.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(report)
    return path


def run_loop(app, company):
    start = time.time()
    initial = {"company": company, "iteration": 0, "sections": {}, "sources": {}, "assessments": {},
               "passed": {}, "to_assess": [], "history": [], "converged": False}
    final = app.invoke(initial)

    log_path = save_log(final, finished=True)
    report_path = write_final_report(final)
    print(f"\n=== {company}: {len(final['history'])} round(s), "
          f"scores {[r['overall_score'] for r in final['history']]}, "
          f"{'CONVERGED' if final['converged'] else 'not converged'}, "
          f"{(time.time() - start) / 60:.1f} min")
    print(f"    Log:    {log_path}\n    Report: {report_path}")


def main():
    companies = sys.argv[1:]
    if not companies:
        raise SystemExit('Usage: python feedback_loop.py "Company" ["Company 2" ...]')

    app = build_graph()
    try:   # save the graph as a Mermaid diagram for your report
        os.makedirs("results", exist_ok=True)
        with open("results/v1/loop_graph.mmd", "w") as f:
            f.write(app.get_graph().draw_mermaid())
    except Exception:
        pass

    for company in companies:
        run_loop(app, company)


if __name__ == "__main__":
    main()