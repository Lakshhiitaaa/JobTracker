# 05 — Module Reference

Function-level reference for editing the code.

Job dictionaries are passed between modules. The shape grows as it flows:

```python
# produced by ats.py / scraper.py
{"title": str, "location": str, "url": str, "description": str}

# after filters.evaluate()
{..., "experience": str, "min_years": int|None, "category": str}

# after main.process()
{..., "company": str, "careers_page": str, "source": str}

# after main.run()
{..., "is_new": bool, "date_found": str}
```

---

## `ats.py`

**`ATS_PATTERNS: dict[str, str]`**
Regex per ATS, each with one capture group for the company token. Includes
`zohorecruit` and `keka`, which are detected but have no client.

**`detect(url: str, html: str = "") -> tuple[str|None, str|None]`**
Returns `(ats_name, token)` or `(None, None)`. Checks `url` first, then `html`.
Case-insensitive. First match wins, so dict order matters if a page mentions two.

**`fetch(ats: str, token: str) -> list[dict]`**
Dispatches to the right client. Raises `NotImplementedError` for a detected-but-
unsupported ATS.

**Clients:** `greenhouse`, `lever`, `ashby`, `smartrecruiters`, `workable`,
`recruitee` — each `(token) -> list[dict]` with keys `title, location, url,
description`. Registered in `CLIENTS`.

**`_get(url, **kw) -> dict`** — GET with the configured UA and timeout,
`raise_for_status()`, return JSON.

**`_strip(html) -> str`** — crude tag stripper for HTML descriptions.

### Adding a new ATS

```python
# 1. pattern
ATS_PATTERNS["newats"] = r"jobs\.newats\.com/([A-Za-z0-9_-]+)"

# 2. client
def newats(tok):
    d = _get(f"https://api.newats.com/v1/{tok}/jobs")
    return [{"title": j["name"],
             "location": j.get("city", ""),
             "url": j["applyUrl"],
             "description": _strip(j.get("body", ""))} for j in d["results"]]

# 3. register
CLIENTS["newats"] = newats
```

Add a detection assertion to `main.selftest()` while you're there.

---

## `scraper.py`

**`scrape(url: str) -> tuple[list[dict], str]`**
The only function `main` calls. Returns `(jobs, source_label)` where the label is
an ATS name, `"html"`, or `"playwright"`. Order: GET → `ats.detect` → `ats.fetch`
→ `extract_links` (accepted if ≥2 jobs) → Playwright render → detect/fetch again
→ `extract_links`. Raises `RuntimeError` if Playwright fails.

**`fetch_html(url) -> str`** — plain `requests.get`, raises on HTTP error.

**`fetch_html_playwright(url) -> str`** — headless Chromium, waits for
`networkidle` plus 1.5s, returns rendered HTML. Browser always closed in `finally`.

**`extract_links(html, base_url) -> list[dict]`**
Every `<a href>` where the text is 5–120 chars, isn't a `NOISE` word
(apply/view/learn more/home/...), and where either the href or the text matches
`JOB_HREF` (`job|career|position|opening|vacanc|role|apply|posting`). Relative
URLs resolved via `urljoin`. Location guessed by regexing the nearest
`li`/`div`/`tr`/`article` ancestor for Indian city names — extend that list for
other regions.

Descriptions are always empty on this path.

---

## `filters.py`

**`evaluate(job: dict) -> tuple[bool, dict, str]`**
The main entry point. Returns `(keep, enriched_job, reason)`. Reasons:
`"ok"`, `"title-mismatch"`, `"location"`, `"experience-unknown"`,
`"experience>N"`. The input dict is copied, not mutated.

**`title_matches(title) -> bool`**
Pads the lowercased title with spaces, requires an `INCLUDE_KEYWORDS` hit and no
`EXCLUDE_TITLE_KEYWORDS` hit. Exclusion wins.

**`extract_experience(text) -> tuple[int|None, str]`**
Returns `(min_years, matched_snippet)`. Lowest match across all four regex
families wins. Falls back to `FRESHER_HINTS` (returns 0). Returns `(None, "")` if
nothing found. Reads the first 6000 chars only.

**`categorize(title) -> str`**
First match in `CATEGORY_RULES`, else `"Software (General)"`. Order matters —
QA is checked before Backend so "QA Automation Java Engineer" lands in QA.
Categories: QA / SDET, DevOps / SRE, AI / ML, Data, Mobile, Full Stack,
Frontend, Backend, Intern, Software (General).

**`location_ok(location) -> bool`**
`True` when `LOCATION_FILTER` is empty. Otherwise case-insensitive substring
match. **A blank location fails a non-empty filter.**

---

## `database.py`

**`make_key(company, title, location, url) -> str`**
MD5. Prefers the URL with query string and trailing slash stripped; falls back to
`company|title|location` normalised.

**`DB(path=None)`** — opens the connection and applies the schema idempotently.

**`DB.upsert(job) -> bool`**
`True` if newly inserted, `False` if already known (in which case `last_seen` is
bumped). Does not commit — `log_run()` and `close()` do.

**`DB.log_run(companies, found, new, errors)`** — appends to `runs` and commits.

**`DB.commit()` / `DB.close()`** — `close()` commits first.

> The connection is created on the main thread and used only after the thread
> pool has finished, so the default `check_same_thread=True` is safe. If you ever
> move `upsert` inside a worker, you'll need per-thread connections or a lock.

---

## `excel_report.py`

**`build(rows, errors=None, out_dir=None) -> str`**
Writes `reports/jobs_YYYY-MM-DD.xlsx`, returns the path. Creates the directory if
needed. Sorts new jobs first, then by company. Applies header fill `1F3864`,
new-row fill `DFF5E1`, thin borders, frozen header, autofilter, and a live
hyperlink on Apply Link. Adds an "Errors" sheet only when `errors` is truthy.

`COLUMNS` and `WIDTHS` are parallel lists — change both together.

---

## `email_sender.py`

**`send(new_jobs, attachment_path, stats) -> True`**
`stats` is `{"companies": int, "found": int, "errors": int}`. Raises
`RuntimeError` if `SMTP_USER`, `SMTP_PASSWORD`, or `EMAIL_TO` is unset. Builds a
plain-text and HTML alternative, attaches the xlsx if it exists, sends over
`SMTP_SSL`.

**`_table(jobs, limit=25) -> str`** — HTML table of the first 25 new jobs with a
"+N more" line. All values HTML-escaped.

---

## `main.py`

**`load_companies(path=None) -> list[dict]`**
Reads the Excel, strips column names, raises `ValueError` if `Company Name` or
`Careers URL` is missing, drops `Status == "inactive"` rows and blank URLs.

**`process(company) -> tuple[str, list[dict], str]`**
Runs in a worker thread. Scrapes one company, filters, stamps `company`,
`careers_page`, and `source` onto each surviving job.

**`run(args)`**
Loads, applies `--company` then `--limit`, fans out over the thread pool,
collects results and errors, upserts (unless `--dry-run`), builds the report,
sends the email unless suppressed.

**`init_sample(path)`** — writes the 4-row starter Excel.

**`selftest() -> int`** — ~20 offline assertions across filters, ATS detection,
database, and Excel. Returns 0 on success, 1 on any failure. Add a `chk()` line
whenever you add behaviour.

**`ats_check(url, exp_name, exp_tok) -> bool`** — selftest helper.

---

## Extension points

| Want to... | Touch |
|---|---|
| Support a new ATS | `ats.ATS_PATTERNS` + a client + `CLIENTS` |
| Change what counts as a match | `config.INCLUDE_KEYWORDS` / `EXCLUDE_TITLE_KEYWORDS` |
| Add a job category | `filters.CATEGORY_RULES` |
| Add a report column | `excel_report.COLUMNS` + `WIDTHS` + the `ws.append` call |
| Send to Telegram/Slack instead | New module mirroring `email_sender.send()`; call it from `run()` |
| Score jobs against your resume | New module after `filters.evaluate`, add a column |
| Detect closed postings | Query `jobs` where `last_seen` is stale |
