# 08 — Roadmap

Ordered by value-per-hour. Don't build anything here until the base pipeline has
been emailing you reliably for a week.

---

## Phase 1 — Coverage (do these first)

### Zoho Recruit and Keka clients
`ats.py` already *detects* both but has no client, so they fall through to HTML
scraping. Both are common among Indian startups, so this is the highest-value
addition for your list.

Add a client function and register it in `CLIENTS` — see the recipe in
[05_MODULE_REFERENCE.md](05_MODULE_REFERENCE.md).

### Workday and Freshteam
Workday is heavily used by larger Indian companies. Its API is POST-based with a
JSON body rather than a simple GET, so it needs slightly different handling.

### Auto-discover the ATS URL
Right now you find ATS URLs by hand. A helper could take a plain careers URL,
fetch it, run `ats.detect()` against the HTML, and print the ATS board URL to
paste into your Excel:

```bash
python discover.py https://razorpay.com/careers/
# -> smartrecruiters : https://careers.smartrecruiters.com/<token>
```

Half an hour of work that saves hours of manual URL hunting.

---

## Phase 2 — Better filtering

### Detail-page fetch for HTML companies
For non-ATS companies you have a job URL but no description. Fetching each job
page and running `extract_experience` on it would fix the `Not specified` problem.
Costs one request per job — cache aggressively and only do it for jobs that pass
the title filter.

### LLM relevance scoring
Regex filtering handles the clear cases. A cheap model call on title + first 500
chars of the description could score fresher-suitability 0–10 and add a column,
catching phrasings the regex misses ("early career", "for those starting out").

Batch all of a day's new jobs into one call rather than one call per job.

### Resume matching
Extract skills from your resume once, then score each job by overlap. Adds a
"Match %" column so you know which 3 of 40 to apply to first.

---

## Phase 3 — Delivery

### Telegram or WhatsApp notifications
More immediate than email. Telegram is straightforward: create a bot with
BotFather, get a chat ID, POST to the send-message endpoint. Mirror the shape of
`email_sender.send()` and call it from `run()`.

### Application tracker
Add columns to the `jobs` table: `applied` (bool), `applied_date`, `status`,
`notes`. A tiny Flask page over the existing SQLite would let you mark jobs as
applied and stop them reappearing in your attention, without deleting the record.

### Dashboard
Streamlit over `jobs.db` is the cheapest path to charts: jobs found per day,
which companies post most, category breakdown, your application funnel.

---

## Phase 4 — Robustness

### Closed-posting detection
`last_seen` already tracks this. A job whose `last_seen` is more than ~14 days
stale has almost certainly closed. Add a "Closed" section to the report so you
stop applying to dead links.

### Retry with backoff
Transient network failures currently mark a company as failed for the whole day.
Two retries with a short backoff would clear most of the Errors sheet.

### Per-company scrape strategy override
An optional `Strategy` column in the Excel (`auto` / `ats` / `html` /
`playwright` / `skip`) to force behaviour for awkward companies instead of
relying on the fallback chain.

### robots.txt awareness
The ATS path is fine — those are public APIs meant to be consumed. The HTML
fallback is worth being polite about. Check `robots.txt` before scraping and skip
disallowed paths.

---

## Phase 5 — If it outgrows personal use

### Multi-user
Currently one `companies.xlsx`, one recipient, one SQLite file. Multi-user means
per-user company lists, per-user filters, and a real database. Meaningful rewrite
— only worth it if people actually ask for it.

### Hosted version
A signup page, per-user config, and a daily digest. At that point the interesting
problem stops being scraping and starts being ATS coverage and deliverability.

---

## Explicitly not planned

| Idea | Why not |
|---|---|
| LinkedIn scraping | Aggressively blocked, against their ToS, will get accounts banned |
| Naukri / Indeed scraping | Same problem, and both have anti-bot systems worth more than this project |
| Auto-applying to jobs | Reputationally risky and usually counterproductive |
| Scraping HR emails at scale | Legally grey and a good way to get blacklisted |

Sticking to public ATS APIs and companies' own careers pages keeps this project
something you can put your name on and demo in an interview.

---

## Portfolio framing

If you show this in an interview, the interesting parts aren't the scraping:

- **You inverted the original design** after realising generic scraping was the
  fragile path and ATS APIs were the reliable one — and you can explain the
  tradeoff table.
- **The dedupe key strips query strings**, because you noticed the same posting
  arrives with different tracking parameters.
- **Experience is parsed from the description, not the title**, which is why the
  ATS path matters — it's the only one that returns a description.
- **Failures are isolated per company** so one bad URL can't kill a run.
- **There's an offline selftest**, so the logic is verifiable without hitting the
  network.

Those are the things that separate "I wrote a scraper" from "I designed a system".
