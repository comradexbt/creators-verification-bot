import os, logging, time, json, re
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

logging.basicConfig(level=logging.INFO)
BOT_TOKEN = "TELEGRAM_BOT_TOKEN_PLACEHOLDER"
TARGET_ADMIN_ID = 7323039280

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

# --- ADMIN BUTTON LOGIC ---
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    status = "✅ Approved" if query.data == "approve" else "❌ Declined"
    new_text = query.message.text.replace("⏳ Pending", status)
    await query.edit_message_text(text=new_text, parse_mode='Markdown')
    
    match = re.search(r"ID: (\d+)", query.message.text)
    if match:
        user_id = match.group(1)
        try: await context.bot.send_message(chat_id=user_id, text=f"Status Update: {status}")
        except: pass

async def handle_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    
    # ADMIN LOGIC
    if user_id == TARGET_ADMIN_ID: return

    # USER LOGIC
    is_limited, count = check_and_add_limit(user_id)
    if is_limited:
        await update.message.reply_text("🙏 Limit Reached. Try again in 7 days.")
        return

    # User ko Counter dikhao
    await update.message.reply_text(f"📝 Application Submitted! ({count}/5)")
    
    # Admin ko Clean Buttons wala layout dikhao
    keyboard = [[InlineKeyboardButton("✅ Approve", callback_data="approve"), 
                 InlineKeyboardButton("❌ Decline", callback_data="decline")]]
    
    admin_alert = (
        f"🚨 **New Creator Application** 🚨\n\n"
        f"👤 User: @{update.message.from_user.username}\n"
        f"🆔 ID: {user_id}\n"
        f"🔗 Profile: {text}\n\n"
        f"**Status:** ⏳ Pending"
    )
    await context.bot.send_message(chat_id=TARGET_ADMIN_ID, text=admin_alert, 
                                   parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

# --- FLASK SERVER ---
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is running!"
def run_server(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

if __name__ == '__main__':
    Thread(target=run_server).start()
    bot_app = ApplicationBuilder().token(BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("Send your X profile link!")))
    bot_app.add_handler(CallbackQueryHandler(button_click))
    bot_app.add_handler(MessageHandler(filters.TEXT, handle_request))
    bot_app.run_polling(drop_pending_updates=True)
