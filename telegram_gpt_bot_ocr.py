#!/usr/bin/env python3
# coding: utf-8
"""
Telegram GPT Bot (Extended) - OCR (Vietnamese), PDF report with watermark, simple web fetch.
CONFIG (via environment variables):
- TELEGRAM_BOT_TOKEN
- OPENAI_API_KEY
- OPENAI_MODEL (optional, default gpt-5)
- MEDIA_DIR (optional, default /tmp/telegram_media)
- WEB_SCRAPE_ENABLED (optional, "1" to allow fetching user-provided URLs)
- WATERMARK_TEXT (optional)
Notes:
- Requires Tesseract OCR and Vietnamese language data installed in system for OCR to work.
- Do NOT hard-code API keys. Use environment variables in Render or your server.
"""

import os, time, logging, tempfile, requests
from collections import deque
from typing import Dict, List
from PIL import Image
import telebot, openai, pytesseract
from io import BytesIO

# PDF generation
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
except Exception:
    canvas = None

# Configuration
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5")
MEDIA_DIR = os.getenv("MEDIA_DIR", "/tmp/telegram_media")
WEB_SCRAPE_ENABLED = os.getenv("WEB_SCRAPE_ENABLED", "0") == "1"
WATERMARK_TEXT = os.getenv("WATERMARK_TEXT", "Mr.P 0922372220")

if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    raise RuntimeError("TELEGRAM_BOT_TOKEN and OPENAI_API_KEY required in environment")

openai.api_key = OPENAI_API_KEY

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("telegram_gpt_bot_ocr")

bot = telebot.TeleBot(TELEGRAM_TOKEN, parse_mode="HTML")

# in-memory context per user
user_context: Dict[int, deque] = {}
def ensure_context(uid: int):
    if uid not in user_context:
        user_context[uid] = deque(maxlen=24)

def push_user(uid:int, text:str):
    ensure_context(uid)
    user_context[uid].append({"role":"user","content":text})

def push_assistant(uid:int, text:str):
    ensure_context(uid)
    user_context[uid].append({"role":"assistant","content":text})

SYSTEM_PROMPT = (
    "Bạn là trợ lý chuyên gia giám định bảo hiểm xe cơ giới cho Mr.P. "
    "Trả lời ngắn gọn, chính xác, nêu nguyên nhân, mức độ lỗi, tài liệu cần thu thập, và bước xử lý tiếp theo. "
    "Sử dụng tiếng Việt. Trả lời thẳng, không vòng vo."
)

def build_messages(uid:int, system_prompt: str = SYSTEM_PROMPT) -> List[dict]:
    ensure_context(uid)
    msgs = [{"role":"system","content":system_prompt}] + list(user_context[uid])
    return msgs

def call_openai(messages:List[dict], max_tokens:int=800):
    resp = openai.ChatCompletion.create(model=OPENAI_MODEL, messages=messages, temperature=0.2, max_tokens=max_tokens)
    return resp["choices"][0]["message"]["content"].strip()

def ocr_image(path_or_bytes) -> str:
    # Accepts file path or bytes
    try:
        if isinstance(path_or_bytes, (bytes, bytearray)):
            img = Image.open(BytesIO(path_or_bytes))
        else:
            img = Image.open(path_or_bytes)
        # Vietnamese language: 'vie' (make sure tesseract data installed)
        text = pytesseract.image_to_string(img, lang='vie')
        return text.strip()
    except Exception as e:
        logger.exception("OCR failed")
        return ""

def fetch_url_text(url: str) -> str:
    if not WEB_SCRAPE_ENABLED:
        return ""
    try:
        headers = {"User-Agent":"Mozilla/5.0 (compatible)"}
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(r.text, "html.parser")
        texts = soup.get_text(separator=" ", strip=True)
        return texts[:3000]
    except Exception as e:
        logger.exception("fetch_url_text failed")
        return ""

def generate_pdf(uid:int, title:str, content:str) -> str:
    os.makedirs(MEDIA_DIR, exist_ok=True)
    fname = f"report_{uid}_{int(time.time())}.pdf"
    fpath = os.path.join(MEDIA_DIR, fname)
    if canvas:
        c = canvas.Canvas(fpath, pagesize=A4)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, 800, "BÁO CÁO GIÁM ĐỊNH - GIC Assistant")
        c.setFont("Helvetica", 10)
        c.drawString(50, 780, f"Người dùng Telegram ID: {uid}")
        c.drawString(50, 760, f"Tiêu đề: {title}")
        text_obj = c.beginText(50, 740)
        for line in content.splitlines():
            text_obj.textLine(line)
            if text_obj.getY() < 80:
                c.drawText(text_obj); c.showPage(); text_obj = c.beginText(50,800)
        c.drawText(text_obj)
        # watermark
        c.setFont("Helvetica-Oblique", 8)
        c.drawString(50, 30, WATERMARK_TEXT)
        c.save()
        return fpath
    else:
        txt = fpath + ".txt"
        with open(txt, "w", encoding="utf-8") as f:
            f.write("BÁO CÁO GIÁM ĐỊNH\n\n")
            f.write(f"Người dùng: {uid}\nTiêu đề: {title}\n\n")
            f.write(content)
            f.write("\n\n" + WATERMARK_TEXT)
        return txt

# --- Handlers ---
@bot.message_handler(commands=['start'])
def cmd_start(m):
    ensure_context(m.from_user.id)
    user_context[m.from_user.id].clear()
    bot.reply_to(m, "Chào! Gửi ảnh hiện trường, PDF biên bản hoặc mô tả vụ việc để tôi phân tích. Gõ 'tạo báo cáo' để xuất PDF.")

@bot.message_handler(content_types=['photo'])
def handle_photo(m):
    uid = m.from_user.id
    file_id = m.photo[-1].file_id
    f = bot.get_file(file_id)
    data = bot.download_file(f.file_path)
    os.makedirs(MEDIA_DIR, exist_ok=True)
    local = os.path.join(MEDIA_DIR, f"{uid}_{file_id}.jpg")
    with open(local, "wb") as fp:
        fp.write(data)
    bot.reply_to(m, "Ảnh đã lưu, đang chạy OCR (Tiếng Việt)...")
    ocr_text = ocr_image(data)
    if ocr_text:
        bot.reply_to(m, "OCR phát hiện văn bản (rút gọn):\n" + (ocr_text[:800] + ("..." if len(ocr_text)>800 else "")))
        push_user(uid, "[OCR] " + ocr_text)
    else:
        push_user(uid, "[Ảnh đính kèm]")
    # run quick analysis
    msgs = build_messages(uid)
    try:
        ans = call_openai(msgs, max_tokens=700)
        push_assistant(uid, ans)
        bot.reply_to(m, ans)
    except Exception:
        bot.reply_to(m, "Lỗi khi phân tích. Thử lại sau.")

@bot.message_handler(content_types=['document'])
def handle_document(m):
    uid = m.from_user.id
    doc = m.document
    fname = doc.file_name
    f = bot.get_file(doc.file_id)
    data = bot.download_file(f.file_path)
    os.makedirs(MEDIA_DIR, exist_ok=True)
    local = os.path.join(MEDIA_DIR, f"{uid}_{doc.file_id}_{fname}")
    with open(local, "wb") as fp:
        fp.write(data)
    bot.reply_to(m, f"Đã lưu tài liệu: {fname}")
    if fname.lower().endswith(".pdf"):
        bot.reply_to(m, "Nếu cần trích xuất nội dung, gửi lệnh: trich xuat <đường dẫn hoặc tên file>.") 
        push_user(uid, "[PDF] " + local)

@bot.message_handler(func=lambda m: True, content_types=['text'])
def handle_text(m):
    uid = m.from_user.id
    text = m.text.strip()
    # quick web fetch: user can send "fetch <url>" to add snippet
    if text.lower().startswith("fetch "):
        url = text.split(" ",1)[1].strip()
        bot.reply_to(m, f"Đang fetch nội dung từ: {url} (nếu chức năng bật)")
        snippet = fetch_url_text(url)
        if snippet:
            bot.reply_to(m, "Trích xuất nội dung (rút gọn):\n" + snippet[:800])
            push_user(uid, "[WEB] " + snippet)
        else:
            bot.reply_to(m, "Không lấy được nội dung. Chức năng crawl có thể tắt hoặc URL không cho phép.")
        return
    if text.lower().startswith("trich xuat") or text.lower().startswith("trích xuất"):
        bot.reply_to(m, "Bắt đầu trích xuất PDF (nếu có).")
        push_user(uid, "[Yêu cầu trích xuất PDF] " + text)
        msgs = build_messages(uid)
        try:
            ans = call_openai(msgs, max_tokens=700)
            push_assistant(uid, ans)
            bot.reply_to(m, ans)
        except Exception:
            bot.reply_to(m, "Lỗi khi trích xuất.")
        return
    if text.lower().startswith("tạo báo cáo") or "tạo báo cáo" in text.lower() or "báo cáo" in text.lower():
        bot.reply_to(m, "Đang tạo báo cáo PDF...")
        msgs = build_messages(uid)
        try:
            analysis = call_openai(msgs, max_tokens=900)
            push_assistant(uid, analysis)
            pdf = generate_pdf(uid, "Báo cáo từ Bot", analysis)
            bot.reply_to(m, f"Báo cáo tạo xong: {pdf}")
        except Exception:
            bot.reply_to(m, "Lỗi khi tạo báo cáo.")
        return
    # default: feed to OpenAI
    push_user(uid, text)
    msgs = build_messages(uid)
    try:
        ans = call_openai(msgs, max_tokens=700)
        push_assistant(uid, ans)
        bot.reply_to(m, ans)
    except Exception:
        bot.reply_to(m, "Lỗi khi gọi AI. Thử lại sau.")

if __name__ == "__main__":
    logger.info("Bot OCR starting...")
    bot.infinity_polling(timeout=60,long_polling_timeout=60)
