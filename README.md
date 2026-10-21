# ESG report generation with RAG and two agents

A pipeline that drafts the Environmental, Social and Governance sections of an ESG report from a company's own sustainability report, then has a second model grade each section and send it back for revision.

- **Retrieval:** 15 corporate sustainability reports are split into chunks, embedded with Qwen `text-embedding-v3` and stored in ChromaDB.
- **Generative agent** (`qwen-plus`): writes each section using only the retrieved chunks, citing chunk IDs and listing what the sources don't cover.
- **Assessment agent** (`qwen-plus`): scores each section 1–5 on six criteria (coverage, specificity, quantifiability, forward-looking, transparency, GRI/TCFD alignment), lists internal inconsistencies and returns JSON feedback.
- **Loop** (LangGraph): generate → assess → revise, up to 3 rounds. A section passes at a score of 4.0 or more with at most one inconsistency.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # then put your DashScope key in .env
python test_qwen_api.py   # should print a short paragraph
```

Chat calls go through the workspace endpoint in `test_qwen_api.py`, `generative_agent.py` and `assessment_agent.py`; embeddings use `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`. Change these if your account uses different endpoints.

## Running it

**1. Build the vector store** (PDFs go in `docs/esg_reports/`, company and industry per file in `docs/industry_mapping.csv`):
```bash
python chunk_pdfs.py
python apply_industry_mapping.py
python embed_and_store.py
```
After editing `industry_mapping.csv`, delete `chroma_db/` and run these three again so the database picks up the new names.

**2. Check retrieval:**
```bash
python retrieve.py                  # top 5 chunks for a test query
python eval_retrieval.py run        # writes results/retrieval_eval.csv; label the 'relevant' column 0/1
python eval_retrieval.py score      # precision@5
```

**3. Generate and assess one report:**
```bash
python generative_agent.py Apple
python assessment_agent.py results/drafts/Apple_draft_v1.md
```

**4. Run the loop and analyse it:**
```bash
python feedback_loop.py Amazon Samsung Unilever Shell HSBC
python analyze_results.py --run v2
python assessor_noise.py            # how much scores vary when the same text is re-scored
python compare_runs.py              # v1 vs v2
```
Each company takes 10–15 minutes. Company names must match `docs/industry_mapping.csv`.

`demo.ipynb` shows retrieval and generation for one company. `analysis.ipynb` shows the case study results and charts.

## Results

**Retrieval:** precision@5 of 0.82 on 10 hand-labelled queries (one result still unlabelled).

**Assessor vs human:** on the Apple draft, the agent's scores were within 1 point of a human review on every criterion (mean absolute difference 0.44). After tightening the prompt it caught the same Scope 2 and emissions-labelling errors the human found, but drifted further from the human scores overall (0.78), partly because the human had missed a target that was in the draft. See `results/human_assessment/`.

**Feedback loop, 5 companies across 4 industries:**

| | v1 | v2 |
|---|---|---|
| Mean change in score, round 1 → final | −0.15 | +0.26 |
| Companies improved | 2/5 | 5/5 |
| Words per section at the end | 1,022 | 711 |
| Inconsistencies, round 1 → final | 18 → 16 | 21 → 15 |
| Companies where every section passed | 0/5 | 0/5 |

v1 returned the latest revision of each section. Revisions kept getting longer, and scores dropped for Amazon and Unilever. v2 keeps the best-scoring version, revises by editing it, and enforces a 700-word limit.

Re-scoring the same text moves a report's score by 0.15 on average, so v2's +0.26 is real but small. Taking the last attempt instead of the best one gives only +0.14, so part of the gain comes from keeping the highest of several noisy scores.

**Other findings:**
- Governance was the weakest pillar (2.67 at round 1) and had the most gaps. The most common gap topics were anti-corruption and ethics, climate risk (TCFD) and board oversight.
- Shell (energy) scored highest at round 1; the financial and technology companies lowest.
- 6 of the 30 SASB material topics for these industries were never examined, mostly data security and privacy. The retrieval queries never ask about them.

Full numbers: `results/v2/analysis_summary.md`, `results/v1/analysis_summary.md`, `results/comparison/comparison.md`.

## Limitations

- One model family writes and grades the reports, and the loop optimises against the same grader it is measured by.
- Each company is represented by a single report, so a "gap" means the retrieved chunks didn't cover it, not that the company never discloses it.
- The retrieval queries are the same for every industry, which is why industry-specific SASB topics get missed.
- Five companies, mostly one per industry, so the industry comparisons are indicative only.

## Files

```
chunk_pdfs.py, apply_industry_mapping.py, embed_and_store.py   build the vector store
retrieve.py, eval_retrieval.py                                  retrieval and precision@5
generative_agent.py, assessment_agent.py                        the two agents
feedback_loop.py                                                LangGraph loop (v2)
feedback_loop_v1.py                                             first version, kept for comparison
analyze_results.py, gap_analysis.py                             tables, charts, GRI/SASB gap analysis
compare_runs.py, assessor_noise.py                              v1 vs v2, scoring variation
demo.ipynb, analysis.ipynb                                      notebooks
docs/                                                           source PDFs, industry mapping, GRI/TCFD topic map
results/                                                        drafts, assessments, loop logs, charts
```
