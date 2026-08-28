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

    print("Session is valid. Fetching courses...")
    courses = scraper.fetch_enrolled_courses(client)
    print(f"Found {len(courses)} enrolled courses to monitor.")

    assignment_url = "https://lms.vit.ac.in/mod/assign/view.php?id=21334"
    assignment_id = "21334"

    state = load_state()

    if assignment_id not in state["assignments"]:
        print(f"New assignment detected: {assignment_id}")
        send_telegram_alert("New Assignment Detected!\nCourse: Operating Systems Lab\nTask: MLFQ Scheduling", url=assignment_url)

        print("Locating real attachment PDF link from assignment page...")
        real_pdf_url = scraper.get_assignment_pdf_url(client, assignment_url)
        print(f"Found PDF URL: {real_pdf_url}")

        print("Downloading attachment...")
        pdf_path = TEMP_DIR / "Lab_8_MLFQ.pdf"
        scaffold_pipeline.download_attachment(real_pdf_url, dict(client.cookies), pdf_path)
        
        print("Extracting text and running AI Brain...")
        text = scaffold_pipeline.extract_text(pdf_path)
        
        study_guide = brain.generate_study_guide(text, "Lab_8_MLFQ.pdf")
        
        if study_guide:
            docx_path = TEMP_DIR / "Lab_8_MLFQ_Study_Guide.docx"
            print("Packaging study guide into Word document (.docx)...")
            scaffold_pipeline.scaffold_markdown_to_docx(study_guide, "Lab 8 Study Guide — MLFQ", docx_path)
            
            print("Dropping document and attachment via Telegram...")
            send_telegram_document(docx_path, caption="Ideal Assignment Solution / Study Guide")
            send_telegram_document(pdf_path, caption="Original Assignment PDF")
            
            state["assignments"][assignment_id] = {
                "title": "Lab 8 MLFQ",
                "url": assignment_url,
                "notified": True
            }
            save_state(state)
            print("Pipeline executed successfully and state updated!")
    else:
        print("No new assignments found. State is up to date.")

if __name__ == "__main__":
    main()
