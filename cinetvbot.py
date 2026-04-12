from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackQueryHandler,
    filters
)
from flask import Flask
import threading

# ============== CONFIG ==============
BOT_TOKEN = "8426456955:AAG1o0E8Vnsk2rtppsHJpxnIy5Q37rNVgpA"
ADMIN_ID = 5952004262
QR_URL = "pay50.png"
DOWNLOAD_LINK = "https://cine-tv24.netlify.app/"

# Store approved users (for ads)
APPROVED_USERS = set()

# ============== /start ==============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🎬 Buy App ₹50", callback_data="buy")]]
    await update.message.reply_text(
        "🎥 *Welcome to App Bot!*\n\n"
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
            await query.message.reply_text("⚠️ QR image not found!")

    elif query.data == "paid":
        await query.message.reply_text(
            "📸 Please send your payment screenshot with UTR number."
        )

# ============== USER PAYMENT PHOTO HANDLER ==============
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    username = f"@{user.username}" if user.username else user.first_name
    photo_id = update.message.photo[-1].file_id

    await update.message.reply_text(
        "✅ Screenshot received.\nPlease wait for admin approval."
    )

    caption = (
        f"📩 *Payment Proof*\n\n"
        f"👤 User: {username}\n"
        f"🆔 User ID: `{user_id}`\n\n"
        f"Use:\n"
        f"/approve {user_id}\n"
        f"/reject {user_id}"
    )

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=photo_id,
        caption=caption,
        parse_mode="Markdown"
    )

# ============== /approve COMMAND ==============
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Not authorized.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /approve <user_id>")
        return

    user_id = int(context.args[0])

    await context.bot.send_message(
        chat_id=user_id,
        text=(
            "✅ *Payment Approved!*\n\n"
            f"🎬 Download link:\n👉 {DOWNLOAD_LINK}\n\n"
            "Enjoy watching!"
        ),
        parse_mode="Markdown"
    )

    APPROVED_USERS.add(user_id)

    await update.message.reply_text(f"✅ Approved user {user_id}")

# ============== /reject COMMAND ==============
async def reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Not authorized.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /reject <user_id>")
        return

    user_id = int(context.args[0])

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

    await update.message.reply_text(f"❌ Rejected user {user_id}")

# ============== /adphoto COMMAND (ADMIN) ==============
async def ad_photo_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Not authorized.")
        return

    context.user_data["ad_photo"] = True
    await update.message.reply_text(
        "📸 Send the photo now.\n"
        "Caption is optional — it will be sent as the ad."
    )

# ============== ADMIN PHOTO AD HANDLER ==============
async def handle_admin_ad_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.user_data.get("ad_photo"):
        return

    context.user_data["ad_photo"] = False

    photo_id = update.message.photo[-1].file_id
    caption = update.message.caption or "📢 *New Update from CineTv*"

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

    await update.message.reply_text(f"✅ Photo ad sent to {sent} users")

# ============== HELP ==============
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Commands:\n"
        "/start – Buy App\n"
        "/approve <user_id> – Approve payment (admin)\n"
        "/reject <user_id> – Reject payment (admin)\n"
        "/adphoto – Send photo ad (admin)"
    )

# ============== FLASK KEEP ALIVE ==============
app = Flask(__name__)

@app.route("/")
def home():
    return "CineTv Bot is running"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# ============== MAIN ==============
def main():
    threading.Thread(target=run_flask, daemon=True).start()

    application = Application.builder().token(BOT_TOKEN).build()

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

    print("🚀 Bot Running...")
    application.run_polling()

if __name__ == "__main__":
    main()
