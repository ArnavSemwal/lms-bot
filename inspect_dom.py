import scraper
from bs4 import BeautifulSoup

client = scraper.get_client()
resp = client.get("https://lms.vit.ac.in/my/")
soup = BeautifulSoup(resp.text, "html.parser")

print("--- Scanning DOM for Course Cards ---")
for tag in soup.find_all(True):
    classes = tag.get("class", [])
    class_str = " ".join(classes) if isinstance(classes, list) else str(classes)
    href = tag.get("href", "")
    if "course" in class_str.lower() or "card" in class_str.lower() or "course" in href.lower():
        text = tag.get_text(strip=True)
        if text and len(text) < 80:
            print(f"[{tag.name}] Class: {class_str} | Href: {href} | Text: {text}")