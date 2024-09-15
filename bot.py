import os
import sqlite3
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, CallbackContext
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip

# رمز ادمین برای آپلود ویدیو
ADMIN_PASSWORD = "vidsender2024"

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

# افزودن واترمارک به ویدیو با moviepy
def add_watermark(input_video, output_video, watermark_text):
    video = VideoFileClip(input_video)
    
    # ایجاد کلیپ متنی برای واترمارک
    watermark = TextClip(watermark_text, fontsize=24, color='white').set_duration(video.duration)
    watermark = watermark.set_position(('left', 'bottom')).set_opacity(0.7)
    
    # ترکیب واترمارک با ویدیو
    final_video = CompositeVideoClip([video, watermark])
    final_video.write_videofile(output_video, codec='libx264')

# مدیریت شماره تلفن‌ها: افزودن و حذف
def add_verified_phone(phone_number):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (phone, is_verified) VALUES (?, 1)", (phone_number,))
    conn.commit()
    conn.close()

def remove_verified_phone(phone_number):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE phone=?", (phone_number,))
    conn.commit()
    conn.close()

# درخواست رمز عبور از ادمین
async def request_password(update: Update, context: CallbackContext):
    keyboard = [[InlineKeyboardButton("Enter Password", callback_data='enter_password')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('برای آپلود ویدیو، رمز عبور خود را وارد کنید:', reply_markup=reply_markup)

# دریافت رمز عبور و اعتبارسنجی
async def button_click(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    if query.data == 'enter_password':
        await query.message.reply_text('لطفا رمز عبور را وارد کنید:')
        context.user_data['awaiting_password'] = True

# دریافت ویدیو از ادمین پس از تأیید رمز عبور
async def receive_password_message(update: Update, context: CallbackContext):
    if 'awaiting_password' in context.user_data and context.user_data['awaiting_password']:
        password = update.message.text
        if password == ADMIN_PASSWORD:
            await update.message.reply_text('رمز عبور صحیح است! اکنون ویدیوی خود را آپلود کنید.')
            context.user_data['awaiting_password'] = False
            context.user_data['admin_verified'] = True
        else:
            await update.message.reply_text('رمز عبور اشتباه است! لطفا دوباره تلاش کنید.')
            context.user_data['awaiting_password'] = False
    elif 'admin_verified' in context.user_data and context.user_data['admin_verified']:
        video_file = await update.message.video.get_file()
        video_path = f'{video_file.file_id}.mp4'
        await video_file.download_to_drive(video_path)

        save_video(video_path)
        video_id = get_last_video_id()
        video_link = f"http://your_bot_url.com/video/{video_id}"
        await update.message.reply_text(f'ویدئو با موفقیت ذخیره شد. لینک ویدیو: {video_link}')
        context.user_data['admin_verified'] = False
    else:
        await update.message.reply_text('لطفا ابتدا رمز عبور را وارد کنید.')

# افزودن شماره تلفن وریفای شده
async def add_phone(update: Update, context: CallbackContext):
    if len(context.args) != 1:
        await update.message.reply_text('لطفا شماره تلفن را به درستی وارد کنید. مثال: /add_phone 09123456789')
        return
    phone_number = context.args[0]
    add_verified_phone(phone_number)
    await update.message.reply_text(f'شماره {phone_number} با موفقیت اضافه شد.')

# حذف شماره تلفن وریفای شده
async def remove_phone(update: Update, context: CallbackContext):
    if len(context.args) != 1:
        await update.message.reply_text('لطفا شماره تلفن را به درستی وارد کنید. مثال: /remove_phone 09123456789')
        return
    phone_number = context.args[0]
    remove_verified_phone(phone_number)
    await update.message.reply_text(f'شماره {phone_number} با موفقیت حذف شد.')

# تنظیم ربات
def main():
    # اجرای دیتابیس
    init_db()

    app = ApplicationBuilder().token("7296810348:AAERX18ArzzCRNCRbUEiaOiRNmiVGkyV3oo").build()

    # دستورات
    app.add_handler(CommandHandler("upload_video", request_password))
    app.add_handler(CommandHandler("add_phone", add_phone))
    app.add_handler(CommandHandler("remove_phone", remove_phone))
    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(MessageHandler(filters.VIDEO | filters.TEXT, receive_password_message))

    app.run_polling()

main()
