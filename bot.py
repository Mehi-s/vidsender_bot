import os
import sqlite3
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip

# رمز ادمین برای آپلود ویدیو
ADMIN_PASSWORD = "vid2024sender"

# دیتابیس برای ذخیره ویدیوها و شماره تلفن‌ها
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS videos
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, video_path TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS users
                      (phone TEXT PRIMARY KEY, is_verified INTEGER)''')
    conn.commit()
    conn.close()

# ذخیره ویدیو در دیتابیس
def save_video(video_path):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO videos (video_path) VALUES (?)", (video_path,))
    conn.commit()
    conn.close()

# دریافت آخرین آی‌دی ویدیو
def get_last_video_id():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM videos ORDER BY id DESC LIMIT 1")
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

# دریافت ویدیو بر اساس آی‌دی
def get_video_by_id(video_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT video_path FROM videos WHERE id=?", (video_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

# بررسی تأیید شماره تلفن
def is_verified(phone):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT is_verified FROM users WHERE phone=?", (phone,))
    result = cursor.fetchone()
    conn.close()
    return result[0] == 1 if result else False

# ذخیره شماره تلفن در دیتابیس
def save_phone(phone):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO users (phone, is_verified) VALUES (?, ?)", (phone, 0))
    conn.commit()
    conn.close()

# تأیید شماره تلفن توسط ادمین
def verify_phone(phone):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_verified = 1 WHERE phone=?", (phone,))
    conn.commit()
    conn.close()

# افزودن واترمارک به ویدیو با moviepy
def add_watermark(input_video, output_video, watermark_text):
    video = VideoFileClip(input_video)
    
    # ایجاد کلیپ متنی برای واترمارک
    watermark = TextClip(watermark_text, fontsize=24, color='white').set_duration(video.duration)
    watermark = watermark.set_position(('left', 'bottom')).set_opacity(0.7)
    
    # ترکیب واترمارک با ویدیو
    final_video = CompositeVideoClip([video, watermark])
    final_video.write_videofile(output_video, codec='libx264')

# دریافت ویدیو توسط ادمین با رمز
async def receive_video(update: Update, context: CallbackContext):
    if len(context.args) != 1 or context.args[0] != ADMIN_PASSWORD:
        await update.message.reply_text('دسترسی غیرمجاز! رمز اشتباه است.')
        return
    
    video_file = await update.message.video.get_file()
    video_path = f'{video_file.file_id}.mp4'
    await video_file.download_to_drive(video_path)

    save_video(video_path)
    await update.message.reply_text('ویدئو با موفقیت ذخیره شد.')

    # ایجاد لینک ویدیو
    video_id = get_last_video_id()
    video_link = f"http://your_bot_url.com/video/{video_id}"
    await update.message.reply_text(f'لینک ویدیو: {video_link}')

# دریافت لینک ویدیو و درخواست شماره تلفن
async def handle_video_link(update: Update, context: CallbackContext):
    video_id = context.args[0]
    phone = update.message.text  # شماره تلفن کاربر

    save_phone(phone)  # ذخیره شماره تلفن در دیتابیس
    await update.message.reply_text(f'شماره {phone} ثبت شد. لطفا منتظر تأیید ادمین باشید.')

# تأیید شماره تلفن توسط ادمین
async def verify_user(update: Update, context: CallbackContext):
    if len(context.args) != 1:
        await update.message.reply_text('لطفا شماره تلفن مورد نظر برای تأیید را وارد کنید.')
        return
    
    phone = context.args[0]
    verify_phone(phone)
    await update.message.reply_text(f'شماره {phone} با موفقیت تأیید شد.')

# ارسال ویدیو پس از تأیید شماره تلفن
async def request_video(update: Update, context: CallbackContext):
    video_id = context.args[0]
    phone = update.message.text  # شماره تلفن کاربر

    if is_verified(phone):  # بررسی تأیید شماره تلفن
        video_path = get_video_by_id(video_id)
        if video_path:
            watermarked_video = f'watermarked_{phone}.mp4'
            add_watermark(video_path, watermarked_video, phone)

            # ارسال ویدیو واترمارک شده
            with open(watermarked_video, 'rb') as f:
                await update.message.reply_video(video=InputFile(f))
        else:
            await update.message.reply_text('ویدئویی برای ارسال وجود ندارد.')
    else:
        await update.message.reply_text('شماره تلفن شما تأیید نشده است.')

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text('سلام! برای استفاده از ربات، شماره تلفن خود را وارد کنید.')

# تنظیم ربات
def main():
    # اجرای دیتابیس
    init_db()

    app = ApplicationBuilder().token("7296810348:AAERX18ArzzCRNCRbUEiaOiRNmiVGkyV3oo").build()

    # دستورات
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("upload_video", receive_video))
    app.add_handler(CommandHandler("verify", verify_user))
    app.add_handler(MessageHandler(filters.Regex(r'^http://your_bot_url.com/video/(\d+)$'), handle_video_link))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, request_video))

    app.run_polling()

main()
