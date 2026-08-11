# Startup Job Tracker

A Python automation that checks startup career pages every day, finds fresher
software jobs, writes a formatted Excel report, and emails only the postings it
has never seen before.

```
companies.xlsx  ->  ATS APIs / scraper  ->  filters  ->  SQLite dedupe
                                                              |
                                        Excel report  <-------+
                                                              |
                                        Email summary <-------+
```

---

## Quick start

```bash
python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # macOS / Linux

pip install -r requirements.txt
playwright install chromium

python main.py --selftest        # 20 offline checks, no network
python main.py --init            # writes a sample companies.xlsx
python main.py --dry-run --limit 5
```

Full walkthrough: **[docs/01_SETUP.md](docs/01_SETUP.md)**

---

## Documentation

| Doc | Read it when |
|---|---|
| [01_SETUP.md](docs/01_SETUP.md) | Installing for the first time |
| [02_COMPANIES.md](docs/02_COMPANIES.md) | Building your company list — **the highest-value doc here** |
| [03_CONFIGURATION.md](docs/03_CONFIGURATION.md) | Tuning what counts as a "fresher software job" |
| [04_ARCHITECTURE.md](docs/04_ARCHITECTURE.md) | Understanding how it works, and why it's built this way |
| [05_MODULE_REFERENCE.md](docs/05_MODULE_REFERENCE.md) | Editing the code |
| [06_DEPLOYMENT.md](docs/06_DEPLOYMENT.md) | Making it run daily without you |
| [07_TROUBLESHOOTING.md](docs/07_TROUBLESHOOTING.md) | Something broke |
| [08_ROADMAP.md](docs/08_ROADMAP.md) | Extending it |

---

## Commands

| Command | What it does |
|---|---|
| `python main.py` | Full daily run: scrape, dedupe, report, email |
| `python main.py --selftest` | Offline logic tests. No network, no files touched |
| `python main.py --init` | Create a starter `companies.xlsx` |
| `python main.py --dry-run` | Scrape and report, but **no DB write and no email** |
| `python main.py --no-email` | Scrape, dedupe, write DB and report — skip the email |
| `python main.py --limit 5` | Only the first 5 companies |
| `python main.py --company zerodha` | Only companies whose name contains "zerodha" |
| `python main.py --companies other.xlsx` | Use a different input file |

Flags combine: `python main.py --dry-run --limit 10`

---

## Project layout

```
JobTracker/
├── companies.xlsx           <- YOUR INPUT. The one file you edit daily.
├── config.py                <- All tuning knobs
├── main.py                  <- Entry point, CLI, orchestration, selftest
├── ats.py                   <- ATS detection + JSON API clients
├── scraper.py               <- HTML / Playwright fallback
├── filters.py               <- Title match, experience parsing, categorisation
├── database.py              <- SQLite dedupe store
├── excel_report.py          <- Formatted .xlsx writer
├── email_sender.py          <- SMTP sender
├── requirements.txt
├── jobs.db                  <- Created on first run. Your dedupe memory.
├── reports/
│   └── jobs_2026-08-11.xlsx <- One per run day
├── docs/
└── .github/workflows/daily.yml
```

---

## The one thing that matters most

The quality of your **Careers URL** column decides whether this project works.

A URL like `https://jobs.lever.co/hasura` hits a JSON API and will still work in
two years. A URL like `https://hasura.io/careers` gets guessed at by an HTML
parser and breaks the next time they redesign.

See [02_COMPANIES.md](docs/02_COMPANIES.md) for how to convert one into the other.
