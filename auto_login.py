import os, json
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

LMS_LOGIN_URL = "https://lms.vit.ac.in/login/index.php"
DASHBOARD_URL_FRAGMENT = "/my/"

def auto_login(headless: bool = True) -> list[dict]:
    username = os.environ["LMS_USERNAME"]
    password = os.environ["LMS_PASSWORD"]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()
        page.goto(LMS_LOGIN_URL)
        page.fill("input[name=\"username\"]", username)
        page.fill("input[name=\"password\"]", password)
        page.click("button[type=\"submit\"], input[type=\"submit\"]")
        page.wait_for_url(f"**{DASHBOARD_URL_FRAGMENT}**", timeout=30_000)
        cookies = context.cookies()
        browser.close()
        return cookies

def save_cookies(cookies: list[dict], path: Path) -> None:
    path.write_text(json.dumps(cookies, indent=2))

if __name__ == "__main__":
    cookies = auto_login(headless=False)
    save_cookies(cookies, Path("cookies.json"))
    print(f"Logged in successfully, {len(cookies)} cookies saved to cookies.json")
