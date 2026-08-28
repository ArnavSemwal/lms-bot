import os
import httpx
import datetime
from dotenv import load_dotenv
import scraper
import state

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_alert(message, button_url=None, button_text="Open in LMS"):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }
    if button_url:
        payload["reply_markup"] = {
            "inline_keyboard": [[{"text": button_text, "url": button_url}]]
        }
        
    try:
        httpx.post(url, json=payload)
    except Exception as e:
        print(f"❌ Telegram API Error: {e}")

def main():
    print("🚀 Cloud-ready Bot starting...")
    client = scraper.get_client()
    
    print("🔍 Checking session validity...")
    try:
        response = client.get(scraper.DASHBOARD_URL)
        if response.status_code != 200 or "login" in str(response.url):
            print("❌ SESSION EXPIRED (Login keyword found)!")
            send_telegram_alert("⚠️ LMS Session Expired!\nPlease run login.py locally, get new cookies, and update your GitHub Secrets.")
            return 
    except httpx.TooManyRedirects:
        # PRD Task 3: Catching the SSO infinite redirect loop
        print("❌ SESSION EXPIRED (Redirect Loop Detected)!")
        send_telegram_alert("⚠️ LMS Session Expired!\nPlease run login.py locally, get new cookies, and update your GitHub Secrets.")
        return
    except Exception as e:
        print(f"❌ Network issue during session check: {e}")
        return
        
    print("✅ Session is valid. Fetching courses...")
    courses = scraper.fetch_enrolled_courses(client)
    
    current_state = state.load_state()
    assignments_db = current_state.get("assignments", {})
    alerts_sent = 0
    
    for cid, cname in courses.items():
        print(f"Checking {cname}...")
        assigns = scraper.fetch_assignments(client, cid)
        
        for item in assigns:
            aid = item['id']
            title = item['title']
            due = item['due_date']
            link = item['url']
            
            if aid not in assignments_db:
                msg = f"🚨 NEW ASSIGNMENT 🚨\n\n📚 Course: {cname}\n📌 Task: {title}\n⏰ Due: {due}"
                send_telegram_alert(msg, button_url=link)
                alerts_sent += 1
                
                assignments_db[aid] = {
                    "title": title,
                    "course": cname,
                    "due_date": due,
                    "url": link,
                    "reminders_sent": []
                }
                
            elif assignments_db[aid]['due_date'] != due:
                msg = f"⚠️ DEADLINE MOVED ⚠️\n\n📚 Course: {cname}\n📌 Task: {title}\n⏰ New Due Date: {due}"
                send_telegram_alert(msg, button_url=link)
                alerts_sent += 1
                
                assignments_db[aid]['due_date'] = due
                assignments_db[aid]['reminders_sent'] = []
                
    if alerts_sent == 0:
        print("✅ Sab chill hai. No new assignments!")
        
    current_state["assignments"] = assignments_db
    current_state["last_run_at"] = datetime.datetime.now().isoformat()
    state.save_state(current_state)
    print("💾 state.json saved successfully.")

if __name__ == "__main__":
    main()
