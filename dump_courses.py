import scraper
from bs4 import BeautifulSoup

client = scraper.get_client()
resp = client.get("https://lms.vit.ac.in/my/courses.php")
soup = BeautifulSoup(resp.text, "html.parser")

print("--- Dumping All Links from /my/courses.php ---")
for a in soup.find_all("a", href=True):
    text = a.get_text(strip=True)
    if text:
        print(f"Text: {text} | Href: {a['href']}")