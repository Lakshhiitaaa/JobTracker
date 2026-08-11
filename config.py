"""Central configuration. Edit this file, not the modules."""
import os

# ---------------- Files ----------------
COMPANIES_FILE = os.getenv("JT_COMPANIES", "companies.xlsx")
REPORTS_DIR    = os.getenv("JT_REPORTS", "reports")
DB_FILE        = os.getenv("JT_DB", "jobs.db")

# ---------------- Filtering ----------------
# A job title must contain at least one of these to be considered software.
INCLUDE_KEYWORDS = [
    "software", "developer", "engineer", "sde", "programmer",
    "java", "python", "golang", "node", "react", "javascript", "typescript",
    "backend", "back end", "back-end", "frontend", "front end", "front-end",
    "full stack", "fullstack", "full-stack",
    "qa", "quality assurance", "test", "testing", "sdet", "automation",
    "api", "devops", "sre", "platform",
    "ai ", "ml ", "machine learning", "data engineer",
    "android", "ios", "mobile", "flutter",
    "graduate engineer", "trainee", "intern",
]

# If the title contains any of these, drop it (seniority guard).
EXCLUDE_TITLE_KEYWORDS = [
    "senior", "sr.", "sr ", "staff", "principal", "lead ", "team lead", "tech lead",
    "manager", "director", "head of", "vp ", "vice president", "chief",
    "architect", " ii", " iii", " iv", " v ", "level 2", "level 3", "l3", "l4", "l5",
    "sales", "marketing", "recruiter", "hr ", "finance", "account executive",
    # customer-facing roles that contain "engineer" but are not software jobs
    "solutions engineer", "solution engineer", "sales engineer", "presales",
    "pre-sales", "customer success", "support engineer", "technical account",
    "consultant", "evangelist", "advocate", "scientist", "professor",
]

# Phrases in the description that strongly indicate a fresher role.
FRESHER_HINTS = [
    "fresher", "freshers", "recent graduate", "new graduate", "new grad",
    "0-1 year", "0-2 year", "0 to 2 year", "1-2 year", "no prior experience",
    "entry level", "entry-level", "campus hire", "graduate trainee",
]

MAX_YEARS_EXPERIENCE = 1      # jobs asking for more than this are dropped
KEEP_IF_EXPERIENCE_UNKNOWN = True   # keep jobs where experience can't be parsed

# Empty list = accept all locations. Otherwise substring match (case-insensitive).
LOCATION_FILTER = [
    "india", "bengaluru", "bangalore", "hyderabad", "pune", "mumbai", "chennai",
    "delhi", "new delhi", "noida", "gurgaon", "gurugram", "kolkata", "ahmedabad",
    "jaipur", "indore", "chandigarh", "kochi", "cochin", "coimbatore",
    "trivandrum", "thiruvananthapuram", "mysore", "mysuru", "visakhapatnam",
    "vizag", "bhubaneswar", "nagpur", "vadodara", "surat", "lucknow", "kanpur",
    "bhopal", "mohali", "goa", "manesar", "faridabad", "thane", "navi mumbai",
    "remote",
]
# Checked BEFORE LOCATION_FILTER. Whole-word match. This is what stops
# "Remote - US" and "Remote (EMEA)" sneaking through on the word "remote".
EXCLUDE_LOCATIONS = [
    "united states", "usa", "us", "u.s.", "uk", "united kingdom", "england",
    "london", "emea", "europe", "european", "canada", "toronto", "australia",
    "sydney", "singapore", "germany", "berlin", "munich", "ireland", "dublin",
    "netherlands", "amsterdam", "israel", "tel aviv", "japan", "tokyo",
    "france", "paris", "poland", "warsaw", "spain", "portugal", "lisbon",
    "brazil", "mexico", "argentina", "new york", "san francisco", "california",
    "texas", "seattle", "austin", "boston", "chicago", "denver", "atlanta",
    "apac", "latam", "philippines", "manila", "vietnam", "indonesia",
    "malaysia", "thailand", "china", "shanghai", "korea", "dubai", "uae",
    "abu dhabi", "saudi", "qatar", "kenya", "nigeria", "south africa",
]

# HTML-scraped pages often have no location at all. True = let those through
# rather than silently dropping every non-ATS company.
ALLOW_BLANK_LOCATION = True

# ---------------- Runtime ----------------
MAX_WORKERS       = 8
REQUEST_TIMEOUT   = 20
USE_PLAYWRIGHT    = True      # fallback for JS-rendered career pages
PLAYWRIGHT_TIMEOUT = 25000
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
POLITE_DELAY = 0.5            # seconds between requests to the same host

# ---------------- Email ----------------
SMTP_HOST     = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER     = os.getenv("SMTP_USER", "")          # your gmail address
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")      # gmail APP PASSWORD, not login pw
EMAIL_FROM    = os.getenv("EMAIL_FROM", "") or SMTP_USER
EMAIL_TO      = [e.strip() for e in os.getenv("EMAIL_TO", "").split(",") if e.strip()]
EMAIL_SUBJECT = "New Fresher Software Jobs - {date} ({count} new)"
SEND_EMAIL_WHEN_NO_NEW_JOBS = False
