import scraper
from bs4 import BeautifulSoup

client = scraper.get_client()
resp = client.get("https://lms.vit.ac.in/my/courses.php")
soup = BeautifulSoup(resp.text, "html.parser")

print("--- Scanning Courses Page Links ---")
for a in soup.find_all("a", href=True):
    href = a["href"]
    text = a.get_text(strip=True)
    if any(k in href for k in ["course", "view", "id"]):
        if text and len(text) > 3:
            print(f"[{text}] -> {href}")