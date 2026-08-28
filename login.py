import json
import os
import sys
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

COOKIES_PATH = os.getenv("COOKIES_PATH", "cookies.json")
LMS_LOGIN_URL = "https://lms.vit.ac.in/login/index.php"
DASHBOARD_URL_KEYWORD = "my"

def perform_manual_login():
    print("Browser launch ho raha hai...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        print(f"Opening login page: {LMS_LOGIN_URL}")
        page.goto(LMS_LOGIN_URL)

        print("\n" + "="*50)
        print("ACTION REQUIRED: Browser me login aur CAPTCHA complete karo.")
        print("Dashboard load hone tak wait karo...")
        print("="*50 + "\n")

        try:
            page.wait_for_url(f"**/{DASHBOARD_URL_KEYWORD}**", timeout=180000)
            print("Login successful detect ho gaya!")
            
            cookies = context.cookies()
            with open(COOKIES_PATH, "w") as f:
                json.dump(cookies, f, indent=2)
            
            print(f"Session cookies successfully saved to: {COOKIES_PATH}")
        except Exception as e:
            print(f"Login wait timeout ya error: {e}")
            sys.exit(1)
        finally:
            browser.close()

if __name__ == "__main__":
    perform_manual_login()
