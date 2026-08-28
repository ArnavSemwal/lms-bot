import json
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

COOKIES_PATH = os.getenv("COOKIES_PATH", "cookies.json")
DASHBOARD_URL = "https://lms.vit.ac.in/my/"

def verify_saved_session():
    if not os.path.exists(COOKIES_PATH):
        print(f"Error: {COOKIES_PATH} file nahi mili. Pehle login.py run karo.")
        return False

    with open(COOKIES_PATH, "r") as f:
        cookies_list = json.load(f)

    cookie_dict = {c["name"]: c["value"] for c in cookies_list}

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    print("Checking session validity via lightweight GET request...")
    # Added verify=False to bypass local SSL certificate validation issues
    with httpx.Client(cookies=cookie_dict, headers=headers, follow_redirects=True, verify=False) as client:
        response = client.get(DASHBOARD_URL)

        if "login/index.php" in str(response.url) or response.status_code == 401:
            print("❌ Session Invalid/Expired! Please re-run login.py")
            return False
        
        if "Dashboard" in response.text or "My courses" in response.text or response.status_code == 200:
            print("✅ Session Active & Valid! Successfully accessed LMS dashboard.")
            return True
        else:
            print("⚠️ Status 200 mila par Dashboard keyword verify nahi hua. Check URL:")
            print(response.url)
            return False

if __name__ == "__main__":
    verify_saved_session()
