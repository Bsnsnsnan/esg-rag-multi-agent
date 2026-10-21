"""
Milestone 3 case studies: runs the full pipeline (RAG retrieval -> Generate -> Assess -> Revise)
for several companies, then builds every table and chart with analyze_results.py.

Run (from the project folder, venv active):
    caffeinate -i python run_case_studies.py          # default 5 companies, Mac stays awake
    python run_case_studies.py Amazon Shell           # only these companies
    python run_case_studies.py --force                # re-run companies that already have a finished log
    python run_case_studies.py --analyze-only         # skip the API calls, just rebuild tables/charts

It is resumable: a company whose log is already finished is skipped, so if the run stops
(rate limit, Wi-Fi, laptop sleep) just run the same command again.
"""
import os
import sys
import json
import time
import traceback
from datetime import datetime

# 5 companies across 4 industries, all with full E/S/G sustainability reports
DEFAULT_COMPANIES = ["Amazon", "Samsung", "Unilever", "Shell", "HSBC"]
LOG_DIR = "results/loop_logs"
ERROR_LOG = "results/case_study_errors.txt"


def is_finished(company):
    path = os.path.join(LOG_DIR, f"{company.replace(' ', '_')}_log.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f).get("finished", False)
    except (OSError, ValueError):
        return False


def record_error(company, err):
    os.makedirs("results", exist_ok=True)
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {company}: {err}\n")


def main():
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    companies = [a for a in sys.argv[1:] if not a.startswith("--")] or DEFAULT_COMPANIES

    if "--analyze-only" not in flags:
        from feedback_loop import build_graph, run_loop
        app = build_graph()
        start = time.time()
        for i, company in enumerate(companies, 1):
            if is_finished(company) and "--force" not in flags:
                print(f"[{i}/{len(companies)}] {company}: finished log exists, skipping (use --force to re-run)")
                continue
            print(f"\n{'#' * 60}\n[{i}/{len(companies)}] {company}\n{'#' * 60}")
            try:
                run_loop(app, company)
            except (Exception, SystemExit) as e:
                traceback.print_exc()
                record_error(company, repr(e))
                print(f"!! {company} failed, continuing with the next company (details in {ERROR_LOG})")
        print(f"\nAll loops done in {(time.time() - start) / 60:.1f} min.")

    import analyze_results
    done = [c for c in companies if is_finished(c)]
    missing = [c for c in companies if c not in done]
    if missing:
        print(f"\nNot finished (re-run the same command to retry): {', '.join(missing)}")
    if done:
        analyze_results.main(done)


if __name__ == "__main__":
    main()
