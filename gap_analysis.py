"""Classifies assessor gaps into GRI/TCFD topics and cross-checks them against SASB material topics.

SASB topic lists are simplified from https://materiality.sasb.org/ ; verify before citing.
"""
import re

# (topic, pillar, GRI / TCFD reference, keyword regex)
TOPICS = [
    ("GHG emissions & air quality", "Environmental", "GRI 305 / TCFD Metrics & Targets",
     r"emission|scope ?[123]\b|\bghg|co2|co₂|carbon|net[- ]zero|decarboni|methane|flaring|air quality|\bnox\b|\bsox\b"),
    ("Energy", "Environmental", "GRI 302",
     r"energy|renewable|electricity|\bfuels?\b"),
    ("Water & effluents", "Environmental", "GRI 303",
     r"water|effluent|\bwue\b|gri ?303"),
    ("Waste, packaging & circularity", "Environmental", "GRI 306",
     r"waste|recycl|landfill|circular|packaging"),
    ("Materials & sourcing", "Environmental", "GRI 301",
     r"\bmaterials?\b|raw material|recycled content|plastic|palm oil|minerals?\b|cobalt|sourcing"),
    ("Biodiversity & land use", "Environmental", "GRI 304",
     r"biodiversity|deforestation|land[- ]use|ecosystem|\bnature\b|habitat"),
    ("Occupational health & safety", "Social", "GRI 403",
     r"gri ?403|ill[- ]health|hazardous|\b(?:rir|trfr|trcf|ltif|fpi(?:-f)?)\b|safety|\behs\b|injur|\btrir\b|\bltir\b|\blti\b|fatalit|lost[- ]time|occupational|critical incident"),
    ("Training & development", "Social", "GRI 404",
     r"training|trained|upskill|reskill|learning|\bskills?\b"),
    ("Diversity, equity & inclusion", "Social", "GRI 405",
     r"gri ?405|diversity|de&i|dei\b|gender|women|female|underrepresented|inclusion|pay (?:equity|gap|ratio)|ethnic"),
    ("Employment & labour practices", "Social", "GRI 401 / 402",
     r"gri ?40[12]|turnover|new hires|attrition|parental leave|headcount|\bworkforce\b|working hour|employee (?:benefit|engagement|recruit|retention)"),
    ("Human rights & labour standards", "Social", "GRI 407–412",
     r"human rights|child labou?r|forced labou?r|modern slavery|collective bargaining|freedom of association|living wage|grievance|indigenous"),
    ("Supplier social assessment", "Social", "GRI 414",
     r"gri ?414|suppliers? (?:audit|social|assess|screening|code|due diligence|non-?compliance|non-?conformit|performance|evaluation)|suppliers assessed|tier[- ]?[12]\b|supply chain (?:audit|labou?r|due diligence)|third-party due diligence"),
    ("Local communities & inclusion", "Social", "GRI 413",
     r"communit|social investment|philanthrop|financial inclusion|access to finance"),
    ("Customer privacy & data security", "Social", "GRI 418",
     r"privacy|data security|cyber|data breach|product security|information security"),
    ("Product & customer safety", "Social", "GRI 416 / 417",
     r"product safety|customer (?:health|safety)|product quality|labell?ing|recall|food safety|nutrition"),
    ("Board structure & oversight", "Governance", "GRI 2-9 to 2-13 / TCFD Governance",
     r"\bboard|director|committee|oversight|independen|governance structure"),
    ("Remuneration & incentives", "Governance", "GRI 2-19 / 2-20",
     r"gri ?2-(?:19|20|21)|remunerat|compensation|executive (?:pay|evaluation)|incentive|bonus"),
    ("Anti-corruption & business ethics", "Governance", "GRI 205 / 206",
     r"gri ?20[56]|corruption|briber|ethic|whistleblow|speak[- ]up|helpline|retaliation|conflicts? of interest|code of conduct|compliance audit|anti-?competitive|antitrust"),
    ("Tax", "Governance", "GRI 207",
     r"\btax"),
    ("Public policy & lobbying", "Governance", "GRI 415",
     r"lobby|political|public policy|trade association|regulatory environment"),
    ("Climate risk & strategy (TCFD)", "Governance", "GRI 201-2 / TCFD Strategy & Risk Mgmt",
     r"scenario|climate[- ]related (?:risk|financial)|climate risk|physical risk|transition risk|tcfd|risk management|financed emissions|credit (?:risk|analysis)|lending|portfolio|capital expenditure|capex|reserves"),
]
TOPIC_NAMES = [t[0] for t in TOPICS]

# Gaps that are about how a report is written rather than an ESG topic
REPORTING_PRACTICE = "Reporting practice (baselines, targets, definitions, GRI refs)"
_PRACTICE = re.compile(r"baseline|target|deadline|milestone|definition|defin|denominator|timeframe|boundary|"
                       r"materiality|gri[- ]?(?:style|indicator|disclosure|code|\d)|disclosure number|assurance|verification|"
                       r"trend|year-on-year|prior year|methodology|missed|declin|deteriorat|challenge|"
                       r"stakeholder engagement|reporting period|unreported|scope clarification|explanation|reasons for", re.I)
ALL_LABELS = TOPIC_NAMES + [REPORTING_PRACTICE, "Other"]
TOPIC_PILLAR = {t[0]: t[1] for t in TOPICS}
TOPIC_REF = {t[0]: t[2] for t in TOPICS}
_PATTERNS = [(t[0], re.compile(t[3], re.I)) for t in TOPICS]


def classify(text):
    """Topics whose keywords appear in the text; otherwise reporting-practice or Other."""
    topics = [name for name, pat in _PATTERNS if pat.search(text or "")]
    if topics:
        return topics
    return [REPORTING_PRACTICE] if _PRACTICE.search(text or "") else ["Other"]


def topics_addressed(report_text, min_hits=2):
    """Topics mentioned at least `min_hits` times in a report: a rough 'is it discussed' test."""
    return {name for name, pat in _PATTERNS if len(pat.findall(report_text or "")) >= min_hits}


# company -> (SASB industry, {SASB disclosure topic: [our topics that represent it]})
SASB = {
    "Amazon": ("E-Commerce (CG-EC)", {
        "Hardware infrastructure energy & water management": ["Energy", "Water & effluents"],
        "Data privacy & advertising standards": ["Customer privacy & data security"],
        "Data security": ["Customer privacy & data security"],
        "Employee recruitment, inclusion & performance": ["Diversity, equity & inclusion", "Employment & labour practices"],
        "Product packaging & distribution": ["Waste, packaging & circularity", "GHG emissions & air quality"],
    }),
    "Samsung": ("Hardware (TC-HW)", {
        "Product security": ["Customer privacy & data security"],
        "Employee diversity & inclusion": ["Diversity, equity & inclusion"],
        "Product lifecycle management": ["Waste, packaging & circularity", "Materials & sourcing"],
        "Supply chain management": ["Supplier social assessment", "Human rights & labour standards"],
        "Materials sourcing": ["Materials & sourcing"],
    }),
    "Apple": ("Hardware (TC-HW)", {
        "Product security": ["Customer privacy & data security"],
        "Employee diversity & inclusion": ["Diversity, equity & inclusion"],
        "Product lifecycle management": ["Waste, packaging & circularity", "Materials & sourcing"],
        "Supply chain management": ["Supplier social assessment", "Human rights & labour standards"],
        "Materials sourcing": ["Materials & sourcing"],
    }),
    "Microsoft": ("Software & IT Services (TC-SI)", {
        "Environmental footprint of hardware infrastructure": ["Energy", "Water & effluents", "GHG emissions & air quality"],
        "Data privacy & freedom of expression": ["Customer privacy & data security"],
        "Data security": ["Customer privacy & data security"],
        "Recruiting & managing a global, diverse & skilled workforce": ["Diversity, equity & inclusion", "Training & development"],
        "Intellectual property protection & competitive behaviour": ["Anti-corruption & business ethics"],
        "Managing systemic risks from technology disruptions": ["Climate risk & strategy (TCFD)"],
    }),
    "Unilever": ("Household & Personal Products (CG-HP)", {
        "Water management": ["Water & effluents"],
        "Product environmental, health & safety performance": ["Product & customer safety"],
        "Packaging lifecycle management": ["Waste, packaging & circularity"],
        "Environmental & social impacts of palm oil supply chain": ["Materials & sourcing", "Biodiversity & land use", "Human rights & labour standards"],
    }),
    "Nestle": ("Processed Foods (FB-PF)", {
        "Energy management": ["Energy"],
        "Water management": ["Water & effluents"],
        "Food safety": ["Product & customer safety"],
        "Health & nutrition / product labelling": ["Product & customer safety"],
        "Packaging lifecycle management": ["Waste, packaging & circularity"],
        "Environmental & social impacts of ingredient supply chain": ["Materials & sourcing", "Supplier social assessment", "Biodiversity & land use"],
    }),
    "Coca Cola": ("Non-Alcoholic Beverages (FB-NB)", {
        "Fleet fuel & energy management": ["Energy", "GHG emissions & air quality"],
        "Water management": ["Water & effluents"],
        "Health & nutrition / product labelling": ["Product & customer safety"],
        "Packaging lifecycle management": ["Waste, packaging & circularity"],
        "Environmental & social impacts of ingredient supply chain": ["Materials & sourcing", "Supplier social assessment"],
    }),
    "Shell": ("Oil & Gas – Exploration & Production (EM-EP)", {
        "Greenhouse gas emissions": ["GHG emissions & air quality"],
        "Air quality": ["GHG emissions & air quality"],
        "Water & wastewater management": ["Water & effluents"],
        "Biodiversity impacts": ["Biodiversity & land use"],
        "Security, human rights & rights of indigenous peoples": ["Human rights & labour standards"],
        "Community relations": ["Local communities & inclusion"],
        "Workforce health & safety": ["Occupational health & safety"],
        "Reserves valuation & capital expenditures": ["Climate risk & strategy (TCFD)"],
        "Business ethics & transparency": ["Anti-corruption & business ethics"],
        "Management of the legal & regulatory environment": ["Public policy & lobbying"],
        "Critical incident risk management": ["Occupational health & safety"],
    }),
    "HSBC": ("Commercial Banks (FN-CB)", {
        "Data security": ["Customer privacy & data security"],
        "Financial inclusion & capacity building": ["Local communities & inclusion"],
        "Incorporation of ESG factors in credit analysis": ["Climate risk & strategy (TCFD)"],
        "Business ethics": ["Anti-corruption & business ethics"],
        "Systemic risk management": ["Board structure & oversight", "Climate risk & strategy (TCFD)"],
    }),
    "Toyota Motor Corporation": ("Automobiles (TR-AU)", {
        "Product safety": ["Product & customer safety"],
        "Labour practices": ["Employment & labour practices", "Human rights & labour standards"],
        "Fuel economy & use-phase emissions": ["GHG emissions & air quality", "Energy"],
        "Materials sourcing": ["Materials & sourcing"],
        "Materials efficiency & recycling": ["Waste, packaging & circularity", "Materials & sourcing"],
    }),
    "Honda": ("Automobiles (TR-AU)", {
        "Product safety": ["Product & customer safety"],
        "Labour practices": ["Employment & labour practices", "Human rights & labour standards"],
        "Fuel economy & use-phase emissions": ["GHG emissions & air quality", "Energy"],
        "Materials sourcing": ["Materials & sourcing"],
        "Materials efficiency & recycling": ["Waste, packaging & circularity", "Materials & sourcing"],
    }),
}


def sasb_crosscheck(company, gap_topics, final_report_text):
    """For each SASB material topic: is it addressed in the final report, flagged as a gap, or neither?"""
    if company not in SASB:
        return None, []
    industry, topics = SASB[company]
    addressed = topics_addressed(final_report_text)
    rows = []
    for sasb_topic, ours in topics.items():
        is_addressed = any(t in addressed for t in ours)
        is_flagged = any(t in gap_topics for t in ours)
        if is_addressed and is_flagged:
            status = "addressed, gaps flagged"
        elif is_addressed:
            status = "addressed"
        elif is_flagged:
            status = "flagged as gap"
        else:
            status = "blind spot"
        rows.append({"sasb_topic": sasb_topic, "mapped_topics": "; ".join(ours),
                     "addressed_in_report": is_addressed, "flagged_as_gap": is_flagged, "status": status})
    return industry, rows
