# Telegram GPT Bot with OCR (Vietnamese), PDF report, basic web fetch

## Features
- OCR (Vietnamese) for uploaded images (requires Tesseract and vie tessdata)
- Generate PDF report with watermark "Mr.P 0922372220"
- Simple web fetch: use "fetch <url>" to add webpage content into analysis (must enable WEB_SCRAPE_ENABLED=1)
- Commands:
  - /start
  - fetch <url>
  - trich xuat <...>  (trích xuất PDF)
  - tạo báo cáo / báo cáo

## Quick start (local)
1. Install Tesseract on your system and Vietnamese tessdata.
   - Debian/Ubuntu example:
     sudo apt-get update && sudo apt-get install -y tesseract-ocr tesseract-ocr-vie
2. Install Python deps:
   pip install -r requirements.txt
3. Set env vars:
   export TELEGRAM_BOT_TOKEN="..."
   export OPENAI_API_KEY="..."
   export WEB_SCRAPE_ENABLED="1"   # optional
   export WATERMARK_TEXT="Mr.P 0922372220"
4. Run:
   python telegram_gpt_bot_ocr.py

## Deploy on Render (recommended)
- Use Dockerfile (Render will build image including tesseract)
- Push repo to GitHub, create Web Service on Render linking to this repo
- Set Environment Variables on Render:
  - TELEGRAM_BOT_TOKEN
  - OPENAI_API_KEY
  - WEB_SCRAPE_ENABLED (optional)
  - WATERMARK_TEXT (optional)
  - MEDIA_DIR (optional)
- Start command (if not using Dockerfile): python telegram_gpt_bot_ocr.py

## Security
- NEVER commit secrets into GitHub.
- Revoke any keys accidentally shared.
