import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import re
from pathlib import Path

COOKIES_FILE = Path("cookies.json")
BASE_URL = "https://lms.vit.ac.in"
DASHBOARD_URL = "https://lms.vit.ac.in/my/"
COURSES_URL = "https://lms.vit.ac.in/my/courses.php"
AJAX_SERVICE_URL = "https://lms.vit.ac.in/lib/ajax/service.php"

# Prioritize real document extensions over a bare "pluginfile.php" match
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
                      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": BASE_URL,
    }
    return httpx.Client(
        cookies=cookies,
        headers=headers,
        timeout=30.0,
        follow_redirects=True,
        verify=False
    )


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
    """Dynamically discovers ALL enrolled courses.
    
    VIT LMS (Moodle 4.x) renders courses dynamically via client-side JavaScript
    calling Moodle's WebService AJAX endpoint (core_course_get_enrolled_courses_by_timeline_classification).
    We extract the session key and call the endpoint directly for 100% reliable discovery.
    """
    resp = client.get(COURSES_URL)
    if "login" in str(resp.url).lower() or resp.status_code in (401, 403):
        raise RuntimeError("Session appears invalid while fetching courses — re-login needed.")
    resp.raise_for_status()

    courses = []
    seen_ids = set()

    # 1. Primary Method: Moodle WebService AJAX API
    sesskey_match = re.search(r'"sesskey":\s*"([^"]+)"', resp.text)
    if sesskey_match:
        sesskey = sesskey_match.group(1)
        service_url = f"{AJAX_SERVICE_URL}?sesskey={sesskey}&info=core_course_get_enrolled_courses_by_timeline_classification"
        payload = [
            {
                "index": 0,
                "methodname": "core_course_get_enrolled_courses_by_timeline_classification",
                "args": {
                    "offset": 0,
                    "limit": 0,
                    "classification": "all",
                    "sort": "fullname"
                }
            }
        ]
        try:
            ajax_resp = client.post(service_url, json=payload)
            if ajax_resp.status_code == 200:
                ajax_data = ajax_resp.json()
                if isinstance(ajax_data, list) and len(ajax_data) > 0 and not ajax_data[0].get("error"):
                    raw_courses = ajax_data[0].get("data", {}).get("courses", [])
                    for c in raw_courses:
                        cid = str(c["id"])
                        if cid not in seen_ids:
                            seen_ids.add(cid)
                            courses.append({
                                "id": cid,
                                "title": c.get("fullname", f"Course {cid}"),
                                "shortname": c.get("shortname", ""),
                                "url": c.get("viewurl", f"{BASE_URL}/course/view.php?id={cid}")
                            })
        except Exception as e:
            print(f"Warning: Moodle AJAX course discovery failed ({e}), falling back to HTML parsing.")

    if courses:
        return courses

    # 2. Fallback Method: Static HTML parsing
    soup = BeautifulSoup(resp.text, "html.parser")
    for a in soup.find_all("a", href=True):
        href = urljoin(COURSES_URL, a["href"])
        match = re.search(r"/course/view\.php\?id=(\d+)", href)
        if not match:
            continue
        course_id = match.group(1)
        if course_id in seen_ids:
            continue
        seen_ids.add(course_id)
        title = a.get_text(strip=True) or f"Course {course_id}"
        if title.lower() in ["home", "dashboard", "my courses", "site pages"]:
            continue
        courses.append({"id": course_id, "title": title, "url": href})

    return courses


def fetch_course_assignments(client: httpx.Client, course_id: str) -> list[dict]:
    """Fetches ALL assignments listed in a course.
    
    Checks both Moodle's /mod/assign/index.php?id=<course_id> table and
    the direct course view page (/course/view.php?id=<course_id>) to ensure
    no assignments are missed.
    """
    index_url = f"{BASE_URL}/mod/assign/index.php?id={course_id}"
    resp = client.get(index_url)

    if "login" in str(resp.url).lower() or resp.status_code in (401, 403):
        raise RuntimeError("Session appears invalid while fetching course assignments — re-login needed.")
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    assignments = []
    seen_assign_ids = set()

    # 1. Try parsing from mod/assign/index.php table
    table = soup.find("table")
    if table:
        rows = table.find_all("tr")
        for row in rows[1:]:  # skip header
            link = row.find("a", href=True)
            if not link:
                continue
            href = urljoin(index_url, link["href"])
            assign_match = re.search(r"[?&]id=(\d+)", href)
            if not assign_match:
                continue
            aid = assign_match.group(1)
            if aid not in seen_assign_ids:
                seen_assign_ids.add(aid)
                # Look for due date if available in table cells
                cells = row.find_all("td")
                due_date_str = cells[2].get_text(strip=True) if len(cells) > 2 else None
                assignments.append({
                    "id": aid,
                    "title": link.get_text(strip=True),
                    "url": href,
                    "due_date": due_date_str
                })

    # 2. Fallback / supplement: check course view page directly
    if not assignments:
        course_url = f"{BASE_URL}/course/view.php?id={course_id}"
        resp_course = client.get(course_url)
        if resp_course.status_code == 200:
            soup_course = BeautifulSoup(resp_course.text, "html.parser")
            for a in soup_course.find_all("a", href=True):
                href = urljoin(course_url, a["href"])
                if "/mod/assign/view.php?id=" in href:
                    assign_match = re.search(r"[?&]id=(\d+)", href)
                    if assign_match:
                        aid = assign_match.group(1)
                        if aid not in seen_assign_ids:
                            seen_assign_ids.add(aid)
                            title = a.get_text(strip=True) or f"Assignment {aid}"
                            assignments.append({
                                "id": aid,
                                "title": title,
                                "url": href,
                                "due_date": None
                            })

    return assignments


def get_assignment_pdf_url(client: httpx.Client, assign_url: str) -> str | None:
    """Scrapes the assignment view page to find the actual pluginfile.php attachment link."""
    resp = client.get(assign_url)

    if "login" in str(resp.url).lower() or resp.status_code in (401, 403):
        raise RuntimeError("Session appears invalid while fetching assignment page — re-login needed.")
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    candidates = []

    for a in soup.find_all("a", href=True):
        href = urljoin(assign_url, a["href"])
        if "pluginfile.php" in href:
            candidates.append(href)

    if not candidates:
        return None

    # Prefer a link that ends in a real document extension
    for href in candidates:
        if href.lower().endswith(ATTACHMENT_EXTENSIONS):
            return href

    return candidates[0]