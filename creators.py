import os, logging, math, requests, time, json, re
from flask import Flask
from threading import Thread
from io import BytesIO
from PIL import Image
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
BOT_TOKEN = "TELEGRAM_BOT_TOKEN_PLACEHOLDER"
TARGET_ADMIN_ID = 7323039280

user_images = {}
user_states = {}

# ==========================================
# --- RATE LIMITER ---
# ==========================================
DATA_FILE = "rate_limits.json"
user_history = {}

if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE, "r") as f:
            user_history = json.load(f)
    except:
        pass

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
# --- BOT FUNCTIONS ---
# ==========================================
async def post_init(application):
    await application.bot.set_my_commands([BotCommand("start", "Start the verification process")])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id == TARGET_ADMIN_ID:
        await update.message.reply_text("👑 Admin Bot Ready!")
    else:
        welcome_msg = "🌟 *Welcome to Web3 Creators Verification!* 🌟\n\nSend your Twitter/X profile link to get verified."
        await update.message.reply_text(welcome_msg, parse_mode='Markdown')

async def handle_buttons_and_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text if update.message.text else "No text"

    if user_id == TARGET_ADMIN_ID:
        if update.message.reply_to_message:
            match = re.search(r"User ID: (\d+)", update.message.reply_to_message.text)
            if match:
                target_id = int(match.group(1))
                try:
                    await context.bot.send_message(chat_id=target_id, text=f"🎉 *Congratulations!*\n\n{text}", parse_mode='Markdown')
                    await update.message.reply_text("✅ Sent!")
                except: await update.message.reply_text("❌ Error!")
        return

    is_limited, count = check_and_add_limit(user_id)
    if is_limited:
        await update.message.reply_text("🙏 *Apologies! Limit Reached.* Please try again after 7 days.", parse_mode='Markdown')
        return

    await update.message.reply_text(f"📝 *Application Submitted! ({count}/5)*", parse_mode='Markdown')
    await context.bot.send_message(chat_id=TARGET_ADMIN_ID, text=f"📩 *New Request ({count}/5)*\n🆔 User ID: {user_id}\n📄 {text}", parse_mode='Markdown')

# ==========================================
# --- DUMMY FLASK SERVER (For Render) ---
# ==========================================
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is running!"

def run_server(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

if __name__ == '__main__':
    Thread(target=run_server).start()
    bot_app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.TEXT, handle_buttons_and_logic))
    bot_app.run_polling(drop_pending_updates=True)
