# VIT LMS Bot

An automated bot for the VIT LMS that scrapes assignments, generates study guides, and sends notifications via Telegram.

## Features
- Fetches new assignments from the VIT LMS.
- Automatically downloads PDF attachments.
- Uses Grok (xAI) API to generate highly structured study guides.
- Converts study guides to DOCX format.
- Sends instant notifications to a Telegram chat.

## Prerequisites
- Python 3.10+
- `pip install -r requirements.txt`
- Install Playwright browsers: `playwright install chromium`

## Environment Setup
Create a `.env` file in the root directory:
```env
LMS_USERNAME=your_username
LMS_PASSWORD=your_password
TELEGRAM_BOT_TOKEN=your_telegram_token
TELEGRAM_CHAT_ID=your_chat_id
XAI_API_KEY=your_xai_api_key
```

## Running the Bot
```bash
python main.py
```
