"""
auto_login.py

Fully automated LMS login — no manual step required, since the account
has no CAPTCHA and no MFA. Used as a fallback whenever the cached
session cookie turns out to be invalid.

Credentials come from environment variables (GitHub Secrets in the cloud
workflow, or a local .env file for testing) — never hardcoded, never
committed.
"""

import os
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

LMS_LOGIN_URL = "https://lms.vit.ac.in/login/index.php"
DASHBOARD_URL_FRAGMENT = "/my/"


def auto_login(headless: bool = True) -> list[dict]:
    """Logs into LMS using LMS_USERNAME/LMS_PASSWORD env vars and returns
    the resulting session cookies as a list of dicts (Playwright's native
    cookie format)."""
    username = os.environ["LMS_USERNAME"]
    password = os.environ["LMS_PASSWORD"]

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
        )
        context = browser.new_context()
        page = context.new_page()
        page.goto(LMS_LOGIN_URL)

        # Adjust these selectors if VIT's login form field names differ —
        # inspect the actual login page once to confirm.
        page.fill('input[name="username"]', username)
        page.fill('input[name="password"]', password)
        page.click('button[type="submit"], input[type="submit"]')

        page.wait_for_url(f"**{DASHBOARD_URL_FRAGMENT}**", timeout=30_000)

        cookies = context.cookies()
        browser.close()
        return cookies


def save_cookies(cookies: list[dict], path: Path) -> None:
    path.write_text(json.dumps(cookies, indent=2))


if __name__ == "__main__":
    # Manual test run: `LMS_USERNAME=... LMS_PASSWORD=... python auto_login.py`
    cookies = auto_login(headless=False)  # headless=False so you can watch it work the first time
    save_cookies(cookies, Path("cookies.json"))
    print(f"Logged in successfully, {len(cookies)} cookies saved to cookies.json")
