import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone
import httpx
from dotenv import load_dotenv
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

load_dotenv()

import scraper
import scaffold_pipeline
import brain
import auto_login
import reminder

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
STATE_FILE = Path("state.json")
COOKIES_FILE = Path("cookies.json")
TEMP_DIR = Path("temp_downloads")
TEMP_DIR.mkdir(exist_ok=True)

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"assignments": {}, "last_run_at": None}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def send_telegram_alert(message: str, url: str = None, chat_id: str = None):
    target_chat = chat_id or TELEGRAM_CHAT_ID
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    reply_markup = None
    if url:
        keyboard = [[InlineKeyboardButton("Open Assignment", url=url)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
    
    import asyncio
    asyncio.run(bot.send_message(chat_id=target_chat, text=message, reply_markup=reply_markup))

def send_telegram_document(file_path: Path, caption: str, chat_id: str = None):
    target_chat = chat_id or TELEGRAM_CHAT_ID
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    import asyncio
    asyncio.run(bot.send_document(chat_id=target_chat, document=open(file_path, "rb"), caption=caption))

def main(target_course=None, target_chat_id=None):
    print("Cloud-ready Bot starting...")
    print("Checking session validity...")
    
    client = scraper.get_client()
    if not scraper.verify_session(client):
        print("Session expired! Triggering automated Playwright re-login...")
        try:
            cookies = auto_login.auto_login(headless=True)
            auto_login.save_cookies(cookies, COOKIES_FILE)
            print("Auto-login successful! Fresh cookies saved.")
            client = scraper.get_client()
        except Exception as e:
            print(f"⚠️ Auto-login failed: {e}")
            send_telegram_alert("VIT LMS session expired and auto-login failed! Please check credentials.", chat_id=target_chat_id)
            return

    print("Session is valid. Fetching enrolled courses...")
    courses = scraper.fetch_enrolled_courses(client)
    
    if target_course:
        course_map = {
            "os-lab": "Operating Systems",
            "data-structures": "Data Structures"
        }
        search_term = course_map.get(target_course, target_course).lower()
        courses = [c for c in courses if search_term in c['title'].lower()]
        print(f"Filtering for specific course: {target_course}. Found {len(courses)} match(es).")
    else:
        print(f"Found {len(courses)} enrolled courses to monitor.")

    state = load_state()
    new_found_count = 0

    for course in courses:
        print(f"Checking course: {course['title']}")
        assignments = scraper.fetch_course_assignments(client, course)
        print(f"Found {len(assignments)} assignments in {course['title']}.")

        for assign in assignments:
            assign_id = assign["id"]
            assign_url = assign["url"]
            assign_title = assign["title"]
            due_date = assign.get("due_date")

            if assign_id not in state["assignments"]:
                new_found_count += 1
                print(f"New assignment detected: {assign_id} - {assign_title}")
                send_telegram_alert(f"New Assignment Detected!\nCourse: {course['title']}\nTask: {assign_title}", url=assign_url, chat_id=target_chat_id)

                print("Locating real attachment PDF link from assignment page...")
                real_pdf_url = scraper.get_assignment_pdf_url(client, assign_url)
                print(f"Found PDF URL: {real_pdf_url}")

                if "pluginfile.php" in real_pdf_url or real_pdf_url.endswith(".pdf"):
                    print("Downloading attachment...")
                    pdf_filename = f"Assignment_{assign_id}.pdf"
                    pdf_path = TEMP_DIR / pdf_filename
                    try:
                        scaffold_pipeline.download_attachment(real_pdf_url, dict(client.cookies), pdf_path)
                        
                        print("Extracting text and running AI Brain...")
                        text = scaffold_pipeline.extract_text(pdf_path)
                        
                        study_guide = brain.generate_study_guide(text, pdf_filename)
                        
                        if study_guide:
                            docx_filename = f"Assignment_{assign_id}_Study_Guide.docx"
                            docx_path = TEMP_DIR / docx_filename
                            print("Packaging study guide into Word document (.docx)...")
                            scaffold_pipeline.scaffold_markdown_to_docx(study_guide, f"Study Guide — {assign_title}", docx_path)
                            
                            print("Dropping document and attachment via Telegram...")
                            send_telegram_document(docx_path, caption=f"Ideal Solution / Study Guide: {assign_title}", chat_id=target_chat_id)
                            send_telegram_document(pdf_path, caption=f"Original Assignment PDF: {assign_title}", chat_id=target_chat_id)
                    except Exception as e:
                        print(f"⚠️ Error processing attachment for assignment {assign_id}: {e}")

                state["assignments"][assign_id] = {
                    "title": assign_title,
                    "course": course['title'],
                    "url": assign_url,
                    "due_date": due_date if due_date else "2026-12-31T23:59:59+00:00",
                    "reminders_sent": [],
                    "notified": True
                }
                save_state(state)

    print("Checking assignment reminders...")
    state = reminder.check_reminders(
        state, 
        datetime.now(timezone.utc), 
        lambda msg: send_telegram_alert(msg, chat_id=target_chat_id)
    )
    save_state(state)

    if new_found_count == 0:
        print("No new assignments found. State is up to date.")
        if target_chat_id:
            send_telegram_alert("Check complete! Koi nayi assignment nahi mili. Sab kuch up-to-date hai! 🎯", chat_id=target_chat_id)
    else:
        print(f"Successfully processed {new_found_count} new assignments!")
        if target_chat_id:
            send_telegram_alert(f"Check complete! {new_found_count} nayi assignment process ho gayi.", chat_id=target_chat_id)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VIT LMS Bot")
    parser.add_argument("--course", type=str, help="Specific course to check (e.g., os-lab)", default=None)
    parser.add_argument("--chat-id", type=str, help="Telegram chat ID to reply to", default=None)
    args = parser.parse_args()
    
    main(target_course=args.course, target_chat_id=args.chat_id)