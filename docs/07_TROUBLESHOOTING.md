# 07 — Troubleshooting

Work top to bottom. Most problems are one of the first three.

---

## First three checks

**1. Is the venv active?** Your prompt must start with `(venv)`.
```bash
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
```

**2. Does the selftest pass?**
```bash
python main.py --selftest
```
If this fails, the problem is your environment, not your data or config.

**3. Are you in the right folder?** The prompt must show the JobTracker path.

---

## Install and startup

| Error | Cause | Fix |
|---|---|---|
| `'python' is not recognized` | PATH not set | Reinstall Python with "Add to PATH" ticked |
| `ModuleNotFoundError: No module named 'pandas'` | venv not active, or deps not installed | Activate, then `pip install -r requirements.txt` |
| `running scripts is disabled on this system` | PowerShell policy | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `No module named 'playwright'` | Not installed | `pip install playwright && playwright install chromium` |
| `Executable doesn't exist at ...chrome-win` | Package installed, browser not | `playwright install chromium` |
| `error: externally-managed-environment` | System Python on Linux | Use a venv (you should anyway) |

---

## Reading `companies.xlsx`

| Error | Fix |
|---|---|
| `FileNotFoundError: companies.xlsx` | Run `python main.py --init`, or you're in the wrong folder |
| `is missing column(s): {'Careers URL'}` | Header must match exactly, including capitals and the space |
| `Permission denied` / `[Errno 13]` | The file is open in Excel. Close it. |
| Rows silently skipped | Blank Careers URL, or `Status` is `Inactive` |
| `Excel file format cannot be determined` | It's a `.csv` renamed to `.xlsx`. Open and Save As real xlsx. |

---

## Scraping

### A company shows `FAILED` in the Errors sheet

| Error text | Meaning | Fix |
|---|---|---|
| `404 Client Error` | URL is wrong or the board moved | Re-find the URL — [02_COMPANIES.md](02_COMPANIES.md) |
| `403 Forbidden` | Blocked as a bot | Find the ATS URL instead; APIs aren't blocked |
| `HTTPSConnectionPool ... timed out` | Slow site | Raise `REQUEST_TIMEOUT` to 40 |
| `playwright failed: Timeout 25000ms` | Page never settles | Raise `PLAYWRIGHT_TIMEOUT` to 45000 |
| `NameResolutionError` | Domain is dead/typo'd | Check the URL in a browser |
| `SSLCertVerificationError` | Broken cert on their end | Usually worth marking `Inactive` |

### A company returns `0 match`

Not necessarily broken. Check in order:

1. **Do they actually have fresher openings?** Open the URL in a browser.
2. **Which source was used?** `(html)` or `(playwright)` means no description, so
   experience is `Not specified`. With `KEEP_IF_EXPERIENCE_UNKNOWN = False` those
   all get dropped.
3. **Is `LOCATION_FILTER` set?** HTML-scraped jobs often have a blank location,
   which fails a non-empty filter. Try emptying it.
4. **Title keywords.** Their titles may use wording you haven't included —
   "Member of Technical Staff", "Product Engineer".

Debug one company:
```bash
python main.py --dry-run --company razorpay
```

### Everything returns `(html)`, never an ATS name

Your Careers URLs are marketing pages. This is the single biggest quality
problem in the project. Work through [02_COMPANIES.md](02_COMPANIES.md).

### Junk in the report (nav links, "Life at X")

The HTML fallback guessing wrong. Either find the ATS URL, or add distinctive
words to `EXCLUDE_TITLE_KEYWORDS`.

---

## Filtering

| Symptom | Fix |
|---|---|
| Senior roles appearing | Add the exact word to `EXCLUDE_TITLE_KEYWORDS`. Check the title — "Software Engineer II" needs `" ii"` with a leading space. |
| Relevant roles missing | Add to `INCLUDE_KEYWORDS`. Try `--dry-run --company X` and look at raw titles. |
| Everything says "Not specified" | Those companies are HTML-scraped, so there's no description to parse. Expected. |
| Non-engineering roles | Add the department word to `EXCLUDE_TITLE_KEYWORDS` |
| A keyword matches too much | Add a leading/trailing space to force a word boundary — `"qa"` matches *Quality*, `" qa "` doesn't |

---

## Deduplication

### Same jobs emailed every day

1. **Are you using `--dry-run`?** It never writes to the DB, so everything is
   always new.
2. **Does `jobs.db` exist and is it growing?** If it's recreated each run,
   something is deleting it — on GitHub Actions this means the commit-back step
   is failing. Check Workflow permissions (Option C in
   [06_DEPLOYMENT.md](06_DEPLOYMENT.md)).
3. **Are the apply URLs changing?** Some boards embed a session ID in the link.
   Compare `apply_link` values across two days:
   ```sql
   SELECT company, title, apply_link, first_seen FROM jobs
   WHERE company='X' ORDER BY first_seen DESC;
   ```

### Nothing is ever new

`jobs.db` already contains everything. Normal on day two. Verify:
```sql
SELECT COUNT(*) FROM jobs;
SELECT * FROM runs ORDER BY run_date DESC LIMIT 5;
```

### Start over

```bash
del jobs.db          # Windows
rm jobs.db           # Mac/Linux
```
The next run treats every job as new — expect one large email.

### `database is locked`

`jobs.db` is on OneDrive/Dropbox, or DB Browser has it open. Move the project off
cloud sync; close other tools.

---

## Email

| Error | Fix |
|---|---|
| `RuntimeError: SMTP_USER / SMTP_PASSWORD / EMAIL_TO env vars not set` | Set them **before** launching Python — `config.py` reads them at import |
| `SMTPAuthenticationError: Username and Password not accepted` | Using your login password. Create an **App Password**. |
| `Application-specific password required` | Same |
| App Passwords option missing in Google | 2-Step Verification isn't enabled |
| `SMTPServerDisconnected` | Wrong port. Gmail SSL is **465**, not 587. |
| `getaddrinfo failed` | No network, or `SMTP_HOST` typo |
| `No new jobs - email skipped` | Working as designed. Set `SEND_EMAIL_WHEN_NO_NEW_JOBS = True` for a heartbeat. |
| Nothing arrives, no error | Check spam. Add your own address to contacts. |
| Attachment missing | The Excel wasn't written — check the console for the report path |

Test credentials in isolation:
```python
import smtplib, os
s = smtplib.SMTP_SSL("smtp.gmail.com", 465)
s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
print("OK")
s.quit()
```

Confirm the variables actually reached Python:
```python
import os; print(repr(os.getenv("SMTP_USER")), repr(os.getenv("EMAIL_TO")))
```
`None` means they weren't set in this shell.

---

## Excel output

| Symptom | Fix |
|---|---|
| `PermissionError` writing the report | Yesterday's report is open in Excel. Close it. |
| Report empty but console showed matches | You looked at an old file — check the exact path printed |
| No Errors sheet | Nothing failed. Good. |
| Hyperlinks not clickable | Only column G is linked; some ATS give a relative URL |

---

## Scheduling

| Symptom | Fix |
|---|---|
| Task Scheduler runs but nothing happens | Use the full path `venv\Scripts\python.exe`, and `cd /d` to the project first |
| `run.bat` flashes and closes | Redirect output: `>> reports\log.txt 2>&1`, then read the log |
| Task never fires | Tick "Run whether user is logged on or not"; untick the AC-power condition |
| GH Actions runs but no email | Secrets not set, or names don't match exactly |
| GH Actions: `403` on push | Workflow permissions → Read and write |
| GH Actions fires at the wrong time | Cron is UTC. IST = UTC + 5:30. |
| Workflow stopped after ~2 months | GitHub disables schedules in inactive repos. Push a commit. |

---

## Performance

| Symptom | Fix |
|---|---|
| Run takes 20+ minutes | Too many Playwright fallbacks. Convert URLs to ATS. |
| Machine freezes during a run | Lower `MAX_WORKERS` to 4 |
| Sites start returning 403 | Lower `MAX_WORKERS`, raise `POLITE_DELAY` |

---

## Still stuck

Collect:
```bash
python --version
pip list
python main.py --selftest
python main.py --dry-run --limit 3
```
The full traceback matters — the last line alone usually isn't enough.
