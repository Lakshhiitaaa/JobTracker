"""SQLite dedupe store."""
import sqlite3, hashlib, re
from datetime import date
import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    job_key      TEXT PRIMARY KEY,
    company      TEXT, title TEXT, category TEXT, experience TEXT,
    location     TEXT, apply_link TEXT, careers_page TEXT,
    first_seen   TEXT, last_seen TEXT
);
CREATE INDEX IF NOT EXISTS idx_first_seen ON jobs(first_seen);
CREATE TABLE IF NOT EXISTS runs (
    run_date TEXT, companies INTEGER, jobs_found INTEGER,
    new_jobs INTEGER, errors INTEGER
);
"""


def _norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def make_key(company, title, location, url):
    """Prefer the apply URL (stable per posting); fall back to a content hash."""
    if url and len(url) > 15:
        base = re.sub(r"[?#].*$", "", url.lower().rstrip("/"))
    else:
        base = f"{_norm(company)}|{_norm(title)}|{_norm(location)}"
    return hashlib.md5(base.encode()).hexdigest()


class DB:
    def __init__(self, path=None):
        self.conn = sqlite3.connect(path or config.DB_FILE)
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def upsert(self, job: dict) -> bool:
        """Insert or touch. Returns True if this job is NEW."""
        today = date.today().isoformat()
        key = make_key(job["company"], job["title"], job.get("location", ""), job.get("url", ""))
        cur = self.conn.execute("SELECT 1 FROM jobs WHERE job_key=?", (key,))
        if cur.fetchone():
            self.conn.execute("UPDATE jobs SET last_seen=? WHERE job_key=?", (today, key))
            return False
        self.conn.execute(
            "INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?)",
            (key, job["company"], job["title"], job.get("category", ""), job.get("experience", ""),
             job.get("location", ""), job.get("url", ""), job.get("careers_page", ""), today, today))
        return True

    def log_run(self, companies, found, new, errors):
        self.conn.execute("INSERT INTO runs VALUES (?,?,?,?,?)",
                          (date.today().isoformat(), companies, found, new, errors))
        self.conn.commit()

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.commit(); self.conn.close()
