"""Startup Job Tracker - entry point.

  python main.py --init        create a sample companies.xlsx
  python main.py --selftest    run offline logic tests (no network)
  python main.py --dry-run     scrape + report, don't email, don't write DB
  python main.py               full daily run
"""
import argparse, sys, traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
import pandas as pd
import config, scraper, filters, database, excel_report


def load_companies(path=None):
    path = path or config.COMPANIES_FILE
    df = pd.read_excel(path)
    df.columns = [str(c).strip() for c in df.columns]
    required = {"Company Name", "Careers URL"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{path} is missing column(s): {missing}")
    if "Status" in df.columns:
        df = df[df["Status"].astype(str).str.strip().str.lower() != "inactive"]
    df = df.dropna(subset=["Careers URL"])
    return df.to_dict("records")


def process(company):
    name = str(company["Company Name"]).strip()
    url = str(company["Careers URL"]).strip()
    jobs, source = scraper.scrape(url)
    kept = []
    for j in jobs:
        ok, ej, _ = filters.evaluate(j)
        if ok:
            ej["company"] = name
            ej["careers_page"] = url
            ej["source"] = source
            kept.append(ej)
    return name, kept, source


def run(args):
    companies = load_companies(args.companies)
    if args.company:
        companies = [c for c in companies
                     if args.company.lower() in str(c["Company Name"]).lower()]
    if args.limit:
        companies = companies[:args.limit]
    print(f"Checking {len(companies)} companies...")

    matched, errors = [], []
    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as ex:
        futs = {ex.submit(process, c): c for c in companies}
        for i, f in enumerate(as_completed(futs), 1):
            c = futs[f]
            try:
                name, kept, source = f.result()
                matched.extend(kept)
                print(f"  [{i}/{len(companies)}] {name:<30} {len(kept):>3} match  ({source})")
            except Exception as e:
                errors.append({"company": c["Company Name"], "url": c["Careers URL"], "error": e})
                print(f"  [{i}/{len(companies)}] {str(c['Company Name']):<30} FAILED: {str(e)[:70]}")

    db = None if args.dry_run else database.DB()
    rows, new_jobs = [], []
    for j in matched:
        is_new = True if db is None else db.upsert(j)
        j["is_new"] = is_new
        j["date_found"] = date.today().isoformat()
        rows.append(j)
        if is_new:
            new_jobs.append(j)
    if db:
        db.log_run(len(companies), len(matched), len(new_jobs), len(errors))
        db.close()

    path = excel_report.build(rows, errors)
    print(f"\n{len(matched)} matching jobs, {len(new_jobs)} new. Report: {path}")

    if args.no_email or args.dry_run:
        return
    if not new_jobs and not config.SEND_EMAIL_WHEN_NO_NEW_JOBS:
        print("No new jobs - email skipped.")
        return
    import email_sender
    email_sender.send(new_jobs, path,
                      {"companies": len(companies), "found": len(matched), "errors": len(errors)})
    print(f"Email sent to {', '.join(config.EMAIL_TO)}")


def init_sample(path):
    pd.DataFrame([
        {"Company Name": "Zerodha", "Careers URL": "https://zerodha.com/careers/", "Location": "Bengaluru", "ATS": "", "Status": "Active"},
        {"Company Name": "Postman", "Careers URL": "https://boards.greenhouse.io/postman", "Location": "Bengaluru", "ATS": "greenhouse", "Status": "Active"},
        {"Company Name": "Hasura", "Careers URL": "https://jobs.lever.co/hasura", "Location": "Bengaluru", "ATS": "lever", "Status": "Active"},
        {"Company Name": "Zepto", "Careers URL": "https://jobs.ashbyhq.com/zepto", "Location": "Mumbai", "ATS": "ashby", "Status": "Active"},
    ]).to_excel(path, index=False)
    print(f"Created {path} - add your companies there.")


def selftest():
    ok = True
    def chk(label, cond):
        nonlocal ok
        print(f"  {'PASS' if cond else 'FAIL'}  {label}")
        ok = ok and cond

    print("filters:")
    chk("keeps 'Software Engineer'", filters.title_matches("Software Engineer"))
    chk("drops 'Senior Software Engineer'", not filters.title_matches("Senior Software Engineer"))
    chk("drops 'Engineering Manager'", not filters.title_matches("Engineering Manager"))
    chk("keeps 'SDET'", filters.title_matches("SDET"))
    chk("drops 'Account Executive'", not filters.title_matches("Account Executive"))
    chk("parses '0-2 years'", filters.extract_experience("we need 0-2 years experience")[0] == 0)
    chk("parses '5+ years'", filters.extract_experience("5+ years of experience")[0] == 5)
    chk("detects 'fresher'", filters.extract_experience("open to freshers")[0] == 0)
    chk("unknown -> None", filters.extract_experience("great team, free lunch")[0] is None)
    chk("category QA", filters.categorize("QA Automation Engineer") == "QA / SDET")
    chk("drops 'Solutions Engineer'", not filters.title_matches("Enterprise Solutions Engineer, UK"))
    chk("drops 'Applied AI Scientist'", not filters.title_matches("Applied AI Scientist"))
    chk("keeps 'Graduate Engineer Trainee'", filters.title_matches("Graduate Engineer Trainee"))

    print("location:")
    chk("Bengaluru allowed", filters.location_ok("Bengaluru, India"))
    chk("London blocked", not filters.location_ok("London, UK"))
    chk("blank allowed", filters.location_ok(""))
    chk("'Remote - US' blocked", not filters.location_ok("Remote - US"))
    chk("'Remote (EMEA)' blocked", not filters.location_ok("Remote (EMEA)"))
    chk("'Remote, India' allowed", filters.location_ok("Remote, India"))
    chk("'Indiana, US' blocked", not filters.location_ok("Indianapolis, Indiana, United States"))
    chk("'Austin' blocked", not filters.location_ok("Austin, Texas"))
    chk("drops 'Software Engineer II'", not filters.title_matches("Software Engineer II"))

    print("evaluate:")
    keep, j, _ = filters.evaluate({"title": "Backend Developer", "location": "Pune",
                                   "description": "0-2 years experience", "url": "http://x/1"})
    chk("fresher backend kept", keep and j["category"] == "Backend")
    keep, _, r = filters.evaluate({"title": "Backend Developer", "location": "Pune",
                                   "description": "6+ years experience", "url": "http://x/2"})
    chk("6y backend dropped", not keep)
    keep, _, _ = filters.evaluate({"title": "Backend Developer", "location": "Pune",
                                   "description": "2+ years of experience", "url": "http://x/3"})
    chk("'2+ years' dropped", not keep)
    keep, _, _ = filters.evaluate({"title": "Backend Developer", "location": "Pune",
                                   "description": "0-2 years of experience", "url": "http://x/4"})
    chk("'0-2 years' kept", keep)

    print("ats detection:")
    chk("greenhouse url", ats_check("https://boards.greenhouse.io/postman", "greenhouse", "postman"))
    chk("lever url", ats_check("https://jobs.lever.co/hasura", "lever", "hasura"))
    chk("ashby url", ats_check("https://jobs.ashbyhq.com/zepto", "ashby", "zepto"))
    chk("plain url -> none", ats_check("https://zerodha.com/careers/", None, None))

    print("database:")
    import os, tempfile
    tmp = os.path.join(tempfile.mkdtemp(), "t.db")
    db = database.DB(tmp)
    job = {"company": "X", "title": "SDE", "location": "BLR", "url": "https://x.com/j/1"}
    chk("first insert is new", db.upsert(job) is True)
    chk("second insert not new", db.upsert(job) is False)
    chk("querystring ignored", db.upsert({**job, "url": "https://x.com/j/1?src=li"}) is False)
    db.close()

    print("excel:")
    p = excel_report.build([{"company": "X", "title": "SDE", "category": "Backend",
                             "experience": "0-2 years", "location": "BLR",
                             "url": "https://x.com/j/1", "careers_page": "https://x.com",
                             "is_new": True}], out_dir=tempfile.mkdtemp())
    chk("report written", os.path.exists(p))

    print("\n" + ("ALL PASSED" if ok else "FAILURES PRESENT"))
    return 0 if ok else 1


def ats_check(url, exp_name, exp_tok):
    import ats
    n, t = ats.detect(url, "")
    return n == exp_name and (exp_tok is None or t == exp_tok)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--companies", default=None)
    ap.add_argument("--company", default=None, help="run one company by name substring")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true", help="no DB writes, no email")
    ap.add_argument("--no-email", action="store_true")
    ap.add_argument("--init", action="store_true", help="create sample companies.xlsx")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        sys.exit(selftest())
    if a.init:
        init_sample(a.companies or config.COMPANIES_FILE); sys.exit(0)
    try:
        run(a)
    except Exception:
        traceback.print_exc(); sys.exit(1)
