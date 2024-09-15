import os
import sqlite3
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, CallbackContext
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip

# اطلاعات ادمین و رمز عبور
ADMIN_ID = "Mehrdad13877"  # Replace with your admin's Telegram user ID
ADMIN_PASSWORD = "vid"

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

# چک کردن شماره تلفن‌ها
def is_verified_user(phone_number):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT is_verified FROM users WHERE phone=?", (phone_number,))
    result = cursor.fetchone()
    conn.close()
    return result is not None and result[0] == 1

# دریافت ویدیو از ادمین پس از تأیید رمز عبور
async def request_password(update: Update, context: CallbackContext):
    if update.message.from_user.id == ADMIN_ID:
        keyboard = [[InlineKeyboardButton("Enter Password", callback_data='enter_password')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('برای آپلود ویدیو، رمز عبور خود را وارد کنید:', reply_markup=reply_markup)
    else:
        await update.message.reply_text('شما دسترسی لازم برای این عملیات را ندارید.')

async def button_click(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    if query.data == 'enter_password':
        await query.message.reply_text('لطفاً رمز عبور را وارد کنید:')
        context.user_data['awaiting_password'] = True

async def receive_password_message(update: Update, context: CallbackContext):
    if 'awaiting_password' in context.user_data and context.user_data['awaiting_password']:
        password = update.message.text
        if password == ADMIN_PASSWORD:
            await update.message.reply_text('رمز عبور صحیح است! اکنون ویدیوی خود را آپلود کنید.')
            context.user_data['awaiting_password'] = False
            context.user_data['admin_verified'] = True
        else:
            await update.message.reply_text('رمز عبور اشتباه است! لطفاً دوباره تلاش کنید.')
            context.user_data['awaiting_password'] = False
    elif 'admin_verified' in context.user_data and context.user_data['admin_verified']:
        video_file = await update.message.video.get_file()
        video_path = f'{video_file.file_id}.mp4'
        await video_file.download_to_drive(video_path)

        save_video(video_path)
        video_id = get_last_video_id()
        video_link = generate_video_link(video_id)
        await update.message.reply_text(f'ویدیو با موفقیت ذخیره شد. لینک ویدیو: {video_link}')
        context.user_data['admin_verified'] = False
    else:
        await update.message.reply_text('لطفاً ابتدا رمز عبور را وارد کنید.')

# ایجاد لینک ویدیو
def generate_video_link(video_id):
    return f"http://t.me/Vidsender_bot?start={video_id}"

# هندل کردن دستور استارت با استفاده از پارامتر ویدیو
async def start(update: Update, context: CallbackContext):
    args = context.args  # دریافت آرگومان‌ها (برای لینک ویدیو)
    if len(args) == 1:  # اگر پارامتر ویدیو موجود باشد
        video_id = args[0]
        user = update.message.from_user

        # درخواست شماره تلفن کاربر برای وریفای کردن
        await update.message.reply_text('لطفاً شماره تلفن خود را برای وریفای کردن ارسال کنید.')

        # ذخیره video_id برای بررسی پس از دریافت شماره تلفن
        context.user_data['video_id'] = video_id
    else:
        await update.message.reply_text('به ربات خوش آمدید!')

# هندل کردن دریافت شماره تلفن
async def receive_contact(update: Update, context: CallbackContext):
    user = update.message.contact
    phone_number = user.phone_number

    if is_verified_user(phone_number):
        await update.message.reply_text(f'شماره {phone_number} وریفای شد. در حال ارسال ویدیو...')

        # دریافت video_id از context
        video_id = context.user_data.get('video_id')
        if video_id:
            video_path = get_video_by_id(video_id)
            if video_path:
                await update.message.reply_text(f'ویدیو در حال ارسال است.')
                with open(video_path, 'rb') as video:
                    await update.message.reply_video(video)
            else:
                await update.message.reply_text('ویدیویی با این شناسه پیدا نشد.')
        else:
            await update.message.reply_text('خطا: ویدیو مشخص نشده است.')
    else:
        await update.message.reply_text('شماره شما وریفای نشده است. لطفاً با ادمین تماس بگیرید.')

# آپلود ویدیو توسط ادمین
async def upload_video(update: Update, context: CallbackContext):
    if update.message.from_user.id == ADMIN_ID:  # چک کردن دسترسی ادمین
        video_file = await update.message.video.get_file()
        video_path = f'{video_file.file_id}.mp4'
        await video_file.download_to_drive(video_path)

        save_video(video_path)
        video_id = get_last_video_id()
        video_link = generate_video_link(video_id)
        await update.message.reply_text(f'ویدیو با موفقیت ذخیره شد. لینک ویدیو: {video_link}')
    else:
        await update.message.reply_text('شما دسترسی لازم برای آپلود ویدیو را ندارید.')

# تنظیم ربات
def main():
    # اجرای دیتابیس
    init_db()

    app = ApplicationBuilder().token("7296810348:AAERX18ArzzCRNCRbUEiaOiRNmiVGkyV3oo").build()

    # دستورات
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("upload_video", request_password))
    app.add_handler(MessageHandler(filters.CONTACT, receive_contact))
    app.add_handler(MessageHandler(filters.VIDEO, receive_password_message))

    app.run_polling()

main()
