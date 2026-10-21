import os
import re
import sys
import json
import time
from dotenv import load_dotenv
from openai import OpenAI
from generative_agent import PILLARS

load_dotenv()
client = OpenAI(api_key=os.getenv("DASHSCOPE_API_KEY"),
                base_url="https://ws-4huke4bou69ngcli.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1")
MODEL = "qwen-plus"

# (criterion, what to assess, score guide)
RUBRIC = [
    ("Coverage", "Does the section address all required GRI/TCFD sub-topics for this pillar?",
     "1 = major topics missing; 3 = main topics covered but several missing; 5 = comprehensive"),
    ("Specificity", "Are claims supported by concrete data and numbers?",
     "1 = vague claims only; 3 = some figures, many general statements; 5 = specific figures with context"),
    ("Quantifiability", "Are metrics presented with units, timeframes, and baselines?",
     "1 = no numbers; 3 = numbers with units but few baselines; 5 = metrics with year-on-year comparison"),
    ("Forward-Looking", "Does it include targets, commitments, or projections?",
     "1 = purely historical; 3 = targets mentioned without timelines; 5 = clear targets with timelines and progress"),
    ("Transparency", "Are gaps, challenges, or negative results acknowledged?",
     "1 = only positive news; 3 = some gaps mentioned; 5 = honest about challenges and missing data"),
    ("Compliance Alignment", "Does it follow GRI/TCFD structural requirements?",
     "1 = no structure; 3 = partly organised by standard; 5 = fully aligned, with standards referenced"),
]
CRITERIA = [name for name, _, _ in RUBRIC]

ASSESSMENT_PROMPT = """You are a strict, independent ESG auditor. Evaluate the report section below
against the rubric. Be critical: a score of 5 must be rare and clearly justified. Judge only what is
actually written in the section. Do not give credit for information that is not there.
Check carefully before scoring:
- Internal consistency: sub-components must not exceed totals, scope labels (e.g. market-based vs
  location-based) must be consistent, and arithmetic must be correct. Any inconsistency caps
  Specificity at 3; list each one in missing_elements.
- Relevance: content placed under a heading it does not belong to (e.g. supplier energy training
  under GRI 404 employee training) does not count towards Coverage.
- Forward-Looking: score 3 or above only if there is at least one quantified target with a baseline
  year and a deadline.
- Transparency: admitting missing data earns at most 3; a 4-5 requires discussing real challenges,
  negative trends or missed targets.
- In missing_elements and improvement_suggestions, describe WHAT information to add; never
  invent example figures, values or targets. Only cite a GRI/TCFD code if you are certain it is correct.

Company: {company}
Pillar: {pillar}
Relevant standards: {standards}

Rubric (score each criterion with an integer from 1 to 5):
{rubric}

Return ONLY a JSON object with exactly this structure, with one entry per criterion in the order above:
{{
  "criterion_scores": [
    {{"criterion": "<criterion name>", "score": <integer 1-5>,
      "justification": "<1-2 sentences>",
      "missing_elements": ["<specific missing item>", "..."],
      "improvement_suggestions": ["<specific actionable fix>", "..."]}}
  ],
  "inconsistencies": ["<each internal contradiction or arithmetic error found, or empty list>"],
  "missing_elements": ["<the most important missing disclosures for the whole section>"],
  "improvement_suggestions": ["<the most important fixes, highest priority first>"]
}}

Report section:
\"\"\"
{report_text}
\"\"\""""


def call_llm(messages, retries=5):
    """Call Qwen in JSON mode, waiting and retrying if rate-limited."""
    for attempt in range(retries):
        try:
            resp = client.chat.completions.create(
                model=MODEL, temperature=0, messages=messages,
                response_format={"type": "json_object"},
            )
            return resp.choices[0].message.content
        except Exception as e:
            if "429" not in str(e) or attempt == retries - 1:
                raise
            wait = 10 * (attempt + 1)
            print(f"  Rate limited, waiting {wait}s...")
            time.sleep(wait)


def validate(result):
    """Check the JSON has all 6 criteria with valid scores; compute the overall score ourselves."""
    by_name = {c.get("criterion"): c for c in result.get("criterion_scores", [])}
    missing = [name for name in CRITERIA if name not in by_name]
    if missing:
        raise ValueError(f"missing criteria: {missing}")

    ordered = []
    for name in CRITERIA:
        c = by_name[name]
        score = int(c["score"])
        if not 1 <= score <= 5:
            raise ValueError(f"{name} score out of range: {score}")
        ordered.append({
            "criterion": name,
            "score": score,
            "justification": c.get("justification", ""),
            "missing_elements": c.get("missing_elements", []),
            "improvement_suggestions": c.get("improvement_suggestions", []),
        })

    # Enforce the consistency rule in code: the LLM does not always apply the cap itself
    inconsistencies = result.get("inconsistencies", []) or []
    if inconsistencies:
        for c in ordered:
            if c["criterion"] == "Specificity" and c["score"] > 3:
                c["score"] = 3
                c["justification"] += " [Capped at 3: internal inconsistencies found.]"

    return {
        "criterion_scores": ordered,
        "inconsistencies": inconsistencies,
        # computed in Python, not by the LLM: models are unreliable at arithmetic
        "overall_score": round(sum(c["score"] for c in ordered) / len(ordered), 2),
        "missing_elements": result.get("missing_elements", []),
        "improvement_suggestions": result.get("improvement_suggestions", []),
    }


def assess_section(company, pillar, section_text, max_attempts=3):
    """Score one section. Retries if the model returns invalid JSON or an incomplete result."""
    rubric_text = "\n".join(f"{i}. {name}: {what} ({guide})"
                            for i, (name, what, guide) in enumerate(RUBRIC, 1))
    prompt = ASSESSMENT_PROMPT.format(
        company=company, pillar=pillar, standards=PILLARS[pillar]["standards"],
        rubric=rubric_text, report_text=section_text)

    for attempt in range(max_attempts):
        raw = call_llm([{"role": "user", "content": prompt}])
        raw = re.sub(r"^```(?:json)?|```$", "", raw.strip()).strip()  # strip code fences if any
        try:
            return validate(json.loads(raw))
        except (json.JSONDecodeError, ValueError, KeyError, TypeError) as e:
            print(f"  Invalid assessment ({e}), retrying ({attempt + 1}/{max_attempts})...")
    raise RuntimeError(f"Assessment failed for {company} / {pillar} after {max_attempts} attempts")


def split_sections(markdown):
    """Pull the Environmental / Social / Governance sections out of a draft report."""
    sections = {}
    for pillar in PILLARS:
        m = re.search(rf"^## {pillar}\s*\n(.*?)(?=^## |\Z)", markdown, re.S | re.M)
        if m:
            sections[pillar] = m.group(1).strip()
    return sections


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python assessment_agent.py results/drafts/<Company>_draft_v1.md")
    path = sys.argv[1]
    with open(path, encoding="utf-8") as f:
        markdown = f.read()

    title = re.search(r"^# (.+?) ESG Report", markdown, re.M)
    company = title.group(1) if title else "Unknown"
    sections = split_sections(markdown)
    if not sections:
        raise SystemExit("No '## Environmental/Social/Governance' sections found in the file.")

    results = {}
    for pillar, text in sections.items():
        print(f"Assessing {pillar}...")
        results[pillar] = assess_section(company, pillar, text)

    print(f"\n{'Criterion':<22}" + "".join(f"{p[:5]:>8}" for p in results))
    for i, name in enumerate(CRITERIA):
        print(f"{name:<22}" + "".join(f"{r['criterion_scores'][i]['score']:>8}" for r in results.values()))
    print(f"{'OVERALL':<22}" + "".join(f"{r['overall_score']:>8.2f}" for r in results.values()))

    os.makedirs("results/assessments", exist_ok=True)
    out = os.path.join("results/assessments",
                       os.path.basename(path).replace(".md", "_assessment.json"))
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"company": company, "source_draft": path, "model": MODEL,
                   "sections": results}, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()