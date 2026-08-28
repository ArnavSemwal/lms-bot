import json
import os
import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()
with open(os.getenv("COOKIES_PATH", "cookies.json"), "r") as f:
    cookies = {c["name"]: c["value"] for c in json.load(f)}

res = httpx.get("https://lms.vit.ac.in/my/", cookies=cookies, verify=False, follow_redirects=True)
soup = BeautifulSoup(res.text, "html.parser")

# Look for json or data blocks where Moodle injects course list
found_courses = False
for script in soup.find_all('script'):
    if script.string and "course" in script.string and "id" in script.string:
        if "fullname" in script.string or "shortname" in script.string:
            print("Found potential course data inside a script tag!")
            # Print a snippet to inspect
            print(script.string[:300])
            found_courses = True

if not found_courses:
    print("Searching for elements with course classes...")
    cards = soup.find_all(class_=lambda x: x and ('course' in x.lower() or 'card' in x.lower()))
    print(f"Found {len(cards)} elements with course/card classes.")
    for c in cards[:5]:
        print(c.get_text(strip=True)[:100])
