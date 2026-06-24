import os, logging, time, json, re
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

logging.basicConfig(level=logging.INFO)
BOT_TOKEN = "TELEGRAM_BOT_TOKEN_PLACEHOLDER"
TARGET_ADMIN_ID = 7323039280

# ==========================================
# --- RATE LIMITER (JSON) ---
# ==========================================
DATA_FILE = "rate_limits.json"
user_history = {}

if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE, "r") as f: user_history = json.load(f)
    except: pass

def check_and_add_limit(user_id):
    user_id_str = str(user_id)
    current_time = time.time()
    if user_id_str not in user_history: user_history[user_id_str] = []
    user_history[user_id_str] = [t for t in user_history[user_id_str] if current_time - t < 604800]
    count = len(user_history[user_id_str])
    if count >= 5: return True, count
    user_history[user_id_str].append(current_time)
    with open(DATA_FILE, "w") as f: json.dump(user_history, f)
    return False, len(user_history[user_id_str])

# ==========================================
# --- BOT HANDLERS ---
# ==========================================
async def post_init(application):
    await application.bot.set_my_commands([BotCommand("start", "Start the verification process")])

# --- INLINE BUTTONS CLICK (Approve/Decline) ---
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Message ka status update karna
    status = "✅ Approved" if query.data == "approve" else "❌ Declined"
    new_text = query.message.text.replace("⏳ Pending", status)
    
    try:
        # Keyboard (buttons) ko hata kar naya text laga dega
        await query.edit_message_text(text=new_text, parse_mode='Markdown')
    except: pass
    
    # User ko notification bhejna
    match = re.search(r"ID: (\d+)", query.message.text)
    if match:
        user_id = match.group(1)
        if query.data == "approve":
            msg = "🎉 *Congratulations!* Your application has been Approved. Please wait for the Admin to send you the link."
        else:
            msg = "❌ Your application was Declined."
            
        try: await context.bot.send_message(chat_id=user_id, text=msg, parse_mode='Markdown')
        except: pass

# --- MAIN MESSAGE HANDLER ---
async def handle_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text if update.message.text else "No text"

    # ------------------------------------
    # 1. ADMIN LOGIC (Reply to send link)
    # ------------------------------------
    if user_id == TARGET_ADMIN_ID:
        if update.message.reply_to_message and update.message.reply_to_message.text:
            match = re.search(r"ID: (\d+)", update.message.reply_to_message.text)
            if match:
                target_id = int(match.group(1))
                try:
                    await context.bot.send_message(chat_id=target_id, text=f"🔗 *Here is your Link:*\n\n{text}", parse_mode='Markdown')
                    await update.message.reply_text("✅ Link sent to the user successfully!")
                except: await update.message.reply_text("❌ Failed to send link.")
        return

    # ------------------------------------
    # 2. NORMAL USER LOGIC
    # ------------------------------------
    is_limited, count = check_and_add_limit(user_id)
    if is_limited:
        await update.message.reply_text("🙏 *Apologies! Limit Reached.*\n\nYou have used your 5 requests. Try again in 7 days.", parse_mode='Markdown')
        return

    await update.message.reply_text(f"📝 *Application Submitted! ({count}/5)*\n\nPlease wait for the Admin to review.", parse_mode='Markdown')
    
    # ------------------------------------
    # 3. PFP PREVIEW & ADMIN NOTIFICATION
    # ------------------------------------
    # Agar user ne sirf username likha hai, toh usko link mein convert karo taake PFP aaye
    profile_link = text
    if "x.com" not in text and "twitter.com" not in text:
        clean_user = text.replace("@", "").strip().split()[0] # Removes @ and extra spaces
        profile_link = f"https://x.com/{clean_user}"

    username = update.message.from_user.username
    user_mention = f"@{username}" if username else "No Username"

    keyboard = [[InlineKeyboardButton("✅ Approve", callback_data="approve"), 
                 InlineKeyboardButton("❌ Decline", callback_data="decline")]]
    
    admin_alert = (
        f"🚨 **New Creator Application** 🚨\n\n"
        f"👤 User: {user_mention}\n"
        f"🆔 ID: {user_id}\n"
        f"🔗 Profile: {profile_link}\n\n"
        f"**Status:** ⏳ Pending"
    )
    
    await context.bot.send_message(
        chat_id=TARGET_ADMIN_ID, 
        text=admin_alert, 
        parse_mode='Markdown', 
        reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=False # Ye ensure karega ke PFP lazmi show ho
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id == TARGET_ADMIN_ID:
        await update.message.reply_text("👑 Admin Bot Ready!")
    else:
        welcome_msg = (
            "🌟 *Welcome to Web3 Creators Verification!* 🌟\n\n"
            "Please send your **Twitter/X Username** or **Profile Link** to get verified.\n"
            "_(Example: @comradexbt OR https://x.com/comradexbt)_"
        )
        await update.message.reply_text(welcome_msg, parse_mode='Markdown')

# ==========================================
# --- FLASK SERVER (Render 24/7) ---
# ==========================================
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is running!"
def run_server(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

if __name__ == '__main__':
    Thread(target=run_server).start()
    bot_app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CallbackQueryHandler(button_click))
    bot_app.add_handler(MessageHandler(filters.TEXT, handle_request))
    bot_app.run_polling(drop_pending_updates=True)
