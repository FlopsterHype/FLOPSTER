import os
import json
import logging
import re
from datetime import time, datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters, JobQueue
from instagrapi import Client

ADMIN_ID = 7311869177
TOKEN = "7879422422:AAG7dno33OdwlpUi94EbDpcXQ7CThm9up2Y"

def get_proxy():
    if os.path.exists("proxy.txt"):
        with open("proxy.txt", "r") as f:
            proxy = f.read().strip()
            return proxy if proxy else None
    return None

def get_config():
    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            return json.load(f)
    return {"time": "10:00"}

logging.basicConfig(filename='bot_log.txt', level=logging.INFO, format='%(asctime)s - %(message)s')
user_states = {}

def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("إضافة حساب ➕", callback_data='add_acc')],
        [InlineKeyboardButton("فحص عدد الريلز 📊", callback_data='check_reels')],
        [InlineKeyboardButton("ضبط وقت النشر ⏰", callback_data='set_time')],
        [InlineKeyboardButton("تغيير البروكسي 🌐", callback_data='set_proxy')],
        [InlineKeyboardButton("نشر تلقائي يومي 🔄", callback_data='auto_post')],
        [InlineKeyboardButton("عرض سجل الأخطاء 📜", callback_data='show_logs')],
        [InlineKeyboardButton("نشر ريلز فوراً 🚀", callback_data='repost_now')]
    ])

def get_proxy_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("إضافة/تعديل بروكسي 📝", callback_data='add_proxy')],
        [InlineKeyboardButton("حذف البروكسي 🗑️", callback_data='del_proxy')],
        [InlineKeyboardButton("رجوع 🔙", callback_data='back')]
    ])

async def daily_repost_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    username = job.data['username']
    target_user = job.data['target']
    session_path = f"sessions/{username}.json"
    try:
        cl = Client()
        proxy = get_proxy()
        if proxy: cl.set_proxy(proxy)
        cl.load_settings(session_path)
        user_id = cl.user_id_from_username(target_user)
        medias = cl.user_medias(user_id, amount=1)
        if medias:
            video_path = cl.video_download(medias[0].pk)
            # رفع الفيديو مع إجبار thumbnail=None لتجاوز FFmpeg
            cl.video_upload(video_path, caption="تم النشر التلقائي", thumbnail=None)
            if os.path.exists(video_path): os.remove(video_path)
            await context.bot.send_message(ADMIN_ID, f"تم النشر التلقائي من {target_user} بنجاح!")
    except Exception as e:
        await context.bot.send_message(ADMIN_ID, f"خطأ في النشر التلقائي: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    await update.message.reply_text("لوحة تحكم الظل الرئيسية:", reply_markup=get_main_keyboard())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    if query.data == 'back':
        await query.edit_message_text("لوحة تحكم الظل الرئيسية:", reply_markup=get_main_keyboard())
    elif query.data == 'set_time':
        user_states[user_id] = 'waiting_for_time'
        await query.edit_message_text("أرسل وقت النشر المطلوب بصيغة HH:MM (مثال: 14:30):")
    elif query.data == 'set_proxy':
        await query.edit_message_text("إدارة البروكسي:", reply_markup=get_proxy_keyboard())
    elif query.data == 'add_proxy':
        user_states[user_id] = 'waiting_for_proxy'
        await query.edit_message_text("أرسل البروكسي الجديد بصيغة: http://user:pass@ip:port")
    elif query.data == 'del_proxy':
        if os.path.exists("proxy.txt"):
            os.remove("proxy.txt")
        await query.edit_message_text("تم حذف البروكسي بنجاح!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع 🔙", callback_data='back')]]))
    elif query.data == 'add_acc':
        user_states[user_id] = 'waiting_for_username'
        await query.edit_message_text("أرسل يوزر الحساب:")
    elif query.data == 'auto_post':
        user_states[user_id] = 'waiting_for_follow_user'
        await query.edit_message_text("أرسل يوزر الحساب الذي تريد المتابعة منه:")
    elif query.data == 'repost_now':
        user_states[user_id] = 'waiting_for_repost'
        await query.edit_message_text("أرسل رابط الريلز ليتم نشره فوراً:")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_states.get(user_id)
    text = update.message.text
    
    if state == 'waiting_for_time':
        with open("config.json", "w") as f:
            json.dump({"time": text}, f)
        await update.message.reply_text(f"تم حفظ وقت النشر بنجاح: {text} بتوقيت سوريا.")
        user_states[user_id] = None
    elif state == 'waiting_for_proxy':
        with open("proxy.txt", "w") as f:
            f.write(text)
        await update.message.reply_text("تم تحديث البروكسي بنجاح!")
        user_states[user_id] = None
    elif state == 'waiting_for_username':
        context.user_data['username'] = text
        await update.message.reply_text("أرسل الكوكيز:")
        user_states[user_id] = 'waiting_for_password'
    elif state == 'waiting_for_password':
        username = context.user_data['username']
        try:
            sessionid = re.search(r'sessionid\s+([^\s]+)', text).group(1)
            csrftoken = re.search(r'csrftoken\s+([^\s]+)', text).group(1)
            cl = Client()
            proxy = get_proxy()
            if proxy: cl.set_proxy(proxy)
            cl.set_settings({"sessionid": sessionid, "csrftoken": csrftoken})
            cl.login_by_sessionid(sessionid)
            cl.dump_settings(f"sessions/{username}.json")
            await update.message.reply_text("تم استيراد الجلسة بنجاح!")
        except Exception as e:
            await update.message.reply_text(f"خطأ: {e}")
        user_states[user_id] = None
    elif state == 'waiting_for_follow_user':
        session_files = os.listdir("sessions")
        if session_files:
            username = session_files[0].replace(".json", "")
            t = get_config()['time'].split(':')
            context.job_queue.run_daily(daily_repost_job, time=time(hour=int(t[0]), minute=int(t[1])), data={'username': username, 'target': text})
            await update.message.reply_text(f"تم تفعيل النشر التلقائي من {text} يومياً الساعة {get_config()['time']} بتوقيت سوريا!")
        user_states[user_id] = None
    elif state == 'waiting_for_repost':
        session_files = os.listdir("sessions")
        if not session_files:
            await update.message.reply_text("لا توجد حسابات!")
            return
        session_path = f"sessions/{session_files[0]}"
        try:
            cl = Client()
            proxy = get_proxy()
            if proxy: cl.set_proxy(proxy)
            try:
                cl.load_settings(session_path)
            except:
                os.remove(session_path)
                await update.message.reply_text("جلسة تالفة، أعد إضافة الحساب.")
                return
            media_pk = cl.media_pk_from_url(text)
            video_path = cl.video_download(media_pk)
            # رفع الفيديو مع إجبار thumbnail=None لتجاوز FFmpeg
            cl.video_upload(video_path, caption="تم النشر", thumbnail=None)
            if os.path.exists(video_path): os.remove(video_path)
            await update.message.reply_text("تم النشر بنجاح!")
        except Exception as e:
            await update.message.reply_text(f"خطأ في النشر: {e}")
        user_states[user_id] = None

if __name__ == '__main__':
    if not os.path.exists("sessions"): os.makedirs("sessions")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
