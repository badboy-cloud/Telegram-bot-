import os
import threading
import asyncio
from dotenv import load_dotenv
from flask import Flask

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackQueryHandler,
    filters
)

# ============== LOAD ENV ==============
load_dotenv()

# 👉 ADD MULTIPLE TOKENS (comma separated in .env)
BOT_TOKENS = os.getenv("BOT_TOKENS").split(",")

ADMIN_ID = int(os.getenv("ADMIN_ID"))
QR_URL = os.getenv("QR_URL")
DOWNLOAD_LINK = os.getenv("DOWNLOAD_LINK")

# Store approved users
APPROVED_USERS = set()

# ============== /start ==============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🎬 Buy App ₹50", callback_data="buy")]]
    await update.message.reply_text(
        "🎥 *Welcome to cinema App Bot!*\n\n"
        "Buy App for ₹50.\n\n"
        "Click below to pay 👇",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ============== CALLBACK ==============
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "buy":
        buttons = [[InlineKeyboardButton("✅ I’ve Paid", callback_data="paid")]]
        try:
            with open(QR_URL, "rb") as photo:
                await query.message.reply_photo(
                    photo=photo,
                    caption = (
                        "💳 *Payment Instructions*\n\n"
                        "1️⃣ Click *Buy App – ₹50*\n"
                        "2️⃣ Scan the QR code & complete payment\n"
                        "3️⃣ Take a clear screenshot (with UTR)\n"
                        "4️⃣ Send the screenshot here 📸\n"
                        "5️⃣ Wait for admin verification ⏳\n"
                        "6️⃣ Get instant app access after approval 🎉\n\n"
                        "⚠️ *Important:*\n"
                        "• Do not close this chat\n"
                        "• Send correct payment proof\n"
                    ),
                    reply_markup=InlineKeyboardMarkup(buttons),
                    parse_mode="Markdown"
                )
        except:
            await query.message.reply_text("⚠️ QR image not found!")

    elif query.data == "paid":
        await query.message.reply_text(
            "📸 Send payment screenshot with UTR number."
        )

# ============== USER PHOTO ==============
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    username = f"@{user.username}" if user.username else user.first_name
    photo_id = update.message.photo[-1].file_id

    await update.message.reply_text(
        "✅ Screenshot received. Wait for admin approval."
    )

    caption = (
        f"📩 *Payment Proof*\n\n"
        f"👤 User: {username}\n"
        f"🆔 User ID: `{user_id}`\n\n"
        f"/approve {user_id}\n"
        f"/reject {user_id}"
    )

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=photo_id,
        caption=caption,
        parse_mode="Markdown"
    )

# ============== APPROVE ==============
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Not authorized")
        return

    if not context.args:
        await update.message.reply_text("Usage: /approve <user_id>")
        return

    user_id = int(context.args[0])

    await context.bot.send_message(
        chat_id=user_id,
        text=(
            "✅ *Payment Approved!*\n\n"
            f"🎬 Download:\n{DOWNLOAD_LINK}\n\nEnjoy!"
        ),
        parse_mode="Markdown"
    )

    APPROVED_USERS.add(user_id)

    await update.message.reply_text(f"✅ Approved {user_id}")

# ============== REJECT ==============
async def reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Not authorized")
        return

    if not context.args:
        await update.message.reply_text("Usage: /reject <user_id>")
        return

    user_id = int(context.args[0])

    await context.bot.send_message(
        chat_id=user_id,
        text=(
            "❌ *Payment Rejected*\n\n"
            "Check:\n• Wrong amount\n• Blur screenshot\n• Duplicate\n\nTry again."
        ),
        parse_mode="Markdown"
    )

    await update.message.reply_text(f"❌ Rejected {user_id}")

# ============== AD PHOTO START ==============
async def ad_photo_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Not authorized")
        return

    context.user_data["ad_photo"] = True
    await update.message.reply_text("📸 Send ad photo now")

# ============== ADMIN AD PHOTO ==============
async def handle_admin_ad_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.user_data.get("ad_photo"):
        return

    context.user_data["ad_photo"] = False

    photo_id = update.message.photo[-1].file_id
    caption = update.message.caption or "📢 *New Update*"

    sent = 0
    for user_id in APPROVED_USERS:
        try:
            await context.bot.send_photo(
                chat_id=user_id,
                photo=photo_id,
                caption=caption,
                parse_mode="Markdown"
            )
            sent += 1
        except:
            pass

    await update.message.reply_text(f"✅ Sent to {sent} users")

# ============== HELP ==============
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start - Buy App\n"
        "/approve <id>\n"
        "/reject <id>\n"
        "/adphoto - Send ad"
    )

# ============== FLASK KEEP ALIVE ==============
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot running"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# ============== CREATE BOT ==========
def create_bot(token):
    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("approve", approve))
    application.add_handler(CommandHandler("reject", reject))
    application.add_handler(CommandHandler("adphoto", ad_photo_start))

    application.add_handler(CallbackQueryHandler(handle_callback))

    application.add_handler(
        MessageHandler(filters.PHOTO & filters.User(ADMIN_ID), handle_admin_ad_photo)
    )
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    return application

# ============== MAIN MULTI BOT ==============
async def run_bot(app):
    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    while True:
        await asyncio.sleep(3600)

async def main():
    threading.Thread(target=run_flask, daemon=True).start()

    apps = [create_bot(token) for token in BOT_TOKENS]

    tasks = [asyncio.create_task(run_bot(app)) for app in apps]

    print("🚀 Multiple Bots Running...")
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
