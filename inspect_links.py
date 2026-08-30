import scraper
from bs4 import BeautifulSoup

client = scraper.get_client()
resp = client.get("https://lms.vit.ac.in/my/")
soup = BeautifulSoup(resp.text, "html.parser")

print("--- Scanning Dashboard Links ---")
for a in soup.find_all("a", href=True):
    href = a["href"]
    text = a.get_text(strip=True)
    if any(k in href for k in ["course", "id=", "view", "mod"]):
        if text:
            print(f"[{text}] -> {href}")