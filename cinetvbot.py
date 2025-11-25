from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from flask import Flask
import threading

# === CONFIG ===
BOT_TOKEN = "8448965403:AAGHPZ5fw6hbi_rexedkRf50rBRQ9FmK-9Y"      # put your token here
ADMIN_ID = 6205742667             # your user ID
QR_URL = "pay50.png"              # QR image must be in same folder
DOWNLOAD_LINK = "https://cinetv24.netlify.app/cinefile"  # app link

# === /start command ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🎬 Buy CineTv App ₹50", callback_data="buy")]]
    await update.message.reply_text(
        "🎥 *Welcome to CineTv App Bot!*\n\n"
        "Buy our official movie app for just ₹50.\n\n"
        "Click below to start payment:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# === handle button clicks ===
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "buy":
        buttons = [[InlineKeyboardButton("✅ I’ve Paid", callback_data="paid")]]

        # Send QR image
        try:
            with open(QR_URL, "rb") as photo:
                await query.message.reply_photo(
                    photo=photo,
                    caption=(
                        "💳 *Payment Instructions:*\n\n"
                        "1️⃣ Scan the QR code using Google Pay / PhonePe / Paytm\n"
                        "2️⃣ Pay ₹50 and take a screenshot\n"
                        "3️⃣ Send it here for verification\n\n"
                        "⚠️ Don’t close this chat until verification"
                    ),
                    reply_markup=InlineKeyboardMarkup(buttons),
                    parse_mode="Markdown"
                )
        except:
            await query.message.reply_text("⚠️ QR file not found!")

    elif query.data == "paid":
        await query.message.reply_text("📸 Please send your payment screenshot here for verification.")

# === handle photo uploads (payment proofs) ===
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    username = f"@{user.username}" if user.username else user.first_name
    photo_id = update.message.photo[-1].file_id

    await update.message.reply_text("✅ Screenshot received! We’ll verify and send your app soon.")

    caption = f"📩 Payment proof from {username}\nUser ID: {user_id}"
    await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo_id, caption=caption)

# === /approve command for admin ===
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        if context.args:
            user_id = int(context.args[0])
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "✅ *Payment verified!*\n\n"
                    f"Here’s your CineTv App download link:\n👉 {DOWNLOAD_LINK}\n\n"
                    "Enjoy watching 🎬"
                ),
                parse_mode="Markdown"
            )
            await update.message.reply_text(f"✅ Download link sent to user {user_id}.")
        else:
            await update.message.reply_text("Usage: /approve <user_id>")
    else:
        await update.message.reply_text("❌ You’re not authorized for this command.")

# === /help command ===
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Use /start to buy the CineTv App for ₹50.")

# === Flask for keep-alive ===
app = Flask(__name__)

@app.route('/')
def home():
    return "CineTv Telegram Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# === Main ===
def main():
    threading.Thread(target=run_flask, daemon=True).start()

    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(CommandHandler("approve", approve))
    application.add_handler(CommandHandler("help", help_command))

    print("🚀 CineTv Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()