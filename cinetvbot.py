import os
import threading
import asyncio
import sqlite3
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

BOT_TOKENS = os.getenv("BOT_TOKENS").split(",")

ADMIN_ID = int(os.getenv("ADMIN_ID"))
QR_URL = os.getenv("QR_URL")
DOWNLOAD_LINK = os.getenv("DOWNLOAD_LINK")

# ============== DATABASE ==============
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY
)
""")
conn.commit()

def add_user(user_id):
    try:
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
    except:
        pass

def get_users():
    cursor.execute("SELECT user_id FROM users")
    return [row[0] for row in cursor.fetchall()]

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
                    caption=(
                        "💳 *Payment Instructions*\n\n"
                        "1️⃣ Click on “Buy App – ₹50”\n"
                        "2️⃣ Scan the QR code and complete the ₹50 payment\n"
                        "3️⃣ Take a screenshot of the payment\n"
                        "4️⃣ Send the screenshot here\n"
                        "5️⃣ Admin will verify your payment\n"
                        "6️⃣ After verification, the app will be sent to you instantly\n\n"
                        "⚠️ Do not close chat"
                    ),
                    reply_markup=InlineKeyboardMarkup(buttons),
                    parse_mode="Markdown"
                )
        except:
            await query.message.reply_text("⚠️ QR image not found!")

    elif query.data == "paid":
        await query.message.reply_text("📸 Send screenshot with UTR.")

# ============== USER PHOTO ==============
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    username = f"@{user.username}" if user.username else user.first_name
    photo_id = update.message.photo[-1].file_id

    await update.message.reply_text("✅ Screenshot received. Wait for approval.")

    caption = (
        f"📩 *Payment Proof*\n\n"
        f"👤 {username}\n"
        f"🆔 `{user_id}`\n\n"
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
        return

    if not context.args:
        await update.message.reply_text("Usage: /approve <id>")
        return

    user_id = int(context.args[0])

    await context.bot.send_message(
        chat_id=user_id,
        text=f"✅ Approved!\n\n🎬 {DOWNLOAD_LINK}"
    )

    add_user(user_id)  # ✅ SAVE PERMANENTLY

    await update.message.reply_text("✅ User saved permanently")

# ============== REJECT ==============
async def reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    user_id = int(context.args[0])

    await context.bot.send_message(
        chat_id=user_id,
        text="❌ Payment rejected. Try again."
    )

# ============== USERS ==============
async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    users = get_users()

    if not users:
        await update.message.reply_text("No users.")
        return

    text = "\n".join(map(str, users))
    await update.message.reply_text(f"📋 Users:\n\n{text}")

# ============== BROADCAST ==============
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    message = " ".join(context.args)
    users = get_users()

    sent = 0
    for user_id in users:
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
            sent += 1
        except:
            pass

    await update.message.reply_text(f"Sent to {sent}")

# ============== FLASK KEEP ALIVE ==============
app = Flask(__name__)

@app.route("/")
def home():
    return "Running"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# ============== CREATE BOT ==========
def create_bot(token):
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(CommandHandler("reject", reject))
    app.add_handler(CommandHandler("users", list_users))
    app.add_handler(CommandHandler("broadcast", broadcast))

    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    return app

# ============== RUN MULTIPLE ==========
async def run_bot(app):
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    while True:
        await asyncio.sleep(3600)

async def main():
    threading.Thread(target=run_flask, daemon=True).start()

    apps = [create_bot(token) for token in BOT_TOKENS]
    await asyncio.gather(*[run_bot(app) for app in apps])

if __name__ == "__main__":
    asyncio.run(main())
