import os
import logging
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Aap ki Bot aur Admin Details
BOT_TOKEN = "TELEGRAM_BOT_TOKEN_PLACEHOLDER"
ADMIN_ID = 7323039280  

# Aap ke Web3 Creators Club ke Links
TG_LINK = "https://t.me/+CYbefSUioG5iNDU0"
TWITTER_LINK = "https://x.com/CreatorsClubw3"

# ===== DUMMY WEB SERVER =====
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Creators Club W3 Bot is Alive and Running 24/7!"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    flask_app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()
# ============================

# 1. Jab user bot ko /start bhejay
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = (
        "👋 Welcome to the Web3 Creators Club!\n\n"
        "To get verified and receive your exclusive invites, please send the link to your Twitter/X profile or username."
    )
    await update.message.reply_text(welcome_msg)

# 2. Jab user apni details bhejay
async def handle_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_text = update.message.text if update.message.text else ""
    user = update.message.from_user
    user_id = user.id
    username = f"@{user.username}" if user.username else user.first_name

    # === X (Twitter) Link Smart Generator ===
    if raw_text:
        if "x.com" in raw_text.lower() or "twitter.com" in raw_text.lower() or "http" in raw_text.lower():
            final_link = raw_text
        else:
            clean_username = raw_text.replace("@", "").strip().split()[0]
            final_link = f"https://x.com/{clean_username}"
    else:
        final_link = "[No Text / Only Media Attached]"
    # ========================================

    # User ko confirmation message
    await update.message.reply_text("⏳ Your application has been submitted to the admin team. Please wait while we review your profile.")

    # Admin ke liye buttons
    keyboard = [
        [InlineKeyboardButton("✅ Approve", callback_data=f'approve_{user_id}'),
         InlineKeyboardButton("❌ Decline", callback_data=f'deny_{user_id}')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Admin ko notification bhejna
    admin_text = f"🚨 **New Creator Application** 🚨\n\n👤 User: {username}\n🆔 ID: {user_id}\n🔗 Profile: {final_link}"
    
    try:
        if update.message.photo:
            photo_file_id = update.message.photo[-1].file_id
            caption = f"🚨 **New Creator Application (With Image)** 🚨\n\n👤 User: {username}\n🆔 ID: {user_id}\n🔗 Profile: {final_link}"
            await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo_file_id, caption=caption, reply_markup=reply_markup)
        else:
            await context.bot.send_message(chat_id=ADMIN_ID, text=admin_text, reply_markup=reply_markup)
    except Exception as e:
        logging.error(f"Failed to send message to admin: {e}")

# 3. Jab Admin button par click kare
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() 
    data = query.data

    action, user_id = data.split('_')
    user_id = int(user_id)

    if action == 'approve':
        success_msg = (
            "🎉 Congratulations! Your profile has been approved.\n\n"
            "Here are your exclusive invite links to join the Web3 Creators Club:\n\n"
            f"📱 **Telegram:** {TG_LINK}\n"
            f"🐦 **Follow on Twitter/X:** {TWITTER_LINK}"
        )
        try:
            await context.bot.send_message(chat_id=user_id, text=success_msg, parse_mode='Markdown')
            if query.message.caption:
                await query.edit_message_caption(caption=f"{query.message.caption}\n\n**Status:** ✅ Approved")
            else:
                await query.edit_message_text(text=f"{query.message.text}\n\n**Status:** ✅ Approved")
        except Exception as e:
            logging.error(f"Could not send approval to user: {e}")
        
    elif action == 'deny':
        sorry_msg = "😔 Sorry! Your profile currently does not meet our minimum requirements. Keep grinding and feel free to apply again later!"
        try:
            await context.bot.send_message(chat_id=user_id, text=sorry_msg)
            if query.message.caption:
                await query.edit_message_caption(caption=f"{query.message.caption}\n\n**Status:** ❌ Declined")
            else:
                await query.edit_message_text(text=f"{query.message.text}\n\n**Status:** ❌ Declined")
        except Exception as e:
            logging.error(f"Could not send decline to user: {e}")

if __name__ == '__main__':
    print("Starting dummy web server to keep bot alive...")
    keep_alive() 
    
    print("Bot is connecting to Telegram...")
    bot_app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, handle_application))
    bot_app.add_handler(CallbackQueryHandler(button_callback))
    
    print("Bot is successfully running! Ready to verify creators.")
    bot_app.run_polling()
