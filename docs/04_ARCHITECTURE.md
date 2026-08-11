# 04 — Architecture

---

## Data flow

```
companies.xlsx
      |
      | pandas.read_excel, drop blank URLs, drop Status=Inactive
      v
  [ ThreadPoolExecutor, MAX_WORKERS=8 ]
      |
      +--> for each company: scraper.scrape(url)
      |         |
      |         |  1. GET the page
      |         |  2. ats.detect(url, html)
      |         |
      |         +-- ATS found ------> ats.fetch()  -> JSON API
      |         |                     title, location, url, DESCRIPTION
      |         |
      |         +-- >=2 links -------> extract_links()  -> HTML guess
      |         |                     title, location, url, (no description)
      |         |
      |         +-- otherwise -------> Playwright render -> retry both
      |
      v
  filters.evaluate(job)
      |  title include-match?  -> no: drop
      |  seniority blocklist?  -> hit: drop
      |  location filter?      -> fail: drop
      |  parse years from description
      |     > MAX_YEARS         -> drop
      |     unparseable         -> keep or drop per KEEP_IF_EXPERIENCE_UNKNOWN
      |  attach category + experience label
      v
  database.upsert(job)  -> returns is_new (True = never seen before)
      v
  excel_report.build()  -> reports/jobs_YYYY-MM-DD.xlsx   (ALL matches)
      v
  email_sender.send()   -> only the NEW jobs, Excel attached
```

The Excel report always contains every currently-live matching job. The email
contains only what's new. That way the spreadsheet is a complete picture and the
email is never repetitive.

---

## Design decisions

### 1. ATS-first, HTML second

The original design treated ATS support as a future enhancement and generic
scraping as the primary path. That is backwards.

Arbitrary career pages share no structure. A generic parser must guess which
`<a>` tags are jobs, and that guess breaks on every redesign. Meanwhile roughly
70–80% of startups host jobs on Greenhouse, Lever, Ashby, SmartRecruiters,
Workable, or Recruitee — all of which expose **public, unauthenticated JSON
endpoints**.

Consequences:

| | ATS JSON | HTML |
|---|---|---|
| Breaks on redesign | No | Yes |
| Job description available | Yes | No |
| Needs a browser | No | Sometimes |
| Requests per company | 1 | 1–2 + render |

The description matters more than it first appears — it's the only place
experience requirements are stated, so it's the difference between real
filtering and title-keyword guessing.

`ats.detect()` checks the URL **and** the page HTML, because many companies
embed their ATS in an iframe on their own domain. So `hasura.io/careers` can
still resolve to the Lever API.

### 2. Experience parsed from description, not title

`filters.extract_experience()` runs four regex families over the first 6000
characters of the description:

| Pattern | Matches |
|---|---|
| `(\d+)\s*(\+|plus)\s*...(years|yrs)` | "5+ years", "3 plus years" |
| `(\d+)\s*[-–—to]{1,3}\s*(\d+)\s*(years|yrs)` | "0-2 years", "2 to 4 yrs" |
| `(minimum|min\.?|at least|atleast|over)\s*(\d+)\s*(years|yrs)` | "minimum 3 years" |
| `(\d+)\s*(years|yrs)\s*(of)?\s*...experience` | "4 years of relevant experience" |

All matches are collected and the **lowest** number wins. A JD saying "0-2 years
required, 5 years preferred" is treated as 0 — correct, since the hard
requirement is what gates the application.

If nothing matches, `FRESHER_HINTS` phrases are checked; a hit means 0 years.
If still nothing, the result is `None` and `KEEP_IF_EXPERIENCE_UNKNOWN` decides.

Capped at 6000 characters because ATS descriptions include boilerplate about
benefits and company history, and "founded 12 years ago" is a false positive
waiting to happen.

### 3. Dedupe key

`database.make_key()`:

1. If a usable apply URL exists (>15 chars), strip the query string and trailing
   slash, lowercase it, and MD5 that.
2. Otherwise MD5 `company|title|location`, whitespace-normalised and lowercased.

The query string is stripped because the same posting arrives with different
tracking parameters (`?src=linkedin`, `?gh_src=...`) and would otherwise look
new every day. The selftest asserts this.

The fallback exists because HTML-scraped pages sometimes yield no stable link.
It's weaker — a retitled job counts as new — but it's rare.

### 4. No scheduler module

The original design listed `scheduler.py` using the `schedule` library. That
requires a Python process running 24/7, which means it silently dies on reboot
and you don't find out for a week.

Cron, Windows Task Scheduler, and GitHub Actions all solve this at the OS level,
survive reboots, and log failures. See [06_DEPLOYMENT.md](06_DEPLOYMENT.md).

### 5. Threading, not async

`ThreadPoolExecutor` with 8 workers. The workload is I/O-bound network calls, so
threads are sufficient, and `requests` + Playwright's sync API are both
blocking-friendly. Async would add complexity for no meaningful gain at this
scale.

Each company is fully independent. One company raising an exception is caught in
`main.run()`, recorded in the errors list, and the rest continue. One bad URL
never kills a run.

---

## Modules

| Module | Responsibility | Depends on |
|---|---|---|
| `config.py` | All settings. No logic. | — |
| `ats.py` | Detect ATS from URL/HTML; call its JSON API | `config` |
| `scraper.py` | Orchestrate ATS → HTML → Playwright; generic link extraction | `config`, `ats` |
| `filters.py` | Title matching, experience parsing, categorisation | `config` |
| `database.py` | SQLite schema, dedupe key, upsert, run log | `config` |
| `excel_report.py` | Formatted xlsx writer | `config` |
| `email_sender.py` | Build HTML email, attach, send via SMTP | `config` |
| `main.py` | CLI, load companies, threading, wire it together, selftest | all |

Dependency direction is one-way — nothing imports `main`, and `config` imports
nothing. No circular imports.

---

## Database schema

```sql
CREATE TABLE jobs (
    job_key      TEXT PRIMARY KEY,   -- MD5, see make_key()
    company      TEXT,
    title        TEXT,
    category     TEXT,               -- Backend / Frontend / QA-SDET / ...
    experience   TEXT,               -- human label, e.g. "0-2 years"
    location     TEXT,
    apply_link   TEXT,
    careers_page TEXT,
    first_seen   TEXT,               -- ISO date. The "Date Found" column.
    last_seen    TEXT                -- ISO date, refreshed every run
);
CREATE INDEX idx_first_seen ON jobs(first_seen);

CREATE TABLE runs (
    run_date   TEXT,
    companies  INTEGER,
    jobs_found INTEGER,
    new_jobs   INTEGER,
    errors     INTEGER
);
```

`last_seen` is refreshed on every sighting, so a job that stops appearing has a
stale `last_seen` — that's how you'd detect closed positions later.

`runs` gives you a history for free. Useful queries:

```sql
-- how many new jobs per day
SELECT run_date, new_jobs FROM runs ORDER BY run_date DESC LIMIT 30;

-- which companies post the most fresher roles
SELECT company, COUNT(*) c FROM jobs GROUP BY company ORDER BY c DESC LIMIT 20;

-- jobs added this week
SELECT company, title, apply_link FROM jobs WHERE first_seen >= date('now','-7 day');

-- likely-closed postings
SELECT company, title FROM jobs WHERE last_seen < date('now','-14 day');
```

Open `jobs.db` with [DB Browser for SQLite](https://sqlitebrowser.org/) to poke
around.

---

## Output format

`reports/jobs_YYYY-MM-DD.xlsx`

**Sheet "Jobs"** — columns: Company, Job Title, Category, Experience, Location,
Date Found, Apply Link, Careers Page, New Today.

- New rows sorted to the top and shaded light green
- Apply Link is a live hyperlink
- Header row frozen, autofilter enabled on all columns

**Sheet "Errors"** — only present when something failed. Columns: Company,
Careers URL, Error (first 300 chars).

One file per day. Re-running on the same day overwrites it.

---

## Failure behaviour

| Failure | Result |
|---|---|
| One company unreachable | Logged to Errors sheet, run continues |
| ATS API returns garbage | Caught, falls through to HTML scraping |
| Playwright not installed | That company errors; ATS companies unaffected |
| No new jobs | Report still written, email skipped |
| SMTP credentials missing | `RuntimeError` **after** the report is written — you keep the xlsx |
| `companies.xlsx` open in Excel | Read may fail — close the file |
| `companies.xlsx` missing a required column | `ValueError` naming the column, run aborts |
