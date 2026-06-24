import os, json, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Your Bot Token
BOT_TOKEN = "TELEGRAM_BOT_TOKEN_PLACEHOLDER"

# Your Admin ID
ADMIN_ID = 7323039280  

# ⚠️ Discord Server Link
GROUP_LINK = "https://discord.gg/tYvydayNZ"

# Files to save data
APPROVED_FILE = "approved_users.txt"
DECLINED_FILE = "declined_users.txt"
RATE_LIMIT_FILE = "rate_limits.json"

# --- SPAM PROTECTION (RATE LIMITING) ---
MAX_REQUESTS = 5
TIME_WINDOW = 7 * 24 * 60 * 60  # 7 days in seconds

def check_rate_limit(user_id):
    """Checks if a user has exceeded their 5 requests per 7 days limit."""
    # Admin is never rate-limited
    if user_id == ADMIN_ID:
        return True

    try:
        if os.path.exists(RATE_LIMIT_FILE):
            with open(RATE_LIMIT_FILE, "r") as f:
                data = json.load(f)
        else:
            data = {}
    except (json.JSONDecodeError, FileNotFoundError):
        data = {}

    user_id_str = str(user_id)
    current_time = time.time()
    
    # Get user's request history
    history = data.get(user_id_str, [])
    
    # Filter to only keep requests from the last 7 days
    recent_history = [ts for ts in history if current_time - ts < TIME_WINDOW]
    
    if len(recent_history) >= MAX_REQUESTS:
        # Save cleaned history to keep file size small
        data[user_id_str] = recent_history
        with open(RATE_LIMIT_FILE, "w") as f:
            json.dump(data, f)
        return False # ❌ Blocked (Limit Reached)
        
    # If not rate limited, add new request timestamp
    recent_history.append(current_time)
    data[user_id_str] = recent_history
    
    with open(RATE_LIMIT_FILE, "w") as f:
        json.dump(data, f)
        
    return True # ✅ Allowed

def save_user_to_file(file_name, username, user_id, x_link):
    with open(file_name, "a", encoding="utf-8") as f:
        f.write(f"Telegram: {username} | ID: {user_id} | X: {x_link}\n")

# 1. When the user starts the bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = (
        "👋 Welcome to the <b>Web3 Creators Pakistan</b> Community!\n\n"
        "🚀 To get verified, please send your <b>X (Twitter) Profile Link</b> OR just your <b>@username</b>."
    )
    await update.message.reply_text(welcome_msg, parse_mode='HTML')

# 2. When the user sends their link/username
async def handle_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_text = update.message.text.strip()
    
    # 🚦 CHECK RATE LIMIT FIRST (SPAM BLOCKER)
    if not check_rate_limit(user_id):
        # ⚠️ Spammer message (Bot won't forward anything to you)
        await update.message.reply_text("🚫 You have reached your submission limit. Please try again after 7 days.")
        return

    # If limit is not reached, process normally:
    user = update.message.from_user
    tg_username = f"@{user.username}" if user.username else user.first_name

    x_username = ""
    if "x.com/" in user_text:
        x_username = user_text.split("x.com/")[-1].split("?")[0].strip("/")
    elif "twitter.com/" in user_text:
        x_username = user_text.split("twitter.com/")[-1].split("?")[0].strip("/")
    elif user_text.startswith("@"):
        x_username = user_text[1:]
    else:
        x_username = user_text.strip()

    x_link = f"https://x.com/{x_username}"
    x_photo_url = f"https://unavatar.io/x/{x_username}"

    # Assure the user
    await update.message.reply_text("⏳ Your profile has been submitted! Please wait while our admin team reviews it.")

    # Approve / Decline buttons for the Admin
    keyboard = [
        [InlineKeyboardButton("✅ Approve", callback_data=f'approve_{user_id}_{x_username}'),
         InlineKeyboardButton("❌ Decline", callback_data=f'deny_{user_id}_{x_username}')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    admin_text = (
        "🚨 <b>NEW CREATOR APPLICATION</b> 🚨\n\n"
        f"👤 <b>Telegram User:</b> {tg_username}\n"
        f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
        f"🌐 <b>X Profile:</b> <a href='{x_link}'>{x_link}</a>\n\n"
        "⚡ <i>Please review the profile and take action below!</i>"
    )
    
    try:
        await context.bot.send_photo(
            chat_id=ADMIN_ID, 
            photo=x_photo_url, 
            caption=admin_text, 
            reply_markup=reply_markup, 
            parse_mode='HTML'
        )
    except Exception as e:
        print(f"Photo fetch error: {e}")
        await context.bot.send_message(
            chat_id=ADMIN_ID, 
            text=admin_text, 
            reply_markup=reply_markup, 
            parse_mode='HTML', 
            disable_web_page_preview=True
        )

# 3. When the Admin clicks Approve or Decline
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() 
    data = query.data

    action, user_id, x_username = data.split('_')
    user_id = int(user_id)
    x_link = f"https://x.com/{x_username}"
    tg_username = f"@{query.message.chat.username}" if query.message.chat.username else "User"

    if action == 'approve':
        success_msg = (
            "🎉 <b>Congratulations! Your profile has been approved.</b>\n\n"
            "👋 Welcome to the elite circle of creators!\n\n"
            "🚀 Here is your exclusive invite link to join our Discord community:\n"
            f"👉 <b><a href='{GROUP_LINK}'>Web3 Creators Discord Server</a></b>"
        )
        await context.bot.send_message(chat_id=user_id, text=success_msg, parse_mode='HTML', disable_web_page_preview=True)
        
        save_user_to_file(APPROVED_FILE, tg_username, user_id, x_link)
        
        if query.message.caption:
            await query.edit_message_caption(caption=f"{query.message.caption}\n\n**Status:** ✅ APPROVED & SAVED", parse_mode='Markdown')
        else:
            await query.edit_message_text(text=f"{query.message.text}\n\n**Status:** ✅ APPROVED & SAVED", parse_mode='Markdown')
        
    elif action == 'deny':
        sorry_msg = "😔 Sorry! Your profile currently does not meet our minimum requirements. Keep grinding and feel free to apply again later!"
        await context.bot.send_message(chat_id=user_id, text=sorry_msg)
        
        save_user_to_file(DECLINED_FILE, tg_username, user_id, x_link)
        
        if query.message.caption:
            await query.edit_message_caption(caption=f"{query.message.caption}\n\n**Status:** ❌ DECLINED & SAVED", parse_mode='Markdown')
        else:
            await query.edit_message_text(text=f"{query.message.text}\n\n**Status:** ❌ DECLINED & SAVED", parse_mode='Markdown')

# Admin Commands
async def send_approved_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat_id != ADMIN_ID: return
    if os.path.exists(APPROVED_FILE) and os.path.getsize(APPROVED_FILE) > 0:
        await context.bot.send_document(chat_id=ADMIN_ID, document=open(APPROVED_FILE, 'rb'), filename="Approved_Creators.txt", caption="📋 Approved Users.")
    else:
        await update.message.reply_text("📭 Approved list is empty.")

async def send_declined_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat_id != ADMIN_ID: return
    if os.path.exists(DECLINED_FILE) and os.path.getsize(DECLINED_FILE) > 0:
        await context.bot.send_document(chat_id=ADMIN_ID, document=open(DECLINED_FILE, 'rb'), filename="Declined_Users.txt", caption="📋 Declined Users.")
    else:
        await update.message.reply_text("📭 Declined list is empty.")

if __name__ == '__main__':
    print("Bot is starting...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("approvedlist", send_approved_list))
    app.add_handler(CommandHandler("declinedlist", send_declined_list))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_application))
    app.add_handler(CallbackQueryHandler(button_callback))

    print("Bot is running! Check it on Telegram.")
    app.run_polling(poll_interval=3.0)
