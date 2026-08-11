"""Title/experience filtering. Decides: is this a fresher software job?"""
import re, config

_YEARS = [
    re.compile(r"(\d{1,2})\s*(?:\+|plus)\s*(?:to\s*\d{1,2}\s*)?(?:years?|yrs?)", re.I),
    re.compile(r"(\d{1,2})\s*[-–—to]{1,3}\s*(\d{1,2})\s*(?:years?|yrs?)", re.I),
    re.compile(r"(?:minimum|min\.?|at least|atleast|over)\s*(?:of\s*)?(\d{1,2})\s*(?:years?|yrs?)", re.I),
    re.compile(r"(\d{1,2})\s*(?:years?|yrs?)\s*(?:of\s*)?(?:relevant\s*|professional\s*|work\s*)?experience", re.I),
]

CATEGORY_RULES = [
    ("QA / SDET",     ["sdet", "qa", "quality assurance", "test engineer", "testing", "automation engineer"]),
    ("DevOps / SRE",  ["devops", "sre", "site reliability", "infrastructure", "platform engineer", "cloud engineer"]),
    ("AI / ML",       ["machine learning", "ml engineer", "ai engineer", "data scientist",
                       "nlp", "deep learning", "ai scientist", "applied ai", "ai research", "llm"]),
    ("Data",          ["data engineer", "analytics engineer", "etl"]),
    ("Mobile",        ["android", "ios", "mobile", "flutter", "react native"]),
    ("Full Stack",    ["full stack", "fullstack", "full-stack"]),
    ("Frontend",      ["frontend", "front end", "front-end", "react", "angular", "vue", "ui engineer"]),
    ("Backend",       ["backend", "back end", "back-end", "java", "python", "golang", "node", "api engineer"]),
    ("Intern",        ["intern", "internship"]),
]


def extract_experience(text: str):
    """Return (min_years or None, raw_snippet or '')."""
    if not text:
        return None, ""
    t = text[:6000].lower()
    found = []
    for pat in _YEARS:
        for m in pat.finditer(t):
            try:
                found.append((int(m.group(1)), m.group(0).strip()))
            except (ValueError, IndexError):
                pass
    if not found:
        for hint in config.FRESHER_HINTS:
            if hint in t:
                return 0, hint
        return None, ""
    found.sort(key=lambda x: x[0])
    return found[0]


def categorize(title: str) -> str:
    t = (title or "").lower()
    for cat, keys in CATEGORY_RULES:
        if any(k in t for k in keys):
            return cat
    return "Software (General)"


def title_matches(title: str) -> bool:
    t = f" {(title or '').lower()} "
    if not any(k in t for k in config.INCLUDE_KEYWORDS):
        return False
    if any(k in t for k in config.EXCLUDE_TITLE_KEYWORDS):
        return False
    return True


def location_ok(location: str) -> bool:
    l = (location or "").strip().lower()
    if not l:
        return getattr(config, "ALLOW_BLANK_LOCATION", True)
    # explicit foreign blocklist wins over everything, whole-word matched so
    # "us" doesn't fire inside "Austin" and "india" doesn't fire in "Indiana"
    for bad in getattr(config, "EXCLUDE_LOCATIONS", []):
        if re.search(r"\b" + re.escape(bad) + r"\b", l):
            return False
    if not config.LOCATION_FILTER:
        return True
    return any(f.lower() in l for f in config.LOCATION_FILTER)


def evaluate(job: dict):
    """Return (keep: bool, enriched_job: dict, reason: str)."""
    title = job.get("title", "")
    if not title_matches(title):
        return False, job, "title-mismatch"
    if not location_ok(job.get("location", "")):
        return False, job, "location"

    yrs, snippet = extract_experience(job.get("description", "") or title)
    if yrs is None:
        if not config.KEEP_IF_EXPERIENCE_UNKNOWN:
            return False, job, "experience-unknown"
        exp_label = "Not specified"
    elif yrs > config.MAX_YEARS_EXPERIENCE:
        return False, job, f"experience>{config.MAX_YEARS_EXPERIENCE}"
    else:
        exp_label = snippet or f"{yrs}+ years"

    job = dict(job)
    job["experience"] = exp_label
    job["min_years"] = yrs
    job["category"] = categorize(title)
    return True, job, "ok"
