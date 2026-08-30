import scraper
from bs4 import BeautifulSoup

client = scraper.get_client()
resp = client.get("https://lms.vit.ac.in/my/courses.php")
soup = BeautifulSoup(resp.text, "html.parser")

print("--- Scanning /my/courses.php ---")
for a in soup.find_all("a", href=True):
    href = a["href"]
    text = a.get_text(strip=True)
    if "course/view.php?id=" in href:
        print(f"[Course Found] Text: {text} | Href: {href}")