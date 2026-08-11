"""Generic fallback scraper for career pages with no supported ATS."""
import re, time, requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import config, ats

HEADERS = {"User-Agent": config.USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}
JOB_HREF = re.compile(r"(job|career|position|opening|vacanc|role|apply|posting)", re.I)
NOISE = re.compile(r"^(apply|view|learn more|read more|see all|all jobs|home|about|contact)$", re.I)


def fetch_html(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=config.REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.text


def fetch_html_playwright(url: str) -> str:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page(user_agent=config.USER_AGENT)
        try:
            pg.goto(url, timeout=config.PLAYWRIGHT_TIMEOUT, wait_until="networkidle")
            pg.wait_for_timeout(1500)
            return pg.content()
        finally:
            b.close()


def extract_links(html: str, base_url: str):
    """Pull anything that looks like a job posting link."""
    soup = BeautifulSoup(html, "html.parser")
    seen, jobs = set(), []
    for a in soup.find_all("a", href=True):
        text = " ".join(a.get_text(" ", strip=True).split())
        if not text or len(text) < 5 or len(text) > 120 or NOISE.match(text):
            continue
        href = a["href"]
        if not JOB_HREF.search(href) and not JOB_HREF.search(text):
            continue
        full = urljoin(base_url, href)
        if full in seen:
            continue
        seen.add(full)
        # nearest container often holds the location
        container = a.find_parent(["li", "div", "tr", "article"])
        loc = ""
        if container:
            ctext = container.get_text(" ", strip=True)
            m = re.search(r"(remote|bengaluru|bangalore|hyderabad|pune|mumbai|delhi|noida|gurgaon|"
                          r"chennai|kolkata|ahmedabad|india)[^|,;]{0,20}", ctext, re.I)
            if m:
                loc = m.group(0).strip()
        jobs.append({"title": text, "location": loc, "url": full, "description": ""})
    return jobs


def scrape(url: str):
    """Returns (jobs, source_label). Tries ATS -> static HTML -> Playwright."""
    html = ""
    try:
        html = fetch_html(url)
    except Exception:
        pass

    name, token = ats.detect(url, html)
    if name:
        try:
            return ats.fetch(name, token), name
        except Exception:
            pass  # fall through to HTML

    jobs = extract_links(html, url) if html else []
    if len(jobs) >= 2:
        return jobs, "html"

    if config.USE_PLAYWRIGHT:
        try:
            html2 = fetch_html_playwright(url)
            name, token = ats.detect(url, html2)
            if name:
                try:
                    return ats.fetch(name, token), name
                except Exception:
                    pass
            time.sleep(config.POLITE_DELAY)
            return extract_links(html2, url), "playwright"
        except Exception as e:
            raise RuntimeError(f"playwright failed: {e}")
    return jobs, "html"
