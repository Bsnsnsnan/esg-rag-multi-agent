# Results summary (v1)

Companies analysed: **5** (Amazon, Samsung, Unilever, Shell, HSBC) across **4 industries** (Consumer Goods, Energy, Financial Services, Technology). Generator and assessor: Qwen (see loop logs for model names). Pass rule: score ≥ 4.0 and no inconsistencies; max 3 rounds. The loop returns the latest version of each section.

## Headline numbers

- Mean overall score went from **3.46** (iteration 1) to **3.31** (final), a change of **-0.15** points; 2/5 companies improved.
- If the loop kept the best-scoring version of each section instead of the last one, the mean would be **3.65** (+0.19). This is an upper bound: picking the maximum of noisy scores inflates it.
- Words per section: **658** in iteration 1, **1022** in the last attempts, **1022** in the returned versions (instruction: 400–700).
- Largest gain: Samsung (+0.22); smallest: Unilever (-0.61).
- Convergence (every section passing): **0/5** companies. Mean rounds used: **3.0** (distribution: 3 rounds: 5).
- Sections at or above 4.0 after the loop: **3/15**.
- Internal inconsistencies flagged by the assessor: **18** in iteration 1 → **16** in the final round.

## Cross-industry comparison

**Best / worst initial disclosure quality.** Best: **Energy** (3.78, n=1); worst: **Technology** (3.28, n=2). Full ranking: Energy 3.78 (n=1); Consumer Goods 3.50 (n=1); Financial Services 3.45 (n=1); Technology 3.28 (n=2).

**Pillar with the most gaps.** Gaps flagged in iteration 1: Environmental 98, Social 116, Governance 131 → most: **Governance**. Mean initial pillar scores: Environmental 3.93, Social 3.37, Governance 3.07 (lowest: **Governance**); final: Environmental 3.80, Social 3.33, Governance 2.80.

**Iterations to converge.** Mean 3.0 rounds; 0/5 companies converged within the 3-round limit.

**Gaps flagged in iteration 1:** 345 in total. 31 (9%) are about reporting practice (missing baselines, targets, definitions or GRI references) rather than a specific topic; 1 unclassified. Most common topics: Anti-corruption & business ethics (48); Climate risk & strategy (TCFD) (47); Board structure & oversight (43); Occupational health & safety (39); GHG emissions & air quality (39).

**Rubric criteria (mean, iteration 1 → final).** Most improved: Transparency 3.27→3.60, Compliance Alignment 4.07→3.93; least improved: Forward-Looking 3.33→3.07, Quantifiability 3.67→3.33. Lowest final criterion: Coverage (2.73).

## SASB cross-check

Of 30 SASB material topics across the companies: addressed, gaps flagged 22 (73%), blind spot 6 (20%), addressed 2 (7%).
Blind spots per company: Amazon: Data privacy & advertising standards, Data security; Samsung: Product security; Unilever: Product environmental, health & safety performance; Shell: Biodiversity impacts; HSBC: Data security.

## Per-company results

| Company | Industry | Initial | Final | Change | Rounds | Converged | Inconsistencies (init→final) |
|---|---|---|---|---|---|---|---|
| Amazon | Technology | 3.11 | 2.61 | -0.50 | 3 | no | 3→5 |
| Samsung | Technology | 3.45 | 3.67 | +0.22 | 3 | no | 6→2 |
| Unilever | Consumer Goods | 3.50 | 2.89 | -0.61 | 3 | no | 5→4 |
| Shell | Energy | 3.78 | 3.78 | +0.00 | 3 | no | 1→3 |
| HSBC | Financial Services | 3.45 | 3.61 | +0.16 | 3 | no | 3→2 |

## Figures

- `results/v1/figures/fig1_convergence.png`
- `results/v1/figures/fig2_section_progression.png`
- `results/v1/figures/fig3_improvement.png`
- `results/v1/figures/fig4_radar_industry.png`
- `results/v1/figures/fig5_gap_heatmap.png`
- `results/v1/figures/fig6_criteria_initial_vs_final.png`

## Caveats

- Scores come from a single LLM judge (Qwen) that also shares a model family with the generator; human calibration on one company (Apple) showed a mean absolute difference of about 0.4–0.8 points.
- Improvement is measured by the same assessor that gives the feedback, so part of the gain may be the generator learning what the assessor rewards rather than better disclosure.
- Gap topics are assigned by keyword rules (gap_analysis.py); some gaps fit several topics or none ('Other').
- The SASB topic lists are a simplified mapping and should be checked on materiality.sasb.org.
- Small sample: 5 companies, mostly one per industry, so industry comparisons are indicative only.
- 'Gaps' mean information not found in the retrieved chunks of one report, not necessarily that the company never discloses it.