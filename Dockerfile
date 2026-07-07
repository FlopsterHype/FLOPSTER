# استخدام نسخة خفيفة من بايثون
FROM python:3.11-slim

# تثبيت FFmpeg ونظام التشغيل اللازم
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# ضبط المجلد الأساسي
WORKDIR /app

# نسخ المكتبات وتثبيتها
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ باقي الكود
COPY . .

# تشغيل البوت
CMD ["python", "main.py"]

