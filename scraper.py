import re
import json
from pathlib import Path
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import httpx

COOKIES_FILE = Path("cookies.json")
BASE_URL = "https://lms.vit.ac.in"
DASHBOARD_URL = "https://lms.vit.ac.in/my/"
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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": BASE_URL,
    }
    return httpx.Client(cookies=cookies, headers=headers, timeout=30.0, follow_redirects=True, verify=False)

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
    return [
        {"id": "os", "title": "Operating Systems (BACSE106)", "url": f"{BASE_URL}/course/index.php"},
        {"id": "dbs", "title": "Database Systems (BACSE202)", "url": f"{BASE_URL}/course/index.php"}
    ]

def fetch_course_assignments(client: httpx.Client, course_id: str) -> list[dict]:
    assignments = []
    resp = client.get(DASHBOARD_URL)
    if "login" in str(resp.url).lower() or resp.status_code in (401, 403):
        raise RuntimeError("Session appears invalid — re-login needed.")
    
    soup = BeautifulSoup(resp.text, "html.parser")
    seen_ids = set()
    
    for a in soup.find_all("a", href=True):
        href = urljoin(BASE_URL, a["href"])
        if "/mod/assign/view.php?id=" in href:
            assign_match = re.search(r"[?&]id=(\d+)", href)
            if assign_match:
                assign_id = assign_match.group(1)
                if assign_id not in seen_ids:
                    seen_ids.add(assign_id)
                    title = a.get_text(strip=True)
                    title = re.sub(r'\s+is due.*$', '', title, flags=re.IGNORECASE)
                    
                    is_dbs = "DBS" in title or "Joins" in title or "Database" in title
                    
                    if course_id == "dbs" and is_dbs:
                        assignments.append({"id": assign_id, "title": title if title else f"Assignment {assign_id}", "url": href})
                    elif course_id == "os" and not is_dbs:
                        assignments.append({"id": assign_id, "title": title if title else f"Assignment {assign_id}", "url": href})

    return assignments

def get_assignment_details(client: httpx.Client, assign_url: str) -> dict:
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
            
    pdf_url = None
    for href in candidates:
        if href.lower().endswith(ATTACHMENT_EXTENSIONS):
            pdf_url = href
            break
    if pdf_url is None and candidates:
        pdf_url = candidates[0]

    status_text = None
    for row in soup.find_all("tr"):
        cells = row.find_all(["th", "td"])
        if len(cells) >= 2 and "submission status" in cells[0].get_text(strip=True).lower():
            status_text = cells[1].get_text(strip=True)
            break

    is_submitted = False
    if status_text:
        lowered = status_text.lower()
        if "submitted" in lowered and "not submitted" not in lowered:
            is_submitted = True

    return {"pdf_url": pdf_url, "submission_status": status_text, "is_submitted": is_submitted}

def get_assignment_pdf_url(client: httpx.Client, assign_url: str) -> str | None:
    return get_assignment_details(client, assign_url)["pdf_url"]