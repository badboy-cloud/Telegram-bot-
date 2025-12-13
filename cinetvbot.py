from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from flask import Flask
import threading

# ================= CONFIG =================
BOT_TOKEN = "8448965403:AAGHPZ5fw6hbi_rexedkRf50rBRQ9FmK-9Y"
ADMIN_ID = 6205742667
QR_URL = "pay50.png"  # QR image in same folder
DOWNLOAD_LINK = "https://cinetv-24.netlify.app/"

# ================= /start =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🎬 Buy CineTv App ₹50", callback_data="buy")]]
    await update.message.reply_text(
        "🎥 *Welcome to CineTv App Bot!*\n\n"
        "Buy our official movie app for just ₹50.\n\n"
        "Click below to start payment 👇",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ================= CALLBACK HANDLER =================
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # BUY BUTTON
    if query.data == "buy":
        buttons = [[InlineKeyboardButton("✅ I’ve Paid", callback_data="paid")]]
        try:
            with open(QR_URL, "rb") as photo:
                await query.message.reply_photo(
                    photo=photo,
                    caption=(
                        "💳 *Payment Instructions*\n\n"
                        "1️⃣ Scan the QR\n"
                        "2️⃣ Pay ₹50\n"
                        "3️⃣ Take screenshot\n"
                        "4️⃣ Click *I’ve Paid* and send screenshot\n\n"
                        "⚠️ Do not close this chat"
                    ),
                    reply_markup=InlineKeyboardMarkup(buttons),
                    parse_mode="Markdown"
                )
        except:
            await query.message.reply_text("⚠️ QR image not found!")

    # PAID BUTTON
    elif query.data == "paid":
        await query.message.reply_text("📸 Please send your payment screenshot.")

    # APPROVE BUTTON (ADMIN)
    elif query.data.startswith("approve_"):
        if query.from_user.id == ADMIN_ID:
            user_id = int(query.data.split("_")[1])
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "✅ *Payment Verified!*\n\n"
                    f"🎬 Download CineTv App:\n👉 {DOWNLOAD_LINK}\n\n"
                    "Enjoy watching!"
                ),
                parse_mode="Markdown"
            )
            await query.message.reply_text("✅ Approved & link sent.")
        else:
            await query.answer("Not authorized", show_alert=True)

    # REJECT BUTTON (ADMIN)
    elif query.data.startswith("reject_"):
        if query.from_user.id == ADMIN_ID:
            user_id = int(query.data.split("_")[1])
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "❌ *Payment Rejected*\n\n"
                    "Your payment could not be verified.\n\n"
                    "Possible reasons:\n"
                    "• Wrong amount\n"
                    "• Unclear screenshot\n"
                    "• Already used payment\n\n"
                    "Please try again or contact admin."
                ),
                parse_mode="Markdown"
            )
            await query.message.reply_text("❌ Rejected & user notified.")
        else:
            await query.answer("Not authorized", show_alert=True)

# ================= PHOTO HANDLER =================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    username = f"@{user.username}" if user.username else user.first_name
    photo_id = update.message.photo[-1].file_id

    await update.message.reply_text(
        "✅ Screenshot received!\nPlease wait for verification."
    )

    admin_buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}")
        ]
    ])

    caption = (
        f"📩 *Payment Proof*\n\n"
        f"👤 User: {username}\n"
        f"🆔 ID: `{user_id}`"
    )

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=photo_id,
        caption=caption,
        reply_markup=admin_buttons,
        parse_mode="Markdown"
    )

# ================= COMMANDS =================
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Use /start to buy CineTv App.")

# ================= FLASK KEEP ALIVE =================
app = Flask(__name__)

@app.route('/')
def home():
    return "CineTv Bot is running!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# ================= MAIN =================
def main():
    threading.Thread(target=run_flask, daemon=True).start()

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("🚀 CineTv Bot Running...")
    application.run_polling()

if __name__ == "__main__":
    main()
