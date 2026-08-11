# 01 — Setup

From nothing to a working daily email. Follow in order; don't skip Step 5.

---

## Step 1 — Install Python

Download **Python 3.11 or newer** from [python.org](https://www.python.org/downloads/).

On Windows, tick **"Add python.exe to PATH"** on the first installer screen.
This is the single most commonly missed step.

Verify:

```bash
python --version
```

Expected: `Python 3.11.x` or higher.

| Problem | Fix |
|---|---|
| `'python' is not recognized` | PATH box wasn't ticked. Re-run the installer, choose Modify, tick it. |
| Shows `Python 2.7.x` | Use `python3 --version` instead, and `python3` everywhere below. |
| Shows `Python 3.9` or lower | Upgrade. The code uses 3.10+ syntax. |

---

## Step 2 — Place the project

Extract the project to a short, simple path:

```
C:\Projects\JobTracker\          (Windows)
~/projects/JobTracker/           (macOS / Linux)
```

**Avoid OneDrive, Google Drive, and Dropbox folders.** Cloud sync locks
`jobs.db` mid-write and produces `database is locked` errors.

Open the folder in VS Code: **File → Open Folder → JobTracker**.

---

## Step 3 — Open the integrated terminal

In VS Code: **Terminal → New Terminal** (or `` Ctrl+` ``).

Confirm the prompt shows your project path:

```
C:\Projects\JobTracker>
```

Every command in this document runs from here.

---

## Step 4 — Create and activate a virtual environment

A venv keeps this project's libraries isolated from your system Python.

```bash
python -m venv venv
```

Activate it:

| OS / Shell | Command |
|---|---|
| Windows CMD | `venv\Scripts\activate` |
| Windows PowerShell | `venv\Scripts\Activate.ps1` |
| macOS / Linux | `source venv/bin/activate` |

Your prompt now begins with `(venv)`. That prefix is how you know it's active.

**You must re-activate every time you open a new terminal.** If a command fails
with `ModuleNotFoundError`, the first thing to check is whether `(venv)` is
showing.

PowerShell may refuse with *"running scripts is disabled"*. Fix once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

---

## Step 5 — Install dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

| Package | Used for |
|---|---|
| `pandas` | Reading `companies.xlsx` |
| `openpyxl` | Writing the formatted report |
| `requests` | ATS JSON APIs and plain HTTP fetches |
| `beautifulsoup4` + `lxml` | Parsing HTML career pages |
| `playwright` | Rendering JavaScript-only career pages |

The `playwright install chromium` line downloads a real browser (~150 MB). It's
only used as a last-resort fallback, but install it now so it's ready. To skip
it, set `USE_PLAYWRIGHT = False` in `config.py`.

---

## Step 6 — Verify the install

```bash
python main.py --selftest
```

This runs ~20 checks on the filtering, ATS detection, dedupe, and Excel logic.
It needs **no internet** and writes only to a temp folder.

Expected last line: `ALL PASSED`

If anything says `FAIL`, stop here. Don't continue until it passes — a failure
means the environment is wrong, not your data.

---

## Step 7 — Create your company list

```bash
python main.py --init
```

This writes `companies.xlsx` with 4 sample rows. Open it and replace them with
your own startups.

This step is where the project succeeds or fails, and it has its own guide:
**[02_COMPANIES.md](02_COMPANIES.md)**. Read it before filling in more than a
handful of rows.

Start with **10–15 companies**. Prove the pipeline works, then expand.

---

## Step 8 — First test run (no email, no database)

```bash
python main.py --dry-run --limit 5
```

- `--dry-run` — nothing is written to `jobs.db`, no email is sent
- `--limit 5` — only the first 5 companies

You'll see one line per company:

```
Checking 5 companies...
  [1/5] Postman                          7 match  (greenhouse)
  [2/5] Hasura                           3 match  (lever)
  [3/5] Zerodha                          2 match  (html)
  [4/5] Zepto                            0 match  (ashby)
  [5/5] SomeCorp                         FAILED: HTTPSConnectionPool...

12 matching jobs, 12 new. Report: reports/jobs_2026-08-11.xlsx
```

The word in brackets is the method used. `greenhouse`/`lever`/`ashby`/etc. means
the reliable JSON path. `html` or `playwright` means guessing.

> In `--dry-run`, **every job shows as new** because the database isn't consulted.
> That's expected.

---

## Step 9 — Read the report and tune

Open `reports/jobs_2026-08-11.xlsx`. Two sheets:

**Sheet "Jobs"** — green rows are new. Check:

| What you see | What to change in `config.py` |
|---|---|
| Senior roles slipping through | Add the word to `EXCLUDE_TITLE_KEYWORDS` |
| Relevant roles missing | Add the word to `INCLUDE_KEYWORDS` |
| Too much noise from other departments | Add those words to `EXCLUDE_TITLE_KEYWORDS` |
| Wrong cities | Fill in `LOCATION_FILTER` |
| Almost everything says "Not specified" | Normal for HTML-scraped companies — see below |

**Sheet "Errors"** — companies that failed. Each one needs a better URL. Go back
to [02_COMPANIES.md](02_COMPANIES.md).

Re-run Step 8 after each change. Loop until the output looks right. **Do not
move on until it does** — once emails start, bad filtering means daily spam.

Full setting reference: [03_CONFIGURATION.md](03_CONFIGURATION.md)

---

## Step 10 — Set up Gmail sending

Gmail rejects your normal password from scripts. You need an **App Password**.

1. Go to [myaccount.google.com](https://myaccount.google.com) → **Security**
2. Enable **2-Step Verification** — App Passwords do not exist without it
3. Search the settings page for **App passwords**
4. Create one named `JobTracker`
5. Copy the 16-character code, e.g. `abcd efgh ijkl mnop`

**Never put this in `config.py`.** Credentials in code end up in Git.

Not using Gmail? See the SMTP table in [03_CONFIGURATION.md](03_CONFIGURATION.md).

---

## Step 11 — Provide credentials as environment variables

In the same terminal:

**Windows CMD**
```cmd
set SMTP_USER=you@gmail.com
set SMTP_PASSWORD=abcdefghijklmnop
set EMAIL_TO=you@gmail.com
```

**Windows PowerShell**
```powershell
$env:SMTP_USER="you@gmail.com"
$env:SMTP_PASSWORD="abcdefghijklmnop"
$env:EMAIL_TO="you@gmail.com"
```

**macOS / Linux**
```bash
export SMTP_USER="you@gmail.com"
export SMTP_PASSWORD="abcdefghijklmnop"
export EMAIL_TO="you@gmail.com"
```

Notes:
- Drop the spaces from the App Password.
- `EMAIL_TO` accepts a comma-separated list: `me@x.com,friend@y.com`
- These vanish when you close the terminal. [06_DEPLOYMENT.md](06_DEPLOYMENT.md)
  makes them permanent.
- `config.py` reads these **at import time**, so set them *before* running
  Python, not after.

---

## Step 12 — First real run

```bash
python main.py --limit 5
```

Check your inbox. You should get an HTML summary table plus the Excel attached.

Now **run the exact same command again**:

```bash
python main.py --limit 5
```

Expected output: `No new jobs - email skipped.`

That is the deduplication working — `jobs.db` remembers what it already sent.
If you get a second identical email, something is wrong; see
[07_TROUBLESHOOTING.md](07_TROUBLESHOOTING.md).

Then run everything:

```bash
python main.py
```

---

## Step 13 — Schedule it

Pick one option in **[06_DEPLOYMENT.md](06_DEPLOYMENT.md)**. Windows Task
Scheduler is the fastest way to get a daily 8 AM email today.

---

## Daily use, once set up

You don't run anything. The scheduler does. Your only ongoing job:

1. Read the morning email.
2. Add new startups to `companies.xlsx` as you find them.
3. Every couple of weeks, open the **Errors** sheet and fix broken URLs.
