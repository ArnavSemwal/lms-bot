import json
import os
import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()
with open(os.getenv("COOKIES_PATH", "cookies.json"), "r") as f:
    cookies = {c["name"]: c["value"] for c in json.load(f)}

res = httpx.get("https://lms.vit.ac.in/my/courses.php", cookies=cookies, verify=False, follow_redirects=True)
soup = BeautifulSoup(res.text, "html.parser")

print("Checking /my/courses.php links:")
for a in soup.find_all('a', href=True):
    if "course/view.php?id=" in a['href']:
        title = a.get_text(strip=True)
        if title and len(title) > 3:
            print(f"Course: {title} | Href: {a['href']}")
