import os
import logging
import re
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

BOT_TOKEN = "TELEGRAM_BOT_TOKEN_PLACEHOLDER"
ADMIN_ID = 7323039280  
TG_LINK = "https://t.me/+CYbefSUioG5iNDU0"
TWITTER_LINK = "https://x.com/CreatorsClubw3"

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

def save_user_data(filename, user_id, username, x_link):
    with open(filename, "a", encoding="utf-8") as file:
        file.write(f"ID: {user_id} | User: {username} | X_Profile: {x_link}\n")

async def get_approved_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID: return
    try:
        await update.message.reply_document(document=open("approved_users.txt", "rb"), caption="✅ Approved Users List.")
    except: await update.message.reply_text("📂 List is empty.")

async def get_declined_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID: return
    try:
        await update.message.reply_document(document=open("declined_users.txt", "rb"), caption="❌ Declined Users List.")
    except: await update.message.reply_text("📂 List is empty.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id == ADMIN_ID:
        keyboard = [[KeyboardButton("📥 Approved List"), KeyboardButton("🗑️ Declined List")], [KeyboardButton("/start")]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, persistent=True)
        await update.message.reply_text("👋 Welcome Admin!", reply_markup=reply_markup)
    else:
        await update.message.reply_text("👋 Welcome to Web3 Creators Club!\n\nSend your Twitter/X username/link to get verified.")

async def handle_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_text = update.message.text if update.message.text else ""
    user = update.message.from_user
    user_id = user.id
    username = f"@{user.username}" if user.username else user.first_name
    x_username = None

    if user_id == ADMIN_ID:
        if raw_text == "📥 Approved List": await get_approved_list(update, context); return
        elif raw_text == "🗑️ Declined List": await get_declined_list(update, context); return

    if raw_text:
        if "x.com" in raw_text.lower() or "twitter.com" in raw_text.lower() or "http" in raw_text.lower():
            final_link = raw_text
            x_username = final_link.rstrip('/').split('/')[-1].split('?')[0]
        else:
            x_username = raw_text.replace("@", "").strip().split()[0]
            final_link = f"https://x.com/{x_username}"
    else: final_link = "[Media Attached]"

    await update.message.reply_text("⏳ Application submitted. Please wait.")
    
    keyboard = [[InlineKeyboardButton("✅ Approve", callback_data=f'approve_{user_id}'), InlineKeyboardButton("❌ Decline", callback_data=f'deny_{user_id}')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    admin_text = f"🚨 **New Application**\n👤 User: {username}\n🔗 Profile: {final_link}"
    
    if update.message.photo:
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=update.message.photo[-1].file_id, caption=admin_text, reply_markup=reply_markup)
    else:
        try:
            await context.bot.send_photo(chat_id=ADMIN_ID, photo=f"https://unavatar.io/x/{x_username}", caption=admin_text, reply_markup=reply_markup)
        except: await context.bot.send_message(chat_id=ADMIN_ID, text=admin_text, reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data, user_id = query.data.split('_')
    msg = query.message.caption or query.message.text
    x_link = re.search(r"🔗 Profile:\s*(.*)", msg).group(1)
    user_name = re.search(r"👤 User:\s*(.*)", msg).group(1)

    if data == 'approve':
        save_user_data("approved_users.txt", user_id, user_name, x_link)
        await context.bot.send_message(chat_id=user_id, text=f"🎉 Approved!\n📱 TG: {TG_LINK}\n🐦 Follow: {TWITTER_LINK}", parse_mode='Markdown')
        await query.edit_message_caption(caption=f"{msg}\n\n✅ Approved")
    else:
        save_user_data("declined_users.txt", user_id, user_name, x_link)
        await context.bot.send_message(chat_id=user_id, text="😔 Sorry, not approved.")
        await query.edit_message_caption(caption=f"{msg}\n\n❌ Declined")

if __name__ == '__main__':
    keep_alive()
    bot_app = ApplicationBuilder().token(BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_application))
    bot_app.add_handler(CallbackQueryHandler(button_callback))
    bot_app.run_polling()