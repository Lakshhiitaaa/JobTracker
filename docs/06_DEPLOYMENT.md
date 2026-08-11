# 06 — Deployment

Four ways to run this daily. Pick one.

| Option | Cost | Runs when laptop is off | Setup | Best for |
|---|---|---|---|---|
| **Windows Task Scheduler** | Free | No | 5 min | Starting today |
| **cron** (Mac/Linux) | Free | No | 2 min | Mac/Linux users |
| **GitHub Actions** | Free | Yes | 20 min | Free + always-on, some friction |
| **VPS** | ~₹400/mo | Yes | 30 min | The proper answer long-term |

Recommendation: start with Task Scheduler today, move to GitHub Actions or a VPS
once you trust the output.

---

## Option A — Windows Task Scheduler

**1. Create `run.bat` in the project folder:**

```bat
@echo off
cd /d C:\Projects\JobTracker
set SMTP_USER=you@gmail.com
set SMTP_PASSWORD=abcdefghijklmnop
set EMAIL_TO=you@gmail.com
venv\Scripts\python.exe main.py >> reports\log.txt 2>&1
```

Use `venv\Scripts\python.exe` explicitly. Task Scheduler won't have your venv
activated.

**2. Add it to `.gitignore`** — it contains your password.

**3. Test it by double-clicking `run.bat`.** Then check `reports\log.txt`.

**4. Schedule it:**

- Start → **Task Scheduler** → **Create Basic Task**
- Name: `JobTracker`
- Trigger: **Daily**, 8:00 AM
- Action: **Start a program** → Browse to `C:\Projects\JobTracker\run.bat`
- Finish

**5. Then right-click the task → Properties:**

| Tab | Setting |
|---|---|
| General | Tick **Run whether user is logged on or not** |
| General | Tick **Run with highest privileges** |
| Conditions | **Untick** "Start the task only if the computer is on AC power" |
| Settings | Tick **Run task as soon as possible after a scheduled start is missed** |

That last one matters — it means a run missed while the laptop was asleep fires
when you next open it.

**6. Test:** right-click the task → **Run**. Check `reports\log.txt` and your inbox.

---

## Option B — cron (macOS / Linux)

**1. Create `run.sh`:**

```bash
#!/bin/bash
cd ~/projects/JobTracker
export SMTP_USER="you@gmail.com"
export SMTP_PASSWORD="abcdefghijklmnop"
export EMAIL_TO="you@gmail.com"
./venv/bin/python main.py >> reports/log.txt 2>&1
```

```bash
chmod +x run.sh
./run.sh          # test it
```

**2. Schedule:**

```bash
crontab -e
```

Add:

```
30 8 * * 1-5 /home/you/projects/JobTracker/run.sh
```

`30 8 * * 1-5` = 08:30, Monday to Friday. Cron uses the machine's local time.

Add `run.sh` to `.gitignore`.

> On macOS, cron needs Full Disk Access: System Settings → Privacy & Security →
> Full Disk Access → add `/usr/sbin/cron`.

---

## Option C — GitHub Actions

Free and always-on, but with one wrinkle: **the runner filesystem is wiped after
every run**, so `jobs.db` must be committed back to the repo or deduplication
resets daily and you get the same email forever.

The included `.github/workflows/daily.yml` handles this.

**1. Create a private repo and push:**

```bash
git init
git add .
git commit -m "initial"
git branch -M main
git remote add origin https://github.com/YOU/jobtracker.git
git push -u origin main
```

**Make it private.** Your company list and job history are yours.

**2. Add secrets:** repo → Settings → Secrets and variables → Actions → New
repository secret. Add three:

| Name | Value |
|---|---|
| `SMTP_USER` | you@gmail.com |
| `SMTP_PASSWORD` | your 16-char app password |
| `EMAIL_TO` | you@gmail.com |

**3. Allow the workflow to push:** Settings → Actions → General → Workflow
permissions → **Read and write permissions** → Save.

Without this, the commit-back step fails with a 403 and dedupe silently breaks.

**4. Test:** Actions tab → Daily Job Tracker → **Run workflow**.

**Cron is UTC.** The workflow uses `30 2 * * 1-5` = 08:00 IST. Adjust by
subtracting 5:30 from your desired IST time.

Caveats:
- Scheduled Actions can be delayed 5–30 minutes under load. Fine for this.
- GitHub disables scheduled workflows in repos with no activity for 60 days. The
  daily commit-back keeps it alive.
- Free tier: 2000 minutes/month on private repos. A 3-minute daily run uses ~66.

---

## Option D — VPS

The cleanest answer. Any ₹300–500/month box works: DigitalOcean, Hetzner, AWS
Lightsail, or an Indian provider.

```bash
sudo apt update && sudo apt install -y python3-venv git
git clone https://github.com/YOU/jobtracker.git
cd jobtracker
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/playwright install --with-deps chromium
```

Then follow **Option B** for cron. The server never sleeps, so no missed runs.

Store secrets in `/etc/jobtracker.env` with `chmod 600`, and source it from
`run.sh` rather than hardcoding.

---

## Secrets: what not to do

| Don't | Do |
|---|---|
| Put the password in `config.py` | Environment variables |
| Commit `run.bat` / `run.sh` | `.gitignore` them |
| Use a public repo | Private |
| Use your Gmail login password | App Password |

If you ever commit a password: **revoke the App Password immediately** at
myaccount.google.com. Deleting the commit is not enough — Git keeps history and
GitHub keeps forks.

Included `.gitignore`:

```
venv/
__pycache__/
*.pyc
run.bat
run.sh
.env
reports/log.txt
```

Note `jobs.db` is **not** ignored — GitHub Actions needs it committed. If you're
using Task Scheduler or cron, add it.

---

## Monitoring

You'll notice a broken job tracker only by the absence of email, which is easy to
miss. Two safeguards:

**1. Get a heartbeat email even on quiet days.** In `config.py`:

```python
SEND_EMAIL_WHEN_NO_NEW_JOBS = True
```

**2. Check the run log occasionally:**

```sql
SELECT * FROM runs ORDER BY run_date DESC LIMIT 14;
```

A gap in dates means the scheduler didn't fire. A spike in `errors` means URLs
have gone stale.

---

## Migrating between hosts

`jobs.db` is a single file and fully portable. Copy it to the new host and
history carries over — no re-notification of jobs you've already seen.

Copy `companies.xlsx` and `jobs.db`; everything else comes from Git.
