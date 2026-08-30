import scraper
from bs4 import BeautifulSoup

client = scraper.get_client()
resp = client.get("https://lms.vit.ac.in/my/")
soup = BeautifulSoup(resp.text, "html.parser")

print("--- Scanning Sidebar / Nav Links ---")
for a in soup.select("nav a, aside a, .list-group a, .drawer a, .block_navigation a"):
    href = a.get("href", "")
    text = a.get_text(strip=True)
    if text and href:
        print(f"[{text}] -> {href}")