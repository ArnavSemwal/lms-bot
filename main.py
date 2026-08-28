import os
import httpx
from dotenv import load_dotenv
import scraper
import db

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        res = httpx.post(url, json=payload)
        if res.status_code == 200:
            print("📲 Telegram notification sent successfully!")
        else:
            print(f"⚠️ Telegram API issue: {res.text}")
    except Exception as e:
        print(f"❌ Network error while sending alert: {e}")

def main():
    print("🚀 Bot is waking up... scanning LMS for fresh trauma!")
    
    # DB initialize kar rahe hain
    db.init_db()
    
    # Scraper ko cookies pakda ke start kar rahe hain
    client = scraper.get_client()
    courses = scraper.fetch_enrolled_courses(client)
    
    if not courses:
        print("Bruh, no courses found. Session expire toh nahi ho gaya?")
        return

    total_alerts = 0
    
    for cid, cname in courses.items():
        print(f"Checking updates for {cname}...")
        assigns = scraper.fetch_assignments(client, cid)
        
        # DB me daal ke purane data se diff nikal rahe hain
        updates = db.save_and_get_diff(cname, assigns)
        
        for update in updates:
            data = update['data']
            if update['type'] == 'NEW':
                msg = (f"🚨 <b>NEW ASSIGNMENT ALERT</b> 🚨\n\n"
                       f"📚 <b>Course:</b> {cname}\n"
                       f"📌 <b>Task:</b> {data['title']}\n"
                       f"⏰ <b>Due:</b> {data['due_date']}\n"
                       f"🔗 <a href='{data['url']}'>Click to open LMS</a>")
                send_telegram_alert(msg)
                total_alerts += 1
                
            elif update['type'] == 'UPDATED':
                msg = (f"⚠️ <b>ASSIGNMENT UPDATED</b> ⚠️\n\n"
                       f"📚 <b>Course:</b> {cname}\n"
                       f"📌 <b>Task:</b> {data['title']}\n"
                       f"⏰ <b>New Status/Due:</b> {data['due_date']}\n"
                       f"🔗 <a href='{data['url']}'>Click to check</a>")
                send_telegram_alert(msg)
                total_alerts += 1
                
    if total_alerts == 0:
        print("✅ Sab chill hai. No new assignments!")

if __name__ == "__main__":
    main()
