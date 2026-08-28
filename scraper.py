import httpx
from bs4 import BeautifulSoup
import json
from pathlib import Path

COOKIES_FILE = Path("cookies.json")
BASE_URL = "https://lms.vit.ac.in"
DASHBOARD_URL = "https://lms.vit.ac.in/my/"

def load_cookies():
    if COOKIES_FILE.exists():
        with open(COOKIES_FILE, "r") as f:
            cookie_list = json.load(f)
            return {c['name']: c['value'] for c in cookie_list}
    return {}

def get_client():
    cookies = load_cookies()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": BASE_URL
    }
    # Force HTTP/1.1 to prevent Moodle/WAF protocol drop issues, disable SSL verify for local network
    return httpx.Client(
        cookies=cookies,
        headers=headers,
        http1=True,
        http2=False,
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
        print(f"❌ Network issue during session check: {e}")
        return False

def fetch_enrolled_courses(client: httpx.Client):
    return [
        {"title": "Operating Systems Lab (MLFQ)", "url": "https://lms.vit.ac.in/mod/assign/view.php?id=21334"}
    ]

def get_assignment_pdf_url(client: httpx.Client, assign_url: str) -> str:
    """Scrapes the assignment view page to find the actual pluginfile.php PDF link with a retry wrapper."""
    for attempt in range(3):
        try:
            resp = client.get(assign_url)
            soup = BeautifulSoup(resp.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a['href']
                if 'pluginfile.php' in href or href.endswith('.pdf'):
                    return href
            return assign_url
        except Exception as e:
            print(f"⚠️ Attempt {attempt + 1} failed for assignment fetch: {e}")
            if attempt == 2:
                raise
    return assign_url
