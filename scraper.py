import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import re
from pathlib import Path

COOKIES_FILE = Path("cookies.json")
BASE_URL = "https://lms.vit.ac.in"
DASHBOARD_URL = "https://lms.vit.ac.in/my/"

# Prioritize real document extensions over a bare "pluginfile.php" match,
# since course logos/icons also route through pluginfile.php on some Moodle setups.
ATTACHMENT_EXTENSIONS = (".pdf", ".docx", ".doc", ".zip")


def load_cookies():
    if COOKIES_FILE.exists():
        with open(COOKIES_FILE, "r") as f:
            cookie_list = json.load(f)
            return {c['name']: c['value'] for c in cookie_list}
    return {}


def get_client():
    cookies = load_cookies()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": BASE_URL,
    }
    # verify=True (default) kept intentionally — do not disable SSL verification.
    # If you hit an SSL error specific to your network, fix the cert issue rather
    # than disabling verification.
    return httpx.Client(cookies=cookies, headers=headers, timeout=30.0, follow_redirects=True)


def verify_session(client: httpx.Client) -> bool:
    try:
        response = client.get(DASHBOARD_URL)
        if "login" in str(response.url).lower() or response.status_code == 401:
            return False
        return True
    except Exception as e:
        print(f"Network issue during session check: {e}")
        return False


def fetch_enrolled_courses(client: httpx.Client) -> list[dict]:
    """Dynamically discovers ALL enrolled courses from the Moodle dashboard.

    This replaces an earlier hardcoded stub that only ever pointed at one
    specific assignment ID — it never actually looked at your course list,
    which is why assignments outside that one hardcoded ID were invisible
    to the bot regardless of when they were posted."""
    resp = client.get(DASHBOARD_URL)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    courses = []
    seen_ids = set()
    for a in soup.find_all("a", href=True):
        href = urljoin(DASHBOARD_URL, a["href"])
        match = re.search(r"/course/view\.php\?id=(\d+)", href)
        if not match:
            continue
        course_id = match.group(1)
        if course_id in seen_ids:
            continue
        seen_ids.add(course_id)
        title = a.get_text(strip=True) or f"Course {course_id}"
        courses.append({"id": course_id, "title": title, "url": href})

    return courses


def fetch_course_assignments(client: httpx.Client, course_id: str) -> list[dict]:
    """Fetches ALL assignments listed on a course's assignment index page —
    not just one. Moodle's mod/assign/index.php?id=<course_id> lists every
    assignment in that course in a table."""
    index_url = f"{BASE_URL}/mod/assign/index.php?id={course_id}"
    resp = client.get(index_url)

    if "login" in str(resp.url).lower() or resp.status_code in (401, 403):
        raise RuntimeError("Session appears invalid while fetching course assignment index — re-login needed.")
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    assignments = []
    table = soup.find("table")
    if not table:
        return assignments

    rows = table.find_all("tr")
    for row in rows[1:]:  # skip header row
        link = row.find("a", href=True)
        if not link:
            continue
        href = urljoin(index_url, link["href"])
        assign_match = re.search(r"[?&]id=(\d+)", href)
        if not assign_match:
            continue
        assignments.append({
            "id": assign_match.group(1),
            "title": link.get_text(strip=True),
            "url": href,
        })

    return assignments


def get_assignment_pdf_url(client: httpx.Client, assign_url: str) -> str | None:
    """Scrapes the assignment view page to find the actual pluginfile.php
    attachment link. Returns None (not the page URL) if nothing is found,
    so callers can detect failure instead of silently downloading the wrong thing."""
    resp = client.get(assign_url)

    # If session died mid-run, this will be Moodle's login page, not the
    # assignment page — fail loudly instead of scraping garbage.
    if "login" in str(resp.url).lower() or resp.status_code in (401, 403):
        raise RuntimeError("Session appears invalid while fetching assignment page — re-login needed.")
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    candidates = []

    for a in soup.find_all("a", href=True):
        href = urljoin(assign_url, a["href"])  # resolve relative -> absolute
        if "pluginfile.php" in href:
            candidates.append(href)

    if not candidates:
        return None

    # Prefer a link that clearly ends in a real document extension.
    for href in candidates:
        if href.lower().endswith(ATTACHMENT_EXTENSIONS):
            return href

    # Fall back to the first pluginfile.php link found (e.g. extension-less
    # download URLs that force-download server-side).
    return candidates[0]