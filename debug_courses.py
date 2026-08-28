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

print("All links containing 'course':")
count = 0
for a in soup.find_all('a', href=True):
    if "course" in a['href']:
        print(f"Text: {a.get_text(strip=True)[:30]} | Href: {a['href']}")
        count += 1
        if count > 15:  # Print first 15 to avoid clutter
            break
