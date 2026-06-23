import os
import logging
import re
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

# --- HELPER FUNCTION: DATA SAVE KARNE KE LIYE ---
def save_user_data(filename, user_id, username, x_link):
    # 'a' mode ka matlab hai purane data ke aage naya data likhna
    with open(filename, "a", encoding="utf-8") as file:
        file.write(f"ID: {user_id} | User: {username} | X_Profile: {x_link}\n")

# --- ADMIN COMMANDS ---
async def get_approved_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Sirf admin yeh command chala sakta hai
    if update.message.from_user.id != ADMIN_ID: return
    try:
        await update.message.reply_document(document=open("approved_users.txt", "rb"), caption="✅ Here is the Approved Users List.")
    except FileNotFoundError:
        await update.message.reply_text("📂 The approved users list is currently empty.")

async def get_declined_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Sirf admin yeh command chala sakta hai
    if update.message.from_user.id != ADMIN_ID: return
    try:
        await update.message.reply_document(document=open("declined_users.txt", "rb"), caption="❌ Here is the Declined Users List.")
    except FileNotFoundError:
        await update.message.reply_text("📂 The declined users list is currently empty.")


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
    x_username = None

    # === X (Twitter) Link Smart Generator & Username Extractor ===
    if raw_text:
        if "x.com" in raw_text.lower() or "twitter.com" in raw_text.lower() or "http" in raw_text.lower():
            final_link = raw_text
            # Poore link se sirf aakhri hissa (username) nikalna
            x_username = final_link.rstrip('/').split('/')[-1].split('?')[0]
        else:
            clean_username = raw_text.replace("@", "").strip().split()[0]
            x_username = clean_username
            final_link = f"https://x.com/{clean_username}"
    else:
        final_link = "[No Text / Only Media Attached]"
    # ==============================================================

    await update.message.reply_text("⏳ Your application has been submitted to the admin team. Please wait while we review your profile.")

    keyboard = [
        [InlineKeyboardButton("✅ Approve", callback_data=f'approve_{user_id}'),
         InlineKeyboardButton("❌ Decline", callback_data=f'deny_{user_id}')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    admin_text = f"🚨 **New Creator Application** 🚨\n\n👤 User: {username}\n🆔 ID: {user_id}\n🔗 Profile: {final_link}"
    
    # Agar user ne khud koi screenshot bheja hai toh use forward karein
    if update.message.photo:
        photo_file_id = update.message.photo[-1].file_id
        caption = f"🚨 **New Creator Application (With Image)** 🚨\n\n👤 User: {username}\n🆔 ID: {user_id}\n🔗 Profile: {final_link}"
        try:
            await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo_file_id, caption=caption, reply_markup=reply_markup)
            return
        except Exception as e:
            logging.error(f"Failed to send image application: {e}")

    # Agar user ne sirf link bheja hai, toh Unavatar se DP nikalne ki koshish karein
    avatar_sent = False
    if x_username:
        avatar_url = f"https://unavatar.io/x/{x_username}"
        try:
            await context.bot.send_photo(chat_id=ADMIN_ID, photo=avatar_url, caption=admin_text, reply_markup=reply_markup)
            avatar_sent = True
        except Exception as e:
            logging.warning(f"Unavatar failed for {x_username}, falling back to text message. Error: {e}")
    
    # Fallback: Agar avatar nahi mila ya unavatar fail ho gaya, toh simple text bhej dein
    if not avatar_sent:
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=admin_text, reply_markup=reply_markup)
        except Exception as e:
            logging.error(f"Failed to send text application to admin: {e}")

# 3. Jab Admin button par click kare
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() 
    data = query.data

    action, user_id_str = data.split('_')
    target_user_id = int(user_id_str)

    # === Admin ke message se User ki Details Extract karna ===
    msg_text = query.message.caption if query.message.caption else query.message.text
    
    # Regex ke zariye Username aur X Link dhoondna
    x_link_match = re.search(r"🔗 Profile:\s*(.*)", msg_text)
    x_link = x_link_match.group(1).strip() if x_link_match else "Unknown"

    user_match = re.search(r"👤 User:\s*(.*)", msg_text)
    applicant_username = user_match.group(1).strip() if user_match else "Unknown"
    # ==========================================================

    if action == 'approve':
        # Text file mein save karna
        save_user_data("approved_users.txt", target_user_id, applicant_username, x_link)
        
        success_msg = (
            "🎉 Congratulations! Your profile has been approved.\n\n"
            "Here are your exclusive invite links to join the Web3 Creators Club:\n\n"
            f"📱 **Telegram:** {TG_LINK}\n"
            f"🐦 **Follow on Twitter/X:** {TWITTER_LINK}"
        )
        try:
            await context.bot.send_message(chat_id=target_user_id, text=success_msg, parse_mode='Markdown')
            if query.message.caption:
                await query.edit_message_caption(caption=f"{query.message.caption}\n\n**Status:** ✅ Approved")
            else:
                await query.edit_message_text(text=f"{query.message.text}\n\n**Status:** ✅ Approved")
        except Exception as e:
            logging.error(f"Could not send approval to user: {e}")
        
    elif action == 'deny':
        # Text file mein save karna
        save_user_data("declined_users.txt", target_user_id, applicant_username, x_link)
        
        sorry_msg = "😔 Sorry! Your profile currently does not meet our minimum requirements. Keep grinding and feel free to apply again later!"
        try:
            await context.bot.send_message(chat_id=target_user_id, text=sorry_msg)
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
    
    # Nayi Admin Commands
    bot_app.add_handler(CommandHandler("approvedlist", get_approved_list))
    bot_app.add_handler(CommandHandler("declinedlist", get_declined_list))
    
    bot_app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, handle_application))
    bot_app.add_handler(CallbackQueryHandler(button_callback))
    
    print("Bot is successfully running! Ready to verify creators.")
    bot_app.run_polling()