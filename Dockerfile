FROM python:3.11-slim
# Install tesseract and deps (including Vietnamese tessdata)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential tesseract-ocr tesseract-ocr-vie libtesseract-dev libleptonica-dev pkg-config poppler-utils \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONUNBUFFERED=1
CMD ["python", "telegram_gpt_bot_ocr.py"]
