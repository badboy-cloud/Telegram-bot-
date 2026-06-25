import os
import asyncio
import psycopg2
import traceback
import sys
from datetime import datetime
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackQueryHandler,
    filters
)
from telegram.error import TelegramError

# ============== LOAD ENV ==============
print("[DEBUG] Loading environment variables...", file=sys.stderr)
load_dotenv()

BOT_TOKENS = os.getenv("BOT_TOKENS", "").split(",")
BOT_TOKENS = [token.strip() for token in BOT_TOKENS if token.strip()]

print(f"[DEBUG] BOT_TOKENS loaded: {len(BOT_TOKENS)} token(s)", file=sys.stderr)
if not BOT_TOKENS:
    print("[ERROR] No BOT_TOKENS found in .env file!", file=sys.stderr)
    sys.exit(1)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("[ERROR] DATABASE_URL not found in .env file!", file=sys.stderr)
    sys.exit(1)

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
QR_PATH = "pay50.png"
DOWNLOAD_LINK = os.getenv("DOWNLOAD_LINK", "")

print(f"[DEBUG] ADMIN_ID: {ADMIN_ID}", file=sys.stderr)
print(f"[DEBUG] QR_PATH: {QR_PATH}", file=sys.stderr)
print(f"[DEBUG] DOWNLOAD_LINK: {DOWNLOAD_LINK}", file=sys.stderr)

# ============== DATABASE ==============
def get_db_connection():
    """Get PostgreSQL database connection"""
    try:
        conn = psycopg2.connect(
            DATABASE_URL,
            sslmode="require"
        )
        return conn
    except psycopg2.Error as e:
        print("Database error:", e, file=sys.stderr)
        return None

def init_database():
    """Initialize PostgreSQL database with required tables"""
    conn = get_db_connection()
    if not conn:
        print("[ERROR] Failed to connect to database", file=sys.stderr)
        return False
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS pending_payments (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            utr TEXT,
            status TEXT DEFAULT 'pending'
        )
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        print("[DEBUG] Database initialized successfully", file=sys.stderr)
        return True
    except psycopg2.Error as e:
        print("Database error:", e, file=sys.stderr)
        if conn:
            conn.close()
        return False

# Initialize database on startup
init_database()

def get_all_users():
    """Get all approved users"""
    try:
        conn = get_db_connection()
        if not conn:
            return []
        
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        users = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return users
    except psycopg2.Error as e:
        print("Database error:", e, file=sys.stderr)
        return []

def get_pending_payments():
    """Get all pending payments"""
    try:
        conn = get_db_connection()
        if not conn:
            return []
        
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, username, utr FROM pending_payments WHERE status = 'pending'")
        payments = cursor.fetchall()
        cursor.close()
        conn.close()
        return payments
    except psycopg2.Error as e:
        print("Database error:", e, file=sys.stderr)
        return []

def add_user(user_id, username, first_name, utr=None):
    """Add user to approved users"""
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
            (user_id,)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except psycopg2.Error as e:
        print("Database error:", e, file=sys.stderr)
        return False

def add_pending_payment(user_id, username, first_name, utr, photo_file_id):
    """Add pending payment"""
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO pending_payments (user_id, username, utr, status) VALUES (%s, %s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET username = %s, utr = %s, status = %s",
            (user_id, username, utr, 'pending', username, utr, 'pending')
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except psycopg2.Error as e:
        print("Database error:", e, file=sys.stderr)
        return False

def remove_user(user_id):
    """Remove user from database"""
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except psycopg2.Error as e:
        print("Database error:", e, file=sys.stderr)
        return False

def get_user_count():
    """Get total approved users"""
    try:
        conn = get_db_connection()
        if not conn:
            return 0
        
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return count
    except psycopg2.Error as e:
        print("Database error:", e, file=sys.stderr)
        return 0

def remove_pending_payment(user_id):
    """Remove pending payment"""
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pending_payments WHERE user_id = %s", (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except psycopg2.Error as e:
        print("Database error:", e, file=sys.stderr)
        return False

def get_payment_details(user_id):
    """Get pending payment details for user"""
    try:
        conn = get_db_connection()
        if not conn:
            return None
        
        cursor = conn.cursor()
        cursor.execute("SELECT username, utr FROM pending_payments WHERE user_id = %s AND status = 'pending'", (user_id,))
        payment = cursor.fetchone()
        cursor.close()
        conn.close()
        return payment
    except psycopg2.Error as e:
        print("Database error:", e, file=sys.stderr)
        return None

def is_user_approved(user_id):
    """Check if user is already approved"""
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result is not None
    except psycopg2.Error as e:
        print("Database error:", e, file=sys.stderr)
        return False

# ============== /START ==============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - show welcome message"""
    try:
        user = update.message.from_user
        keyboard = [[InlineKeyboardButton("🛒 Buy App ₹50", callback_data="buy")]]
        
        await update.message.reply_text(
            "🎥 *Welcome to Cinemain App Bot!*\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "✨ Premium App Features:\n"
            "• Unlimited streaming\n"
            "• HD quality content\n"
            "• Offline download\n"
            "• Ad-free experience\n\n"
            "💰 *Special Price: ₹50 Only*\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "Click button below to proceed 👇",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    except TelegramError:
        pass
    except Exception:
        pass

# ============== CALLBACK QUERY ==============
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all callback queries"""
    query = update.callback_query
    user = query.from_user
    user_id = user.id
    
    try:
        await query.answer()
        
        if query.data == "buy":
            keyboard = [[InlineKeyboardButton("✅ I've Paid", callback_data="paid_confirm")]]
            
            try:
                if os.path.exists(QR_PATH):
                    with open(QR_PATH, "rb") as photo:
                        await query.message.reply_photo(
                            photo=photo,
                            caption=(
                                "💳 *Payment Instructions*\n\n"
                                "━━━━━━━━━━━━━━━━━━\n"
                                "1️⃣ Scan QR code above\n"
                                "2️⃣ Pay ₹50 via UPI/Bank\n"
                                "3️⃣ Take screenshot\n"
                                "4️⃣ Copy UTR number\n\n"
                                "━━━━━━━━━━━━━━━━━━\n\n"
                                "📸 *Send:*\n"
                                "• Payment screenshot\n"
                                "• UTR number\n\n"
                                "⏱️ Approval in 5-10 mins"
                            ),
                            reply_markup=InlineKeyboardMarkup(keyboard),
                            parse_mode="Markdown"
                        )
                else:
                    await query.message.reply_text(
                        "⚠️ QR image not found"
                    )
            except TelegramError:
                await query.message.reply_text("❌ Error loading QR. Please contact admin.")
                
        elif query.data == "paid_confirm":
            await query.message.reply_text(
                "📸 *Send Payment Proof:*\n\n"
                "• Screenshot of payment\n"
                "• UTR/Reference number\n\n"
                "Format: Screenshot + UTR"
            )
            context.user_data['waiting_for_payment'] = True
            
    except TelegramError:
        pass
    except Exception:
        pass

# ============== PHOTO HANDLER ==============
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo uploads for payment"""
    try:
        user = update.message.from_user
        user_id = user.id
        username = f"@{user.username}" if user.username else user.first_name or "User"
        first_name = user.first_name or "Unknown"
        photo_file_id = update.message.photo[-1].file_id
        
        # Extract UTR from caption if provided
        utr = "Not provided"
        if update.message.caption:
            utr = update.message.caption.strip()
        
        # Save to pending payments
        add_pending_payment(user_id, username, first_name, utr, photo_file_id)
        
        # Send confirmation to user
        await update.message.reply_text(
            "✅ *Payment Proof Received!*\n\n"
            "⏱️ Waiting for admin verification...\n"
            "💬 You'll get notified soon"
        )
        
        # Send to admin
        admin_keyboard = [
            [InlineKeyboardButton("✅ Approve", callback_data=f"approve_pay_{user_id}"),
             InlineKeyboardButton("❌ Reject", callback_data=f"reject_pay_{user_id}")]
        ]
        
        caption = (
            f"📩 *New Payment Proof*\n\n"
            f"👤 *User:* {username}\n"
            f"🆔 *ID:* `{user_id}`\n"
            f"🔗 *UTR:* `{utr}`\n"
            f"🕐 *Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
        )
        
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo_file_id,
            caption=caption,
            reply_markup=InlineKeyboardMarkup(admin_keyboard),
            parse_mode="Markdown"
        )
        
    except TelegramError:
        await update.message.reply_text("❌ Error processing photo. Please try again.")
    except Exception:
        await update.message.reply_text("❌ Error occurred. Contact admin.")

# ============== TEXT HANDLER ==============
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    try:
        if context.user_data.get('waiting_for_payment'):
            user = update.message.from_user
            user_id = user.id
            username = f"@{user.username}" if user.username else user.first_name or "User"
            first_name = user.first_name or "Unknown"
            
            text = update.message.text.strip()
            
            add_pending_payment(user_id, username, first_name, text, None)
            
            await update.message.reply_text(
                "✅ *UTR Received!*\n\n"
                "⏱️ Please upload payment screenshot"
            )
            
    except TelegramError:
        pass
    except Exception:
        pass

# ============== ADMIN: APPROVE ==============
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin approve payment and send download link"""
    try:
        if update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("❌ Admin only")
            return
        
        if not context.args:
            await update.message.reply_text("Usage: /approve <user_id>")
            return
        
        try:
            user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID")
            return
        
        # Check if already approved
        if is_user_approved(user_id):
            await update.message.reply_text(f"⚠️ User {user_id} already approved")
            return
        
        # Get payment details
        payment = get_payment_details(user_id)
        
        if not payment:
            await update.message.reply_text(f"❌ No pending payment for user {user_id}")
            return
        
        username, utr = payment
        
        # Send to user
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="✅ *Payment Approved!*\n\nYour payment has been verified.",
                parse_mode="Markdown"
            )
            
            # Send download link
            if DOWNLOAD_LINK:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"📥 *Download App:*\n{DOWNLOAD_LINK}",
                    parse_mode="Markdown"
                )
            else:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="⚠️ Download link unavailable"
                )
        
        except TelegramError:
            await update.message.reply_text(f"❌ Cannot send to user {user_id} (blocked/inactive)")
            return
        
        # Save to users table
        add_user(user_id, username, "", utr)
        
        # Remove from pending
        remove_pending_payment(user_id)
        
        await update.message.reply_text(
            f"✅ *User Approved*\n\n"
            f"👤 {username}\n"
            f"🆔 {user_id}\n"
            f"💾 Saved permanently"
        )
        
    except TelegramError:
        pass
    except Exception as e:
        print("Database error:", e, file=sys.stderr)
        await update.message.reply_text("❌ Error processing approval")

# ============== ADMIN: REJECT ==============
async def reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin reject payment"""
    try:
        if update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("❌ Admin only")
            return
        
        if not context.args:
            await update.message.reply_text("Usage: /reject <user_id>")
            return
        
        try:
            user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID")
            return
        
        # Check if payment exists
        payment = get_payment_details(user_id)
        if not payment:
            await update.message.reply_text(f"❌ No pending payment for user {user_id}")
            return
        
        # Send rejection message
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "❌ *Payment Rejected*\n\n"
                    "━━━━━━━━━━━━━━━━━━\n"
                    "Your payment could not be verified.\n\n"
                    "Possible reasons:\n"
                    "• Wrong amount\n"
                    "• Invalid UTR\n"
                    "• Payment not completed\n\n"
                    "Please try again or contact support."
                ),
                parse_mode="Markdown"
            )
        except TelegramError:
            pass
        
        # Remove from pending
        remove_pending_payment(user_id)
        
        await update.message.reply_text(f"❌ User {user_id} rejected. Pending payment removed.")
        
    except TelegramError:
        pass
    except Exception as e:
        print("Database error:", e, file=sys.stderr)
        await update.message.reply_text("❌ Error processing rejection")

# ============== ADMIN: APPROVE CALLBACK ==============
async def approve_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle approve button from admin panel"""
    query = update.callback_query
    
    try:
        if query.from_user.id != ADMIN_ID:
            await query.answer("❌ Admin only", show_alert=True)
            return
        
        user_id_str = query.data.split("_")[-1]
        user_id = int(user_id_str)
        
        # Check if already approved
        if is_user_approved(user_id):
            await query.answer("⚠️ User already approved", show_alert=True)
            return
        
        # Get payment details
        payment = get_payment_details(user_id)
        
        if not payment:
            await query.answer("❌ Payment not found", show_alert=True)
            return
        
        username, utr = payment
        
        # Send to user
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="✅ *Payment Approved!*\n\nYour payment has been verified.",
                parse_mode="Markdown"
            )
            
            # Send download link
            if DOWNLOAD_LINK:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"📥 *Download App:*\n{DOWNLOAD_LINK}",
                    parse_mode="Markdown"
                )
            else:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="⚠️ Download link unavailable"
                )
        
        except TelegramError:
            await query.answer("❌ Cannot send to user (blocked)", show_alert=True)
            return
        
        # Save to users
        add_user(user_id, username, "", utr)
        remove_pending_payment(user_id)
        
        await query.edit_message_caption(
            caption=query.message.caption + f"\n\n✅ *APPROVED BY ADMIN*"
        )
        await query.answer("✅ Approved", show_alert=False)
        
    except TelegramError:
        pass
    except Exception as e:
        print("Database error:", e, file=sys.stderr)
        await query.answer("❌ Error", show_alert=True)

# ============== ADMIN: REJECT CALLBACK ==============
async def reject_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle reject button from admin panel"""
    query = update.callback_query
    
    try:
        if query.from_user.id != ADMIN_ID:
            await query.answer("❌ Admin only", show_alert=True)
            return
        
        user_id_str = query.data.split("_")[-1]
        user_id = int(user_id_str)
        
        # Check if payment exists
        payment = get_payment_details(user_id)
        if not payment:
            await query.answer("❌ Payment not found", show_alert=True)
            return
        
        # Send rejection message
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "❌ *Payment Rejected*\n\n"
                    "━━━━━━━━━━━━━━━━━━\n"
                    "Your payment could not be verified.\n\n"
                    "Possible reasons:\n"
                    "• Wrong amount\n"
                    "• Invalid UTR\n"
                    "• Payment not completed\n\n"
                    "Please try again or contact support."
                ),
                parse_mode="Markdown"
            )
        except TelegramError:
            pass
        
        remove_pending_payment(user_id)
        
        await query.edit_message_caption(
            caption=query.message.caption + f"\n\n❌ *REJECTED BY ADMIN*"
        )
        await query.answer("❌ Rejected", show_alert=False)
        
    except TelegramError:
        pass
    except Exception as e:
        print("Database error:", e, file=sys.stderr)
        await query.answer("❌ Error", show_alert=True)

# ============== ADMIN: LIST USERS ==============
async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all approved users"""
    try:
        if update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("❌ Admin only")
            return
        
        try:
            conn = get_db_connection()
            if not conn:
                await update.message.reply_text("❌ Database error")
                return
            
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users ORDER BY user_id DESC")
            users = cursor.fetchall()
            cursor.close()
            conn.close()
        except psycopg2.Error as e:
            print("Database error:", e, file=sys.stderr)
            await update.message.reply_text("❌ Database error")
            return
        
        if not users:
            await update.message.reply_text("📋 No users yet")
            return
        
        text = "📋 *Approved Users*\n\n━━━━━━━━━━━━━━━━━━\n"
        for (user_id,) in users:
            text += f"🆔 {user_id}\n"
        
        text += f"━━━━━━━━━━━━━━━━━━\n✅ Total: {len(users)}"
        
        await update.message.reply_text(text, parse_mode="Markdown")
        
    except TelegramError:
        pass
    except Exception as e:
        print("Database error:", e, file=sys.stderr)
        await update.message.reply_text("❌ Error fetching users")

# ============== ADMIN: STATS ==============
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot statistics"""
    try:
        if update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("❌ Admin only")
            return
        
        total_users = get_user_count()
        pending = len(get_pending_payments())
        
        text = (
            "📊 *Bot Statistics*\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"✅ Approved Users: {total_users}\n"
            f"⏳ Pending Payments: {pending}\n"
            f"📈 Total Requests: {total_users + pending}\n"
            "━━━━━━━━━━━━━━━━━━"
        )
        
        await update.message.reply_text(text, parse_mode="Markdown")
        
    except TelegramError:
        pass
    except Exception as e:
        print("Database error:", e, file=sys.stderr)
        await update.message.reply_text("❌ Error fetching stats")

# ============== ADMIN: BROADCAST ==============
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast message to all users"""
    try:
        if update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("❌ Admin only")
            return
        
        if not context.args:
            await update.message.reply_text("Usage: /broadcast <message>")
            return
        
        message = " ".join(context.args)
        users = get_all_users()
        
        sent = 0
        failed = 0
        
        for user_id in users:
            try:
                await context.bot.send_message(chat_id=user_id, text=message, parse_mode="Markdown")
                sent += 1
            except TelegramError:
                failed += 1
            except Exception:
                failed += 1
        
        await update.message.reply_text(
            f"📢 *Broadcast Complete*\n\n"
            f"✅ Sent: {sent}\n"
            f"❌ Failed: {failed}"
        )
        
    except TelegramError:
        pass
    except Exception:
        await update.message.reply_text("❌ Error during broadcast")

# ============== ADMIN: PENDING PAYMENTS ==============
async def pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show pending payment requests"""
    try:
        if update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("❌ Admin only")
            return
        
        pending_list = get_pending_payments()
        
        if not pending_list:
            await update.message.reply_text("✅ No pending payments")
            return
        
        text = "⏳ *Pending Payments*\n\n━━━━━━━━━━━━━━━━━━\n"
        for user_id, username, utr in pending_list:
            text += f"👤 {username}\n🆔 {user_id}\n🔗 UTR: {utr}\n\n"
        
        text += f"━━━━━━━━━━━━━━━━━━\n⏳ Pending: {len(pending_list)}"
        
        await update.message.reply_text(text, parse_mode="Markdown")
        
    except TelegramError:
        pass
    except Exception as e:
        print("Database error:", e, file=sys.stderr)
        await update.message.reply_text("❌ Error fetching pending payments")

# ============== ADMIN: REMOVE USER ==============
async def removeuser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove user from database"""
    try:
        if update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("❌ Admin only")
            return
        
        if not context.args:
            await update.message.reply_text("Usage: /removeuser <user_id>")
            return
        
        try:
            user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID")
            return
        
        if remove_user(user_id):
            await update.message.reply_text(f"🗑️ User {user_id} removed")
        else:
            await update.message.reply_text(f"❌ Cannot remove user {user_id}")
        
    except TelegramError:
        pass
    except Exception:
        await update.message.reply_text("❌ Error removing user")

# ============== CREATE BOT ==========
def create_bot(token):
    """Create and configure bot application"""
    try:
        print(f"[DEBUG] Creating Application with token: {token[:10]}...", file=sys.stderr)
        app = Application.builder().token(token).build()
        print(f"[DEBUG] Application created successfully", file=sys.stderr)

        # Command handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("approve", approve))
        app.add_handler(CommandHandler("reject", reject))
        app.add_handler(CommandHandler("users", list_users))
        app.add_handler(CommandHandler("stats", stats))
        app.add_handler(CommandHandler("broadcast", broadcast))
        app.add_handler(CommandHandler("pending", pending))
        app.add_handler(CommandHandler("removeuser", removeuser))

        # Callback handlers
        app.add_handler(CallbackQueryHandler(approve_payment_callback, pattern=r"^approve_pay_"))
        app.add_handler(CallbackQueryHandler(reject_payment_callback, pattern=r"^reject_pay_"))
        app.add_handler(CallbackQueryHandler(handle_callback))

        # Message handlers
        app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

        print(f"[DEBUG] All handlers registered successfully", file=sys.stderr)
        return app
    except Exception as e:
        print(f"[ERROR] Failed to create bot: {e}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        raise

# ============== RUN BOT ==========
async def run_bot(app):
    """Run bot with polling"""
    try:
        print(f"[DEBUG] Initializing bot application...", file=sys.stderr)
        await app.initialize()
        print(f"[DEBUG] Bot initialized successfully", file=sys.stderr)
        
        await app.start()
        print(f"[DEBUG] Bot started successfully", file=sys.stderr)
        
        print(f"[DEBUG] Starting polling...", file=sys.stderr)
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        print(f"[DEBUG] Polling started successfully", file=sys.stderr)
        
        print(f"[DEBUG] Bot is now polling for messages...", file=sys.stderr)
        await asyncio.sleep(float('inf'))
        
    except TelegramError as e:
        print(f"[ERROR] Telegram API Error: {e}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
    except Exception as e:
        print(f"[ERROR] Unexpected error in run_bot: {e}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)

async def main():
    """Main entry point for multiple bots"""
    try:
        print("[DEBUG] Starting main function...", file=sys.stderr)
        
        if not BOT_TOKENS:
            print("[ERROR] No BOT_TOKENS available!", file=sys.stderr)
            return
        
        print(f"[DEBUG] Creating {len(BOT_TOKENS)} bot application(s)...", file=sys.stderr)
        apps = [create_bot(token) for token in BOT_TOKENS]
        print(f"[DEBUG] Bot application(s) created successfully", file=sys.stderr)
        
        print("[DEBUG] Starting bot polling with asyncio.gather...", file=sys.stderr)
        await asyncio.gather(*[run_bot(app) for app in apps])
        
    except KeyboardInterrupt:
        print("\n[INFO] Bot interrupted by user", file=sys.stderr)
    except Exception as e:
        print(f"[ERROR] Fatal error in main: {e}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)

if __name__ == "__main__":
    try:
        print("[DEBUG] Bot startup initiated", file=sys.stderr)
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INFO] Bot shutdown", file=sys.stderr)
    except Exception as e:
        print(f"[ERROR] Fatal error: {e}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
