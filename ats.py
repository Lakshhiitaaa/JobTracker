"""ATS detection + JSON API clients.

This is the reliable path: ~70-80% of startups host jobs on an ATS that
exposes a public JSON endpoint. No HTML parsing, no Playwright, no breakage.
"""
import re, requests, config

HEADERS = {"User-Agent": config.USER_AGENT}

ATS_PATTERNS = {
    "greenhouse":      r"(?:boards|job-boards|boards-api)\.greenhouse\.io/(?:embed/job_board\?for=)?([A-Za-z0-9_-]+)",
    "lever":           r"jobs\.lever\.co/([A-Za-z0-9_-]+)",
    "ashby":           r"jobs\.ashbyhq\.com/([A-Za-z0-9_.-]+)",
    "smartrecruiters": r"careers\.smartrecruiters\.com/([A-Za-z0-9_-]+)",
    "workable":        r"apply\.workable\.com/([A-Za-z0-9_-]+)",
    "recruitee":       r"([A-Za-z0-9_-]+)\.recruitee\.com",
    "zohorecruit":     r"([A-Za-z0-9_-]+)\.zohorecruit\.(?:com|in|eu)",
    "keka":            r"([A-Za-z0-9_-]+)\.keka\.com/careers",
}


def detect(url: str, html: str = "") -> tuple:
    """Return (ats_name, token) or (None, None). Checks the URL first, then
    the page HTML (many companies iframe/redirect to their ATS)."""
    for blob in (url or "", html or ""):
        for name, pat in ATS_PATTERNS.items():
            m = re.search(pat, blob, re.I)
            if m:
                return name, m.group(1)
    return None, None


def _get(url, **kw):
    r = requests.get(url, headers=HEADERS, timeout=config.REQUEST_TIMEOUT, **kw)
    r.raise_for_status()
    return r.json()


def _strip(html):
    return re.sub(r"<[^>]+>", " ", html or "").replace("&nbsp;", " ")


# ---------- per-ATS clients: each returns [{title, location, url, description}] ----------

def greenhouse(tok):
    d = _get(f"https://boards-api.greenhouse.io/v1/boards/{tok}/jobs?content=true")
    return [{"title": j.get("title", ""),
             "location": (j.get("location") or {}).get("name", ""),
             "url": j.get("absolute_url", ""),
             "description": _strip(j.get("content", ""))} for j in d.get("jobs", [])]


def lever(tok):
    d = _get(f"https://api.lever.co/v0/postings/{tok}?mode=json")
    return [{"title": j.get("text", ""),
             "location": (j.get("categories") or {}).get("location", ""),
             "url": j.get("hostedUrl", ""),
             "description": j.get("descriptionPlain", "") or _strip(j.get("description", ""))}
            for j in d]


def ashby(tok):
    d = _get(f"https://api.ashbyhq.com/posting-api/job-board/{tok}?includeCompensation=false")
    return [{"title": j.get("title", ""), "location": j.get("location", ""),
             "url": j.get("jobUrl", ""),
             "description": _strip(j.get("descriptionHtml", ""))} for j in d.get("jobs", [])]


def smartrecruiters(tok):
    d = _get(f"https://api.smartrecruiters.com/v1/companies/{tok}/postings?limit=100")
    out = []
    for j in d.get("content", []):
        loc = j.get("location") or {}
        out.append({"title": j.get("name", ""),
                    "location": ", ".join(x for x in [loc.get("city"), loc.get("country")] if x),
                    "url": j.get("ref", "") or f"https://jobs.smartrecruiters.com/{tok}/{j.get('id')}",
                    "description": j.get("jobAd", {}).get("sections", {}).get("jobDescription", {}).get("text", "")})
    return out


def workable(tok):
    d = _get(f"https://apply.workable.com/api/v1/widget/accounts/{tok}?details=true")
    return [{"title": j.get("title", ""), "location": j.get("location", {}).get("location_str", ""),
             "url": j.get("url", ""), "description": _strip(j.get("description", ""))}
            for j in d.get("jobs", [])]


def recruitee(tok):
    d = _get(f"https://{tok}.recruitee.com/api/offers/")
    return [{"title": j.get("title", ""), "location": j.get("location", ""),
             "url": j.get("careers_url", ""), "description": _strip(j.get("description", ""))}
            for j in d.get("offers", [])]


CLIENTS = {"greenhouse": greenhouse, "lever": lever, "ashby": ashby,
           "smartrecruiters": smartrecruiters, "workable": workable, "recruitee": recruitee}


def fetch(ats: str, token: str):
    """Fetch jobs for a detected ATS. Raises NotImplementedError if unsupported."""
    fn = CLIENTS.get(ats)
    if not fn:
        raise NotImplementedError(f"{ats} has no JSON client yet")
    return fn(token)
