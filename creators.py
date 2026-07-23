import os, logging, time, json, re
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

logging.basicConfig(level=logging.INFO)

# Tokens aur IDs ab Environment Variables se aayenge
BOT_TOKEN = os.environ.get("BOT_TOKEN")
TARGET_ADMIN_ID = int(os.environ.get("TARGET_ADMIN_ID", 0))

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
    
    status = "✅ Approved" if query.data == "approve" else "❌ Declined"
    
    is_photo = bool(query.message.photo)
    current_text = query.message.caption if is_photo else query.message.text
    
    if not current_text: return
    new_text = current_text.replace("Status: ⏳ Pending", f"Status: {status}")
    
    try:
        if is_photo:
            await query.edit_message_caption(caption=new_text)
        else:
            await query.edit_message_text(text=new_text)
    except: pass
    
    # ------------------------------------
    # APPROVAL MESSAGE & DECLINE LOGIC
    # ------------------------------------
    match = re.search(r"ID: (\d+)", current_text)
    if match:
        user_id = match.group(1)
        # Sirf Approve hone par message jayega, decline par kuch nahi jayega
        if query.data == "approve":
            approval_msg = (
                "🎉 *Congratulations! Your application has been Approved.*\n\n"
                "Welcome to the Exclusive Community of Web3 Creators 🚀\n\n"
                "Exclusive Community for web3 Creators\n"
                "TG community: https://t.me/+CYbefSUioG5iNDU0\n"
                "X/Twitter: x.com/CreatorsClubw3"
            )
            try: 
                await context.bot.send_message(
                    chat_id=user_id, 
                    text=approval_msg, 
                    parse_mode='Markdown', 
                    disable_web_page_preview=True
                )
            except: pass

# --- MAIN MESSAGE HANDLER ---
async def handle_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text if update.message.text else "No text"

    if user_id == TARGET_ADMIN_ID:
        return # Admin manually kuch likhega to ignore kar dega

    # ------------------------------------
    # NORMAL USER LOGIC
    # ------------------------------------
    is_limited, count = check_and_add_limit(user_id)
    if is_limited:
        await update.message.reply_text("🙏 *Apologies! Limit Reached.*\n\nYou have used your 5 requests. Try again in 7 days.", parse_mode='Markdown')
        return

    await update.message.reply_text(f"📝 *Application Submitted! ({count}/5)*\n\nPlease wait for the Admin to review.", parse_mode='Markdown')
    
    # ------------------------------------
    # PFP ATTACHMENT & ADMIN NOTIFICATION
    # ------------------------------------
    profile_link = text
    clean_user = ""
    
    if "x.com" in text or "twitter.com" in text:
        match = re.search(r"(?:x\.com|twitter\.com)/([^/?]+)", text)
        if match: clean_user = match.group(1)
    else:
        clean_user = text.replace("@", "").strip().split()[0]
        profile_link = f"https://x.com/{clean_user}"

    username = update.message.from_user.username
    user_mention = f"@{username}" if username else "No Username"

    keyboard = [[InlineKeyboardButton("✅ Approve", callback_data="approve"), 
                 InlineKeyboardButton("❌ Decline", callback_data="decline")]]
    
    admin_alert = (
        f"🚨 New Creator Application 🚨\n\n"
        f"👤 User: {user_mention}\n"
        f"🆔 ID: {user_id}\n"
        f"🔗 Profile: {profile_link}\n\n"
        f"Status: ⏳ Pending"
    )
    
    try:
        if clean_user:
            pfp_url = f"https://unavatar.io/twitter/{clean_user}"
            await context.bot.send_photo(
                chat_id=TARGET_ADMIN_ID,
                photo=pfp_url,
                caption=admin_alert,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            raise Exception("No Username")
    except:
        await context.bot.send_message(
            chat_id=TARGET_ADMIN_ID, 
            text=admin_alert, 
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=True
        )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id == TARGET_ADMIN_ID:
        await update.message.reply_text("👑 Admin Bot Ready!")
    else:
        # Example line remove kar di gayi hai
        welcome_msg = (
            "🌟 *Welcome to Web3 Creators Verification!* 🌟\n\n"
            "Please send your **Twitter/X Username** or **Profile Link** to get verified."
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
