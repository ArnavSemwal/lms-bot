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

print("Searching for divs with data-region...")
for div in soup.find_all('div', attrs={'data-region': True}):
    print(f"data-region: {div['data-region']}")

print("\nSearching for course list items or containers...")
for el in soup.find_all(class_=lambda x: x and 'course' in x.lower()):
    classes = " ".join(el.get('class', []))
    print(f"Tag: {el.name} | Class: {classes}")
