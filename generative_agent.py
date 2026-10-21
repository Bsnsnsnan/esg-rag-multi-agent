"""
Generative Agent v1: writes an E / S / G draft report for one company using RAG.

Run:  python generative_agent.py Apple
Out:  results/drafts/Apple_draft_v1.md
"""
import os
import sys
from datetime import date
from dotenv import load_dotenv
from openai import OpenAI
from retrieve import retrieve

load_dotenv()
client = OpenAI(api_key=os.getenv("DASHSCOPE_API_KEY"),
                base_url="https://ws-4huke4bou69ngcli.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1")
MODEL = "qwen-plus"   
PILLARS = {
    "Environmental": {
        "standards": "GRI 302 Energy, GRI 303 Water, GRI 305 Emissions, GRI 306 Waste; "
                     "TCFD Strategy, Risk Management, Metrics & Targets",
        "queries": ["Scope 1, Scope 2 and Scope 3 greenhouse gas emissions",
                    "energy consumption and renewable energy share",
                    "water withdrawal and consumption",
                    "waste generated, recycling and circularity",
                    "net-zero and climate targets",
                    "emissions reduction goal versus baseline year and progress"],
    },
    "Social": {
        "standards": "GRI 403 Occupational Health & Safety, GRI 404 Training, GRI 405 Diversity, "
                     "GRI 414 Supplier Social Assessment; TCFD Strategy (social impacts of climate transition)",
        "queries": ["number of employees and workforce composition",
                    "diversity, equity and inclusion, women in leadership",
                    "occupational health and safety injury rates",
                    "employee training and development hours",
                    "human rights and supply chain labour standards"],
    },
    "Governance": {
        "standards": "GRI 2 General Disclosures (governance), GRI 205 Anti-corruption; "
                     "TCFD Governance & Risk Management",
        "queries": ["board composition and independence",
                    "board oversight of sustainability and climate risk",
                    "anti-corruption, anti-bribery and code of conduct",
                    "executive remuneration linked to ESG targets",
                    "risk management process for climate-related risks"],
    },
}

SYSTEM_PROMPT = """You are an ESG report writer. Using ONLY the provided context from company
disclosures, write a professional report section on {pillar} performance for {company}.
Follow these standards: {standards}.

Rules:
- Include quantitative data where available, always with units and reporting year.
- Check that figures are consistent (parts must not exceed totals, scope labels such as
  market-based vs location-based must be consistent) and state the reporting year for every figure.
- After every factual claim, cite the chunk ID EXACTLY as it appears in the context
  (copy the full ID inside the square brackets; do not shorten it).
- Every sentence that states a fact must have a citation. If you cannot cite it, do not write it.
  Do not use general knowledge about the company.
- Attribute statements to the right organisation (e.g. an auditor's policy is not the company's policy).
- If information for a sub-topic is missing, list it under a final "### Not covered in source material"
  subheading (this means it was not found in the retrieved context, not that the company never discloses it).
- Do not write a title. Start directly with the first ### subheading. Use only ### for subheadings.
- Formal language suitable for stakeholders. 400-700 words."""


def gather_context(company, queries, k=4):
    """Run several searches and merge the results, dropping duplicate chunks."""
    seen, chunks = set(), []
    for q in queries:
        for r in retrieve(q, company=company, k=k):
            if r["id"] not in seen:
                seen.add(r["id"])
                chunks.append(r)
    return chunks


def generate_section(company, pillar, previous_draft=None, feedback=None, extra_queries=None):
    """Write one pillar section. previous_draft/feedback are for the Milestone 2 revise loop."""
    cfg = PILLARS[pillar]
    chunks = gather_context(company, cfg["queries"] + (extra_queries or []))
    context = "\n\n".join(f"[{c['id']}]\n{c['text'].replace(chr(0), '')}" for c in chunks)

    user_msg = f"Provided Context:\n{context}"
    if previous_draft and feedback:
        user_msg += (f"\n\nYour previous draft:\n{previous_draft}"
                     f"\n\nReviewer feedback. Revise the draft to address every point:\n{feedback}")

    resp = client.chat.completions.create(
        model=MODEL,
        temperature=0.3,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.format(
                pillar=pillar, company=company, standards=cfg["standards"])},
            {"role": "user", "content": user_msg},
        ],
    )
    return resp.choices[0].message.content, [c["id"] for c in chunks]


def main():
    if len(sys.argv) < 2:
        raise SystemExit('Usage: python generative_agent.py "Company Name"')
    company = sys.argv[1]

    sections, all_sources = {}, []
    for pillar in PILLARS:
        print(f"Writing {pillar} section for {company}...")
        text, sources = generate_section(company, pillar)
        if not sources:
            raise SystemExit(f"No chunks found for '{company}'. Check the exact company name.")
        sections[pillar] = text
        all_sources += sources

    toc = "\n".join(f"{i}. [{p}](#{p.lower()})" for i, p in enumerate(PILLARS, 1))
    body = "\n\n".join(f"## {p}\n\n{t}" for p, t in sections.items())
    sources = "\n".join(f"- {s}" for s in dict.fromkeys(all_sources))
    report = (f"# {company} ESG Report (Draft v1)\n\n"
              f"*Generated {date.today()} by Generative Agent v1 ({MODEL})*\n\n"
              f"## Table of Contents\n\n{toc}\n\n{body}\n\n## Sources (retrieved chunks)\n\n{sources}\n")

    os.makedirs("results/drafts", exist_ok=True)
    out = f"results/drafts/{company.replace(' ', '_')}_draft_v1.md"
    with open(out, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\nSaved draft to {out}")


if __name__ == "__main__":
    main()
