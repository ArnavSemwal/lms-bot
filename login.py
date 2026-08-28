import json
from playwright.sync_api import sync_playwright

def login_and_save_cookies():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        print("🚀 Browser khul gaya! Fatafat credentials daal aur CAPTCHA solve maar.")
        page.goto("https://lms.vit.ac.in/login/index.php")
        
        print("⏳ Waiting for you to bypass CAPTCHA and hit the dashboard...")
        
        try:
            page.wait_for_url("https://lms.vit.ac.in/my/*", timeout=120000)
            
            print("✅ Dashboard access secured! Cookies rip kar raha hoon...")
            cookies = context.cookies()
            
            with open("cookies.json", "w") as f:
                json.dump(cookies, f, indent=4)
                
            print("🔥 cookies.json successfully updated. Browser closing now.")
            
        except Exception as e:
            print("❌ Time out ya error ho gaya. Wapas run kar aur jaldi solve karna!")
            print(f"Details: {e}")
            
        finally:
            browser.close()

if __name__ == "__main__":
    login_and_save_cookies()
