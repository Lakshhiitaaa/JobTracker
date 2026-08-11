# 02 — Building `companies.xlsx`

This is the highest-leverage file in the project. Everything downstream depends
on the URLs you put here.

---

## The format

| Column | Required | Purpose |
|---|---|---|
| **Company Name** | Yes | Shown in the report and email. Also what `--company` matches against. |
| **Careers URL** | Yes | The page (or ATS board) to check. |
| Location | No | Your own note. **The code ignores this** — city filtering is `LOCATION_FILTER` in `config.py`. |
| ATS | No | Your own note. The code auto-detects; it doesn't read this column. |
| Status | No | Set to `Inactive` to skip a row. Any other value (or blank) = active. |

Example:

| Company Name | Careers URL | Location | ATS | Status |
|---|---|---|---|---|
| Postman | https://boards.greenhouse.io/postman | Bengaluru | greenhouse | Active |
| Hasura | https://jobs.lever.co/hasura | Bengaluru | lever | Active |
| Zepto | https://jobs.ashbyhq.com/zepto | Mumbai | ashby | Active |
| Zerodha | https://zerodha.com/careers/ | Bengaluru | none | Active |
| OldStartup | https://oldstartup.com/jobs | Pune | | Inactive |

Rules:
- Rows with a blank Careers URL are dropped automatically.
- Extra columns are ignored, so add your own notes freely.
- Column names must match exactly, including capitalisation.
- Keep the file **closed** while the script runs — Excel holds a lock.

---

## Why the URL matters so much

The scraper takes the first path that works:

```
1. Is this an ATS?  -> hit its JSON API        (reliable, gives full job description)
2. Plain HTML?      -> guess from <a> tags     (fragile, no description)
3. JavaScript page? -> Playwright, then guess  (slow, fragile, no description)
```

Path 1 is not just more reliable — it's the only path that returns the **job
description**, which is what the experience filter reads. Companies on paths 2
and 3 will mostly show `Not specified` in the Experience column, so senior roles
can slip through on title alone.

| | ATS JSON | HTML scrape |
|---|---|---|
| Survives a site redesign | Yes | No |
| Returns job description | Yes | No |
| Reliable experience filter | Yes | Title only |
| Speed | ~0.5s | 2–20s |
| Needs Playwright | No | Sometimes |

**Every company you move from path 2 to path 1 is a permanent win.**

---

## Supported ATS platforms

| ATS | URL you should put in the Excel |
|---|---|
| Greenhouse | `https://boards.greenhouse.io/<token>` |
| Lever | `https://jobs.lever.co/<token>` |
| Ashby | `https://jobs.ashbyhq.com/<token>` |
| SmartRecruiters | `https://careers.smartrecruiters.com/<token>` |
| Workable | `https://apply.workable.com/<token>` |
| Recruitee | `https://<token>.recruitee.com` |

`<token>` is the company's board slug — usually a lowercase version of their name.

**Detected but not yet supported:** Zoho Recruit and Keka are recognised by
`ats.py` but have no JSON client, so they fall back to HTML scraping. These are
common among Indian startups; see [08_ROADMAP.md](08_ROADMAP.md).

---

## How to find a company's ATS URL

### Method 1 — Look at where the careers page sends you

Open the company's careers page and click any job. Look at the address bar.
If it changes to `jobs.lever.co/...` or `boards.greenhouse.io/...`, you're done —
strip everything after the company token and use that.

### Method 2 — Search the page source (works for embedded boards)

Many companies embed the ATS in an iframe, so the address bar never changes.

1. Open the careers page in Chrome
2. Press `Ctrl+U` (view source)
3. Press `Ctrl+F` and search for each of these in turn:
   - `greenhouse`
   - `lever`
   - `ashby`
   - `smartrecruiters`
   - `workable`
   - `recruitee`
4. When you get a hit, read the company token out of the surrounding URL

### Method 3 — Check the network tab (JavaScript boards)

1. Open the careers page, press `F12` → **Network** tab
2. Filter to **Fetch/XHR**
3. Reload the page
4. Look for a request to an `api.` domain — the token is usually in the path

### Method 4 — Guess and verify

Paste one of these into your browser, replacing `<token>` with the company name
in lowercase, no spaces:

| ATS | Verification URL |
|---|---|
| Greenhouse | `https://boards-api.greenhouse.io/v1/boards/<token>/jobs` |
| Lever | `https://api.lever.co/v0/postings/<token>?mode=json` |
| Ashby | `https://api.ashbyhq.com/posting-api/job-board/<token>` |
| SmartRecruiters | `https://api.smartrecruiters.com/v1/companies/<token>/postings` |
| Workable | `https://apply.workable.com/api/v1/widget/accounts/<token>` |
| Recruitee | `https://<token>.recruitee.com/api/offers/` |

If you see JSON full of job titles, the token is correct. If you see a 404, try
another ATS or another spelling.

> This is the fastest way to check before adding a row. It takes about 15 seconds
> per company and saves you a failed scrape every single day.

---

## Worked example

You want to track **Razorpay**.

1. Open `https://razorpay.com/careers/` — jobs are listed but clicking one keeps
   you on the same domain. Address bar is no help.
2. `Ctrl+U`, search `greenhouse` — no hit. Search `lever` — no hit. Search
   `smartrecruiters` — hit, and the surrounding URL contains a token.
3. Verify: paste `https://api.smartrecruiters.com/v1/companies/<token>/postings`
   into the browser. JSON with job titles appears.
4. Add the row:

| Company Name | Careers URL | Location | ATS | Status |
|---|---|---|---|---|
| Razorpay | https://careers.smartrecruiters.com/`<token>` | Bengaluru | smartrecruiters | Active |

5. Test just that company:

```bash
python main.py --dry-run --company razorpay
```

Expected: `[1/1] Razorpay   4 match  (smartrecruiters)`

---

## When there's genuinely no ATS

Some startups run a hand-built careers page. Options, in order of preference:

1. **Use the ATS anyway if they have one for a subsidiary or a different region.**
2. **Leave it on HTML scraping.** It works when the page is server-rendered and
   the job links contain words like `job`, `career`, `opening`, or `position`.
   Test with `--dry-run --company <name>` and see what comes back.
3. **Let Playwright handle it.** Automatic when static HTML yields fewer than 2
   jobs. Slow, but it works on React-rendered pages.
4. **Mark it `Inactive`.** If a company fails three runs in a row and you can't
   find a better URL, park it. A permanently failing row costs you 20 seconds of
   runtime every single day for nothing.

---

## Scaling to 50–200 companies

**Build in batches of 10.** Add 10, run `--dry-run`, fix what fails, then add
the next 10. Adding 150 rows at once gives you an Errors sheet you'll never
work through.

**Runtime estimate.** With `MAX_WORKERS = 8`:

| Company mix | 100 companies |
|---|---|
| Mostly ATS | ~1 minute |
| Half ATS, half HTML | ~3 minutes |
| Mostly Playwright | ~10+ minutes |

Another reason to chase ATS URLs.

**Where to find startups to add:**
- Y Combinator company directory
- Portfolio pages of Indian VCs (Accel, Blume, Elevation, Peak XV)
- LinkedIn — when you find a company you like, go straight to their careers page
- Wellfound / AngelList
- Tracxn and Crunchbase lists

---

## Maintenance routine

Every two weeks:

1. Open the latest report's **Errors** sheet.
2. For each failing company, retry Method 2 above — many switch ATS over time.
3. Mark repeat offenders `Inactive`.
4. Spot-check a few companies showing `0 match` — a company that used to return
   jobs and now returns zero usually means their page changed, not that they
   stopped hiring.
