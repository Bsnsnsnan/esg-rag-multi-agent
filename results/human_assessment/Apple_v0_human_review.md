# Human assessment: Apple_draft_v0.md

| Criterion | Environmental | Social | Governance |
|---|---|---|---|
| Coverage | 3 | 2 | 2 |
| Specificity | 4 | 2 | 3 |
| Quantifiability | 3 | 2 | 2 |
| Forward-Looking | 2 | 1 | 1 |
| Transparency | 4 | 5* | 4* |
| Compliance Alignment | 4 | 3 | 2 |
| Average | 3.3 | 2.5 | 2.3 |

Overall: about 2.7 out of 5. The Environmental section is a usable draft. The Social and Governance sections are mostly lists of what is missing.

\*These Transparency scores need a caveat, explained under "Cross-cutting issues" below.

## Environmental (3.3)

**Coverage: 3.** The section covers GRI 302, 303, 305 and 306. It leaves out:
- GRI 301 Materials, which is arguably Apple's most material topic (recycled content, rare earths, cobalt).
- GRI 304 Biodiversity.
- All four TCFD pillars. These are only noted as a gap.

**Specificity: 4.** The section is full of figures, but several are wrong or mislabelled:
- Scope 2 contradiction. The report gives "Scope 2 (market-based)" as 278,108 tCO₂e. Two sentences later it says Scope 2 from electricity is zero and steam/heating/cooling is 3,300 tCO₂e. The 278k figure is probably location-based.
- Footprint mislabelled. The "Net corporate emissions… 14.5 million" figure is actually the company-wide footprint, which includes Scope 3. Corporate emissions are only about 0.06 Mt. Also, 15.3 − 0.7 gives 14.6, not 14.5.
- Manufacturing figure is impossible. Manufacturing is given as 29.03 Mt, which is larger than the 15.3 Mt gross total. It is probably taken from an older year.
- "100% of total energy use" is wrong. That figure is renewable electricity. Scope 1 fuel use (55,200 tCO₂e) shows the company's energy is not all renewable.
- Wrong label for the 1,782 MW. It is described as "on-site generation." It is more likely Apple-created projects in total, not on-site capacity.
- Ambiguous water target. AWS certification "by 2025" reads as a target, but it is presented as an achievement.

**Quantifiability: 3.** Units and fiscal years are given consistently. However:
- There are no baselines and no year-on-year comparisons.
- FY2020 colocation data is mixed in with FY2024 data without any flag.

**Forward-Looking: 2.** This is the biggest miss. The report never mentions Apple 2030, the goal of cutting emissions 75% against a 2015 baseline and neutralizing the rest. The only targets mentioned are the Zero Waste Program and the 2030 supplier water reuse target, and the latter appears only in the gaps list.

> **Correction (after cross-checking):** the draft does mention the Apple 2030 target ("carbon neutrality across its entire value chain by 2030—entailing a 75% reduction in gross emissions from the 2015 baseline"). This point in the human review was wrong; the agent's higher Forward-Looking score is defensible.

**Transparency: 4.** The gaps list is specific and useful. Noting that e-waste is excluded from the diversion rate is a good catch.

**Compliance Alignment: 4.** Headings follow GRI standards. It would score higher if it cited disclosure-level numbers (for example 305-1, 305-2, 305-3) and had a TCFD mapping.

## Social (2.5)

**Coverage: 2.** The four GRI headers are there, but GRI 405 is empty and GRI 403 has no performance data. Also missing are:
- GRI 401 Employment
- GRI 408/409 Child and forced labour
- GRI 413 Communities
- GRI 416 Customer health and safety

**Specificity: 2.** Most of the content is a paraphrase of the EHS policy. Two sub-sections borrow environmental material:
- The Clean Energy Academy (renewable energy training for suppliers) is used to fill GRI 404, which is about employee training.
- Chemical safety programs are used to fill GRI 414, which is about supplier labour and social assessment.

**Quantifiability: 2.** Only three numbers appear: about 300 supplier facilities, 65+ safer cleaners, and 164,000 employees. None of them measure social performance.

**Forward-Looking: 1.** There are no targets.

**Compliance Alignment: 3.** The GRI headings are correct, but the content under them does not answer what those standards ask for.

## Governance (2.3)

**Coverage: 2.** The section has none of the following:
- GRI 2-9 to 2-21 (governance structure and remuneration)
- GRI 205 Anti-corruption, beyond a policy quote
- GRI 415 Public policy
- TCFD Governance, which is acknowledged as missing

**Specificity: 3.** The Green Bond details are concrete: the amount, the notes, the reporting period and the assurance date. But two parts are misplaced:
- The independence statements from the assurance providers (Apex, Trinity) are presented as evidence of Apple's own anti-corruption practices. They are not.
- The F-GHG abatement result is presented as a governance outcome. It belongs under emissions.

The 8.4 Mt F-GHG figure is also worth checking against the source chunk.

**Quantifiability: 2 and Forward-Looking: 1.** There are almost no governance metrics and no targets.

**Compliance Alignment: 2.** Unlike the other two pillars, the headings cite no GRI or TCFD codes.

## Cross-cutting issues

- **The report draws on a single source.** Every citation comes from the Environmental Progress Report 2025. That alone guarantees weak Social and Governance sections. To fix this, add these sources to the retrieval corpus: the Proxy Statement (board, compensation, oversight); the People and Environment in Our Supply Chain report (supplier audits, labour); the 10-K (risk factors); Apple's Ethics & Compliance and inclusion disclosures.
- **The "disclosure gaps" mix up two different things.** Many of them really mean "not in our retrieved chunks," not "Apple doesn't disclose this." Apple does publish supplier audit results and board oversight details. Presented as company gaps, these items are misleading. Social and Governance score high on Transparency only because the generator is candid about its own missing context. I'd relabel these as "Not covered in source material."
- **Numbers are not checked against each other.** The Scope 2 and footprint errors could be caught automatically. A simple check (sub-components ≤ totals, scope labels consistent) before publishing would catch most of them.
- **TCFD is absent throughout.** The rubric covers both GRI and TCFD, but none of the four TCFD pillars appears anywhere. A short TCFD index mapping each pillar to the relevant sections would lift Coverage and Compliance in all three pillars.
