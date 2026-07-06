import os
import logging
from yt_dlp import YoutubeDL

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ---------------- إعدادات ----------------
BOT_TOKEN = "8236899701:AAGAV6LuJ4gXcJq7JhmW_Ca_ePvuWKWgPFI"
COOKIES_FILE = "cookies.txt"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎧 أرسل اسم أغنية أو رابط يوتيوب")

# ---------------- البحث (أقوى نسخة) ----------------
def search(query: str):
    ydl_opts = {
        "quiet": True,
        "noplaylist": True,
        "default_search": "ytsearch1",
        "extract_flat": True,
        "geo_bypass": True,
        "http_headers": {
            "User-Agent": "Mozilla/5.0"
        },
    }

    if os.path.exists(COOKIES_FILE):
        ydl_opts["cookiefile"] = COOKIES_FILE

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch1:{query}", download=False)

        if info and "entries" in info and len(info["entries"]) > 0:
            vid = info["entries"][0].get("id")
            return f"https://www.youtube.com/watch?v={vid}"

    return None

# ---------------- تحميل (الحل النهائي) ----------------
def download(url: str):
    os.makedirs("downloads", exist_ok=True)

    ydl_opts = {
        # 🔥 أهم حل: لا نحدد format صارم
        "format": "bestaudio/best",
        "outtmpl": "downloads/%(id)s.%(ext)s",

        "noplaylist": True,
        "geo_bypass": True,
        "retries": 10,
        "fragment_retries": 10,

        "http_headers": {
            "User-Agent": "Mozilla/5.0"
        },

        "cookiefile": COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,

        # 🔥 هذا يحل مشاكل بعض الفيديوهات
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"]
            }
        },

        "ignoreerrors": True,
        "quiet": True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

        # 🔥 الملف الحقيقي من id (أكثر استقرار)
        file_base = f"downloads/{info['id']}"

        # نبحث عن أي امتداد ممكن
        for ext in ["m4a", "webm", "mp3", "opus"]:
            path = file_base + "." + ext
            if os.path.exists(path):
                return path, info

        # fallback أخير
        raise Exception("No downloaded file found")

# ---------------- MAIN ----------------
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    await update.message.reply_text("🎧 جاري البحث...")

    try:
        # رابط أو بحث
        if "youtube.com" in text or "youtu.be" in text:
            url = text
        else:
            url = search(text)

            if not url:
                await update.message.reply_text("❌ لم يتم العثور على الأغنية")
                return

        await update.message.reply_text("⬇️ جاري التحميل...")

        file_path, info = download(url)

        if not file_path or not os.path.exists(file_path):
            await update.message.reply_text("❌ فشل التحميل")
            return

        with open(file_path, "rb") as audio:
            await update.message.reply_audio(
                audio=audio,
                title=info.get("title"),
                performer=info.get("uploader")
            )

        os.remove(file_path)

    except Exception as e:
        await update.message.reply_text(f"❌ خطأ:\n{e}")

# ---------------- تشغيل ----------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
