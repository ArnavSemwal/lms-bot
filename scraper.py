import json
import os
import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

COOKIES_PATH = os.getenv("COOKIES_PATH", "cookies.json")
DASHBOARD_URL = "https://lms.vit.ac.in/my/"

# Tera VIP list right here
TARGET_COURSES = ["BACSE106", "BACSE201", "BACSE202", "BACSE344", "BAHUM202"]

def get_client():
    with open(COOKIES_PATH, "r") as f:
        cookies_list = json.load(f)
    cookie_dict = {c["name"]: c["value"] for c in cookies_list}
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}
    return httpx.Client(cookies=cookie_dict, headers=headers, follow_redirects=True, verify=False)

def fetch_enrolled_courses(client):
    response = client.get(DASHBOARD_URL)
    if response.status_code != 200 or "login" in str(response.url):
        return {}
    soup = BeautifulSoup(response.text, "html.parser")
    courses = {}
    select_box = soup.find('select', class_='cal_courses_flt')
    if select_box:
        for option in select_box.find_all('option'):
            val = option.get('value')
            cname = option.get_text(strip=True)
            if val and val.isdigit() and val not in ["0", "1"]:
                # Filter logic: Agar cname me tera target code hai, tabhi uthao
                if any(code in cname for code in TARGET_COURSES):
                    courses[val] = cname
    return courses

def fetch_assignments(client, course_id):
    url = f"https://lms.vit.ac.in/mod/assign/index.php?id={course_id}"
    res = client.get(url)
    soup = BeautifulSoup(res.text, "html.parser")
    assignments = []
    
    for row in soup.find_all('tr'):
        a_tag = row.find('a', href=lambda href: href and "mod/assign/view.php?id=" in href)
        if a_tag:
            title = a_tag.get_text(strip=True)
            link = a_tag['href']
            assign_id = link.split('id=')[-1]
            
            cols = row.find_all(['td', 'th'])
            due_date = "Not Found"
            if len(cols) > 2:
                due_date = cols[-2].get_text(strip=True)
                
            assignments.append({
                "id": assign_id,
                "title": title,
                "url": link,
                "due_date": due_date
            })
    return assignments

if __name__ == "__main__":
    print("🚀 Initializing focused scraper...")
    client = get_client()
    courses = fetch_enrolled_courses(client)
    print(f"✅ Found {len(courses)} active target courses.\n")
    
    for cid, cname in courses.items():
        print(f"--- Checking {cname} ---")
        assigns = fetch_assignments(client, cid)
        if not assigns:
            print("  No assignments found abhi tak.")
        for a in assigns:
            print(f"  📌 {a['title']}")
            print(f"     Due: {a['due_date']}")
            print(f"     Link: {a['url']}")
        print("")
