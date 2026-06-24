import os, logging, re, math, asyncio, requests, time
from io import BytesIO
from flask import Flask
from threading import Thread
from PIL import Image, ImageDraw, ImageFont
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
BOT_TOKEN = "TELEGRAM_BOT_TOKEN_PLACEHOLDER"
TARGET_ADMIN_ID = 7323039280

user_images = {}
user_states = {}

# --- RATE LIMIT SETTINGS ---
user_request_history = {}
MAX_REQUESTS = 5
TIME_WINDOW_DAYS = 7
TIME_WINDOW_SECONDS = TIME_WINDOW_DAYS * 24 * 60 * 60

def is_user_rate_limited(user_id):
    """Checks if a user has exceeded 5 requests in the last 7 days."""
    current_time = time.time()
    
    # Initialize user history if they are new
    if user_id not in user_request_history:
        user_request_history[user_id] = []
        
    # Remove old requests that are past the 7-day window
    user_request_history[user_id] = [
        t for t in user_request_history[user_id] 
        if current_time - t < TIME_WINDOW_SECONDS
    ]
    
    # Check if they hit the limit
    if len(user_request_history[user_id]) >= MAX_REQUESTS:
        return True # Limited!
    
    # Add new request timestamp and allow
    user_request_history[user_id].append(current_time)
    return False

# --- DYNAMIC KEYBOARDS ---
def get_main_keyboard():
    return ReplyKeyboardMarkup([[KeyboardButton("🖼️ Start Collage Maker")]], resize_keyboard=True, persistent=True)

def get_collage_keyboard():
    return ReplyKeyboardMarkup([
        ["✅ Make Collage", "🗑️ Cancel Collage"],
        ["🔙 Back to PFP Mode"]
    ], resize_keyboard=True, persistent=True)

# --- COLLAGE LOGIC ---
def create_collage(image_list, text_watermark="Creators Club"):
    images = []
    for img_data in image_list:
        try:
            if isinstance(img_data, str): 
                response = requests.get(img_data, timeout=5)
                img = Image.open(BytesIO(response.content)).convert("RGBA")
            else: 
                img = Image.open(BytesIO(img_data)).convert("RGBA")
            img = img.resize((150, 150))
            images.append(img)
        except: continue
    if not images: return None
    cols = math.ceil(math.sqrt(len(images)))
    rows = math.ceil(len(images) / cols)
    collage = Image.new('RGBA', (cols * 150, rows * 150), (0, 0, 0, 255))
    for idx, img in enumerate(images): collage.paste(img, ((idx % cols) * 150, (idx // cols) * 150))
    output = BytesIO()
    collage.convert("RGB").save(output, format='JPEG')
    output.seek(0)
    return output

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    # Admin Start Logic
    if user_id == TARGET_ADMIN_ID: 
        user_states[user_id] = "INSTANT_PFP"
        user_images[user_id] = []
        await update.message.reply_text("👋 Admin Bot Ready!", reply_markup=get_main_keyboard())
    # Normal User Start Logic
    else:
        await update.message.reply_text(
            "👋 Welcome!\n\nSend your Twitter/X username/link to get verified.\n(Limit: 5 requests per 7 days)"
        )

async def handle_buttons_and_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    # Agar message mein text nahi hai (jaise sirf photo ho without caption), toh avoid error
    text = update.message.text if update.message.text else "No text/Link"

    # ==========================================
    # 1. NORMAL USER LOGIC (WITH RATE LIMITS)
    # ==========================================
    if user_id != TARGET_ADMIN_ID:
        
        # SAB SE PEHLE LIMIT CHECK KAREIN:
        if is_user_rate_limited(user_id):
            # Agar 5 dafa limit poori ho gayi hai, toh ye message jaye:
            await update.message.reply_text("🚨 Your limit has been reached. Please try again after 7 days.")
            
            # RETURN bohat zaroori hai! Ye code ko yahin rok dega aur admin ko request nahi jayegi.
            return 

        # Agar limit bachi hui hai, toh ye chale ga:
        await update.message.reply_text("⏳ Application submitted. Please wait.")
        
        # Admin ko message bhejne ki logic:
        username = update.message.from_user.username
        user_mention = f"@{username}" if username else f"User ID: {user_id}"
        
        await context.bot.send_message(
            chat_id=TARGET_ADMIN_ID, 
            text=f"📩 New Request from {user_mention}:\n\n{text}"
        )
        
        # Normal user ka kaam yahan khatam, isliye return:
        return 

    # ==========================================
    # 2. ADMIN LOGIC (NO LIMITS - Sirf aapke liye)
    # ==========================================
    state = user_states.get(user_id, "INSTANT_PFP")

    # Buttons Handle karna
    if text == "🖼️ Start Collage Maker":
        user_states[user_id] = "COLLAGE_MAKER"
        await update.message.reply_text("🎨 Mode: Collage. Link/Photo bhejein.", reply_markup=get_collage_keyboard())
        return
    elif text == "🔙 Back to PFP Mode":
        user_states[user_id] = "INSTANT_PFP"
        await update.message.reply_text("⚡ Mode: Instant PFP.", reply_markup=get_main_keyboard())
        return
    elif text == "🗑️ Cancel Collage":
        user_images[user_id] = []
        await update.message.reply_text("🗑️ List Saaf.")
        return
    elif text == "✅ Make Collage":
        img = create_collage(user_images[user_id])
        if img: await context.bot.send_photo(chat_id=user_id, photo=img)
        user_images[user_id] = []
        return

    # Collage Mode Data Save
    if state == "COLLAGE_MAKER":
        if update.message.photo:
            # (Yahan aapki photo download logic ayegi)
            pass
        elif "x.com" in text or "twitter.com" in text:
            # (Yahan aapki link add logic ayegi)
            pass
        return

    # Default PFP Mode
    if "x.com" in text or "twitter.com" in text:
        # (Yahan aapki direct PFP logic ayegi)
        pass

if __name__ == '__main__':
    # Flask code agar host karne ke liye chahiye to yahan add kar lein
    bot_app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    bot_app.add_handler(CommandHandler("start", start))
    # filters.TEXT aur filters.PHOTO dono ko allow karega
    bot_app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_buttons_and_logic)) 
    
    bot_app.run_polling()
