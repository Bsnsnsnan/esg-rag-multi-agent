# Results summary (v2)

Companies analysed: **5** (Amazon, Samsung, Unilever, Shell, HSBC) across **4 industries** (Consumer Goods, Energy, Financial Services, Technology). Generator and assessor: Qwen (see loop logs for model names). Pass rule: score ≥ 4.0 and ≤ 1 inconsistency; max 3 rounds. The loop returns the best-scoring version of each section.

## Headline numbers

- Mean overall score went from **3.35** (iteration 1) to **3.61** (final), a change of **+0.26** points; 5/5 companies improved.
- Without best-keeping (taking each section's last attempt) the mean would be **3.49** (+0.14).
- Words per section: **651** in iteration 1, **705** in the last attempts, **711** in the returned versions (instruction: 400–700).
- Largest gain: HSBC (+0.44); smallest: Samsung (+0.16).
- Convergence (every section passing): **0/5** companies. Mean rounds used: **3.0** (distribution: 3 rounds: 5).
- Sections at or above 4.0 after the loop: **4/15**.
- Internal inconsistencies flagged by the assessor: **21** in iteration 1 → **15** in the final round.

## Cross-industry comparison

**Best / worst initial disclosure quality.** Best: **Energy** (4.00, n=1); worst: **Financial Services** (3.17, n=1). Full ranking: Energy 4.00 (n=1); Consumer Goods 3.22 (n=1); Technology 3.17 (n=2); Financial Services 3.17 (n=1).

**Pillar with the most gaps.** Gaps flagged in iteration 1: Environmental 92, Social 124, Governance 134 → most: **Governance**. Mean initial pillar scores: Environmental 3.97, Social 3.40, Governance 2.67 (lowest: **Governance**); final: Environmental 4.03, Social 3.63, Governance 3.17.

**Iterations to converge.** Mean 3.0 rounds; 0/5 companies converged within the 3-round limit.

**Gaps flagged in iteration 1:** 350 in total. 32 (9%) are about reporting practice (missing baselines, targets, definitions or GRI references) rather than a specific topic; 10 unclassified. Most common topics: Anti-corruption & business ethics (60); Climate risk & strategy (TCFD) (58); Board structure & oversight (43); Diversity, equity & inclusion (43); Training & development (39).

**Rubric criteria (mean, iteration 1 → final).** Most improved: Transparency 2.93→3.60, Compliance Alignment 3.73→4.13; least improved: Forward-Looking 3.40→3.53, Coverage 3.00→3.00. Lowest final criterion: Coverage (3.00).

## SASB cross-check

Of 30 SASB material topics across the companies: addressed, gaps flagged 22 (73%), blind spot 6 (20%), addressed 1 (3%), flagged as gap 1 (3%).
Blind spots per company: Amazon: Data privacy & advertising standards, Data security; Samsung: Product security; Unilever: Product environmental, health & safety performance; Shell: Biodiversity impacts; HSBC: Data security.

## Per-company results

| Company | Industry | Initial | Final | Change | Rounds | Converged | Inconsistencies (init→final) |
|---|---|---|---|---|---|---|---|
| Amazon | Technology | 2.78 | 3.11 | +0.33 | 3 | no | 5→3 |
| Samsung | Technology | 3.56 | 3.72 | +0.16 | 3 | no | 3→3 |
| Unilever | Consumer Goods | 3.22 | 3.44 | +0.22 | 3 | no | 5→3 |
| Shell | Energy | 4.00 | 4.17 | +0.17 | 3 | no | 1→1 |
| HSBC | Financial Services | 3.17 | 3.61 | +0.44 | 3 | no | 7→5 |

## Figures

- `results/v2/figures/fig1_convergence.png`
- `results/v2/figures/fig2_section_progression.png`
- `results/v2/figures/fig3_improvement.png`
- `results/v2/figures/fig4_radar_industry.png`
- `results/v2/figures/fig5_gap_heatmap.png`
- `results/v2/figures/fig6_criteria_initial_vs_final.png`

## Caveats

- Scores come from a single LLM judge (Qwen) that also shares a model family with the generator; human calibration on one company (Apple) showed a mean absolute difference of about 0.4–0.8 points.
- Keeping the best of several noisy scores biases the returned score upwards (selection effect); compare gains with the assessor's re-scoring variation (assessor_noise.py).
- Improvement is measured by the same assessor that gives the feedback, so part of the gain may be the generator learning what the assessor rewards rather than better disclosure.
- Gap topics are assigned by keyword rules (gap_analysis.py); some gaps fit several topics or none ('Other').
- The SASB topic lists are a simplified mapping and should be checked on materiality.sasb.org.
- Small sample: 5 companies, mostly one per industry, so industry comparisons are indicative only.
- 'Gaps' mean information not found in the retrieved chunks of one report, not necessarily that the company never discloses it.