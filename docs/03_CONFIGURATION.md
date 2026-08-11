# 03 — Configuration

Everything tunable lives in `config.py`. No other file needs editing for normal
use.

Settings that come from environment variables are marked **env**. Those are read
**when `config.py` is imported**, so export them before launching Python.

---

## Files

| Setting | Default | Env var | Notes |
|---|---|---|---|
| `COMPANIES_FILE` | `companies.xlsx` | `JT_COMPANIES` | Input list. Overridable per-run with `--companies`. |
| `REPORTS_DIR` | `reports` | `JT_REPORTS` | Created if missing. One file per run day. |
| `DB_FILE` | `jobs.db` | `JT_DB` | Dedupe memory. **Deleting this makes every job "new" again.** |

---

## Filtering

This is where you'll spend your tuning time.

### `INCLUDE_KEYWORDS`

A job title must contain at least one of these (case-insensitive substring) to
be considered at all.

Ships with: software, developer, engineer, sde, programmer, java, python,
golang, node, react, javascript, typescript, backend, frontend, full stack, qa,
quality assurance, test, testing, sdet, automation, api, devops, sre, platform,
ai, ml, machine learning, data engineer, android, ios, mobile, flutter,
graduate engineer, trainee, intern.

> Watch for short entries. `"ai "` and `"ml "` include a trailing space on
> purpose — without it, `"ai"` matches *Retail*, *Maintenance*, and *Email*.
> The title is padded with spaces before matching, so a leading or trailing
> space in your keyword is a word-boundary trick. Use it for any keyword under
> 4 characters.

### `EXCLUDE_TITLE_KEYWORDS`

If the title contains any of these, the job is dropped — **even if it matched an
include keyword**. Exclusion always wins.

Two jobs at once:

- **Seniority guard:** senior, sr., staff, principal, lead, team lead, tech lead,
  manager, director, head of, vp, vice president, chief, architect, iii, iv,
  level 3, l3, l4, l5
- **Department guard:** sales, marketing, recruiter, hr, finance, account executive

This is your primary noise control. When something irrelevant shows up in the
report, add a distinctive word from its title here.

> Careful with short entries. `" iii"` has a leading space so it doesn't match
> inside other words. If you add `"lead"` without a trailing space it will also
> kill *Leadership Development* — and note the shipped default is `"lead "`.

### `FRESHER_HINTS`

Phrases that mark a role as fresher-friendly when **no explicit year count**
appears in the description: fresher, freshers, recent graduate, new graduate,
new grad, 0-1 year, 0-2 year, 0 to 2 year, 1-2 year, no prior experience,
entry level, entry-level, campus hire, graduate trainee.

A hit here sets the parsed experience to 0 years.

### `MAX_YEARS_EXPERIENCE`

Default `2`. Jobs whose parsed minimum experience exceeds this are dropped.

A description saying "3-5 years" parses as a minimum of 3 → dropped at the
default. "0-2 years" parses as 0 → kept.

### `KEEP_IF_EXPERIENCE_UNKNOWN`

Default `True`.

| Value | Behaviour |
|---|---|
| `True` | Keep jobs where no year count could be parsed. Experience column shows `Not specified`. |
| `False` | Drop them. |

Keep it `True` while your list is HTML-heavy — those companies never supply a
description, so `False` would filter out almost everything. Switch to `False`
once most of your list is on ATS URLs and you're drowning in results.

### `LOCATION_FILTER`

Default `[]` — accept everything.

Fill it with lowercase substrings to restrict by city:

```python
LOCATION_FILTER = ["bengaluru", "bangalore", "remote", "hyderabad", "pune"]
```

Match is a case-insensitive substring against the location string the ATS
returns. Include **both** spellings of Bengaluru/Bangalore — companies use both.

> Jobs from HTML-scraped pages often have a blank location, and a blank location
> **fails** the filter. Turning this on will silently drop your non-ATS
> companies. Prefer leaving it empty and filtering in Excel.

---

## Runtime

| Setting | Default | Notes |
|---|---|---|
| `MAX_WORKERS` | `8` | Companies checked in parallel. 8–12 is sane for 50–200 companies. Higher risks rate limiting. |
| `REQUEST_TIMEOUT` | `20` | Seconds before an HTTP request gives up. |
| `USE_PLAYWRIGHT` | `True` | Set `False` to skip the browser fallback entirely — much faster, but JavaScript career pages return nothing. |
| `PLAYWRIGHT_TIMEOUT` | `25000` | Milliseconds. Raise to 40000 for slow sites. |
| `USER_AGENT` | Chrome 124 string | Sent on every request. Some sites reject the default `python-requests` UA. |
| `POLITE_DELAY` | `0.5` | Seconds paused after a Playwright render. |

> Playwright runs a real Chromium per company. At `MAX_WORKERS = 8` that can be
> 8 browsers at once. If your machine struggles, lower `MAX_WORKERS` rather than
> disabling Playwright.

---

## Email

| Setting | Default | Env var | Notes |
|---|---|---|---|
| `SMTP_HOST` | `smtp.gmail.com` | `SMTP_HOST` | |
| `SMTP_PORT` | `465` | `SMTP_PORT` | SSL port. The code uses `SMTP_SSL`, so use the SSL port, not the STARTTLS one. |
| `SMTP_USER` | *(empty)* | `SMTP_USER` | Your email address. |
| `SMTP_PASSWORD` | *(empty)* | `SMTP_PASSWORD` | **App Password**, not your login password. |
| `EMAIL_FROM` | falls back to `SMTP_USER` | `EMAIL_FROM` | |
| `EMAIL_TO` | *(empty)* | `EMAIL_TO` | Comma-separated: `a@x.com,b@y.com` |
| `EMAIL_SUBJECT` | `New Fresher Software Jobs - {date} ({count} new)` | | `{date}` and `{count}` are substituted. |
| `SEND_EMAIL_WHEN_NO_NEW_JOBS` | `False` | | `True` sends a "nothing today" email so you know the job ran. |

Provider settings:

| Provider | Host | SSL port |
|---|---|---|
| Gmail | `smtp.gmail.com` | 465 |
| Outlook / Office 365 | `smtp.office365.com` | 587 — needs STARTTLS, **code change required** |
| Zoho Mail | `smtp.zoho.in` | 465 |
| SendGrid | `smtp.sendgrid.net` | 465 (user is literally `apikey`) |

> `email_sender.py` uses `smtplib.SMTP_SSL`. Outlook's port 587 is STARTTLS and
> will not work without switching to `smtplib.SMTP` plus `starttls()`.

---

## Tuning recipes

**Too many results, mostly irrelevant**
```python
KEEP_IF_EXPERIENCE_UNKNOWN = False
MAX_YEARS_EXPERIENCE = 1
```
Plus add offending words to `EXCLUDE_TITLE_KEYWORDS`.

**Too few results**
```python
MAX_YEARS_EXPERIENCE = 3
KEEP_IF_EXPERIENCE_UNKNOWN = True
LOCATION_FILTER = []
```
Also check the Errors sheet — "too few" is usually broken URLs, not filtering.

**QA / SDET roles only**
```python
INCLUDE_KEYWORDS = ["qa", "quality assurance", "sdet", "test engineer",
                    "testing", "automation engineer", "test automation"]
```

**Internships only**
```python
INCLUDE_KEYWORDS = ["intern", "internship", "trainee", "graduate engineer"]
```

**Run fast, skip the browser**
```python
USE_PLAYWRIGHT = False
MAX_WORKERS = 12
```

---

## After every config change

```bash
python main.py --selftest
python main.py --dry-run --limit 10
```

The selftest asserts specific behaviour (e.g. that "Senior Software Engineer" is
rejected). If you rewrite `EXCLUDE_TITLE_KEYWORDS` and a test fails, the test is
telling you that you removed something load-bearing.
