import os
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

COOKIES_FILE = Path("cookies.json")
LOGIN_URL = "https://lms.vit.ac.in/login/index.php"

def auto_login(headless=True):
    username = os.environ["LMS_USERNAME"]
    password = os.environ["LMS_PASSWORD"]
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        context = browser.new_context()
        page = context.new_page()
        
        print("Navigating to LMS login page...")
        page.goto(LOGIN_URL, timeout=60000)
        
        print("Filling credentials...")
        page.fill("#username", username)
        page.fill("#password", password)
        page.click("#loginbtn")
        
        print("Waiting for login to complete...")
        page.wait_for_url("**/my/**", timeout=60000)
        print("Login successful!")
        
        cookies = context.cookies()
        browser.close()
        return cookies

def save_cookies(cookies, path=COOKIES_FILE):
    with open(path, "w") as f:
        json.dump(cookies, f, indent=2)
    print(f"Cookies saved to {path}")

if __name__ == "__main__":
    cookies = auto_login(headless=False)
    save_cookies(cookies)