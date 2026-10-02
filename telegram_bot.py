import os
import sys
import subprocess
import datetime
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# Keep a global reference to the current interval (in hours)
# We start with the value from .env or default to 4
try:
    current_interval_hours = float(os.getenv("CHECK_INTERVAL_HOURS", 4))
except ValueError:
    current_interval_hours = 4.0

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🟢 LMS Bot is running!\n\n"
        "Commands you can use:\n"
        "/checknow - Force an immediate LMS check\n"
        f"/setinterval <hours> - Change the background check interval (current: {current_interval_hours} hrs)\n"
        "/status - Check current interval and status"
    )

async def check_lms_job(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{current_time}] Running scheduled LMS check via Telegram Bot...")
    
    # Run the existing main.py logic as a subprocess so we don't block the async bot loop
    process = await asyncio.create_subprocess_exec(
        sys.executable, "main.py", "--chat-id", str(chat_id),
        stdout=sys.stdout, stderr=sys.stderr
    )
    await process.communicate()
    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Check complete.\n")

async def force_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Running LMS check immediately...")
    # Run synchronously or as subprocess for immediate feedback
    process = await asyncio.create_subprocess_exec(
        sys.executable, "main.py", "--chat-id", str(update.message.chat_id),
        stdout=sys.stdout, stderr=sys.stderr
    )
    await process.communicate()
    await update.message.reply_text("✅ Immediate check complete.")

async def set_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_interval_hours
    if not context.args:
        await update.message.reply_text("⚠️ Please provide the hours. Example: /setinterval 2")
        return

    try:
        new_hours = float(context.args[0])
        if new_hours <= 0:
            raise ValueError()
    except ValueError:
        await update.message.reply_text("⚠️ Invalid number. Please provide a positive number of hours (e.g., 1.5 or 3).")
        return

    current_interval_hours = new_hours
    
    # Remove existing jobs
    current_jobs = context.job_queue.get_jobs_by_name("lms_check_job")
    for job in current_jobs:
        job.schedule_removal()
        
    # Schedule the new job
    interval_seconds = int(new_hours * 3600)
    context.job_queue.run_repeating(
        check_lms_job, 
        interval=interval_seconds, 
        first=interval_seconds, # wait the interval before running again
        chat_id=update.message.chat_id,
        name="lms_check_job"
    )
    
    await update.message.reply_text(f"✅ Background check interval updated to **{new_hours} hours**.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🟢 Bot is running.\n⏳ Current interval: {current_interval_hours} hours.")

def main():
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not found in .env file.")
        return

    print("🤖 Starting Interactive Telegram Bot...")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("checknow", force_check))
    app.add_handler(CommandHandler("setinterval", set_interval))
    app.add_handler(CommandHandler("status", status))

    # We need a default chat ID to run the initial job if nobody interacts with it yet.
    # It will use the one in .env
    default_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if default_chat_id:
        interval_seconds = int(current_interval_hours * 3600)
        app.job_queue.run_repeating(
            check_lms_job, 
            interval=interval_seconds, 
            first=10, # Run the first check 10 seconds after bot starts
            chat_id=default_chat_id,
            name="lms_check_job"
        )
        print(f"Scheduled default job for chat {default_chat_id} every {current_interval_hours} hours.")
    else:
        print("⚠️ No TELEGRAM_CHAT_ID in .env. You must send /start to the bot to start receiving checks.")

    print("Listening for messages... Send /start to your bot on Telegram!")
    app.run_polling()

if __name__ == "__main__":
    # Ensure Windows asyncio works correctly with subprocesses
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    main()
