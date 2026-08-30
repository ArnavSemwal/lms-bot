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
import filters

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
    client = scraper.get_client()
    if not scraper.verify_session(client):
        print("Session expired! Triggering automated Playwright re-login...")
        try:
            cookies = auto_login.auto_login(headless=True)
            auto_login.save_cookies(cookies, COOKIES_FILE)
            client = scraper.get_client()
        except Exception as e:
            print(f"Warning: Auto-login failed: {e}")
            send_telegram_alert("VIT LMS session expired and auto-login failed! Please check credentials.", chat_id=target_chat_id)
            return

    courses = scraper.fetch_enrolled_courses(client)
    state = load_state()
    new_found_count = 0
    allowlist = filters.load_allowlist()

    for course in courses:
        assignments = scraper.fetch_course_assignments(client, course["id"])
        
        for assign in assignments:
            assign_id = assign["id"]
            assign_url = assign["url"]
            assign_title = assign["title"]

            if not filters.is_allowed(assign_title, course["title"], allowlist):
                filters.log_blocked(assign_title, course["title"])
                continue

            # Agar already state mein hai, toh bas check karlo ki kya ab submit ho gayi?
            if assign_id in state["assignments"]:
                if not state["assignments"][assign_id].get("submitted", False):
                    details = scraper.get_assignment_details(client, assign_url)
                    if details.get("is_submitted"):
                        print(f"Task '{assign_title}' is now marked as SUBMITTED!")
                        state["assignments"][assign_id]["submitted"] = True
                        save_state(state)
                continue

            print(f"Checking details for: {assign_title}")
            details = scraper.get_assignment_details(client, assign_url)
            
            # Agar brand new hai aur already submit ho chuka hai, silent entry maaro
            if details.get("is_submitted"):
                print(f"Skipping '{assign_title}' — Already submitted!")
                state["assignments"][assign_id] = {
                    "title": assign_title,
                    "course": course['title'],
                    "url": assign_url,
                    "reminders_sent": [],
                    "notified": True,
                    "submitted": True
                }
                save_state(state)
                continue

            # Agar nayi hai aur pending hai, tabhi aage badho
            new_found_count += 1
            print(f"New pending task detected: {assign_title}")
            send_telegram_alert(f"New Assignment Detected!\nCourse: {course['title']}\nTask: {assign_title}", url=assign_url, chat_id=target_chat_id)

            real_pdf_url = details.get("pdf_url")
            if real_pdf_url and ("pluginfile.php" in real_pdf_url or real_pdf_url.endswith(".pdf")):
                print("Downloading attachment...")
                pdf_filename = f"Assignment_{assign_id}.pdf"
                pdf_path = TEMP_DIR / pdf_filename
                try:
                    scaffold_pipeline.download_attachment(real_pdf_url, dict(client.cookies), pdf_path)
                    text = scaffold_pipeline.extract_text(pdf_path)
                    study_guide = brain.generate_study_guide(text, pdf_filename)
                    
                    if study_guide:
                        docx_filename = f"Assignment_{assign_id}_Study_Guide.docx"
                        docx_path = TEMP_DIR / docx_filename
                        scaffold_pipeline.scaffold_markdown_to_docx(study_guide, f"Study Guide - {assign_title}", docx_path)
                        send_telegram_document(docx_path, caption=f"Ideal Solution / Study Guide: {assign_title}", chat_id=target_chat_id)
                        send_telegram_document(pdf_path, caption=f"Original Assignment PDF: {assign_title}", chat_id=target_chat_id)
                except Exception as e:
                    print(f"Warning: Error processing attachment for assignment {assign_id}: {e}")

            state["assignments"][assign_id] = {
                "title": assign_title,
                "course": course['title'],
                "url": assign_url,
                "reminders_sent": [],
                "notified": True,
                "submitted": False
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
        print("No new pending assignments found.")
        if target_chat_id:
            send_telegram_alert("Check complete! Koi nayi pending assignment nahi mili.", chat_id=target_chat_id)
    else:
        if target_chat_id:
            send_telegram_alert(f"Check complete! {new_found_count} nayi assignments process ho gayi.", chat_id=target_chat_id)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VIT LMS Bot")
    parser.add_argument("--course", type=str, help="Specific course", default=None)
    parser.add_argument("--chat-id", type=str, help="Telegram chat ID", default=None)
    args = parser.parse_args()
    main(target_course=args.course, target_chat_id=args.chat_id)