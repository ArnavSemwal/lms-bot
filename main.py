import os
import json
from pathlib import Path
import httpx
from dotenv import load_dotenv
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

import scraper
import scaffold_pipeline
import brain

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
STATE_FILE = Path("state.json")
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

def send_telegram_alert(message: str, url: str = None):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    reply_markup = None
    if url:
        keyboard = [[InlineKeyboardButton("Open Assignment", url=url)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
    
    import asyncio
    asyncio.run(bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, reply_markup=reply_markup))

def send_telegram_document(file_path: Path, caption: str):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    import asyncio
    asyncio.run(bot.send_document(chat_id=TELEGRAM_CHAT_ID, document=open(file_path, "rb"), caption=caption))

def main():
    print("Cloud-ready Bot starting...")
    print("Checking session validity...")
    
    client = scraper.get_client()
    if not scraper.verify_session(client):
        print("Session expired! Alerting via Telegram...")
        send_telegram_alert("VIT LMS session expired! Please re-login locally and update COOKIES_JSON secret.")
        return

    print("Session is valid. Fetching enrolled courses...")
    courses = scraper.fetch_enrolled_courses(client)
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

            if assign_id not in state["assignments"]:
                new_found_count += 1
                print(f"New assignment detected: {assign_id} - {assign_title}")
                send_telegram_alert(f"New Assignment Detected!\nCourse: {course['title']}\nTask: {assign_title}", url=assign_url)

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
                            send_telegram_document(docx_path, caption=f"Ideal Solution / Study Guide: {assign_title}")
                            send_telegram_document(pdf_path, caption=f"Original Assignment PDF: {assign_title}")
                    except Exception as e:
                        print(f"⚠️ Error processing attachment for assignment {assign_id}: {e}")

                state["assignments"][assign_id] = {
                    "title": assign_title,
                    "course": course['title'],
                    "url": assign_url,
                    "notified": True
                }
                save_state(state)

    if new_found_count == 0:
        print("No new assignments found across any course. State is up to date.")
    else:
        print(f"Successfully processed {new_found_count} new assignments!")

if __name__ == "__main__":
    main()
