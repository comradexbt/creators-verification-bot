import os, logging, re, math, asyncio, requests, json, time
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
RATE_LIMIT_FILE = "rate_limits.json"
MAX_REQUESTS = 5
TIME_WINDOW = 7 * 24 * 60 * 60  # 7 days in seconds

def check_rate_limit(user_id):
    """Checks if a user has exceeded their 5 requests per 7 days limit."""
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
        # Save cleaned history anyway to keep file size small
        data[user_id_str] = recent_history
        with open(RATE_LIMIT_FILE, "w") as f:
            json.dump(data, f)
        return False # Rate limited (Blocked)
        
    # If not rate limited, add new request timestamp
    recent_history.append(current_time)
    data[user_id_str] = recent_history
    
    with open(RATE_LIMIT_FILE, "w") as f:
        json.dump(data, f)
        
    return True # Allowed

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
    # (Pehle wala collage code waisa hi hai)
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
    if user_id != TARGET_ADMIN_ID: return # Remove this line if you want public access
    
    user_states[user_id] = "INSTANT_PFP"
    user_images[user_id] = []
    await update.message.reply_text("👋 Bot Ready!", reply_markup=get_main_keyboard())

async def handle_buttons_and_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id != TARGET_ADMIN_ID: return # Remove this line if you want public access
    
    text = update.message.text
    state = user_states.get(user_id, "INSTANT_PFP")

    # Navigation buttons (In par rate limit nahi lagegi)
    if text in ["🖼️ Start Collage Maker", "🔙 Back to PFP Mode", "🗑️ Cancel Collage", "✅ Make Collage"]:
        if text == "🖼️ Start Collage Maker":
            user_states[user_id] = "COLLAGE_MAKER"
            await update.message.reply_text("🎨 Mode: Collage. Link/Photo bhejein.", reply_markup=get_collage_keyboard())
        elif text == "🔙 Back to PFP Mode":
            user_states[user_id] = "INSTANT_PFP"
            await update.message.reply_text("⚡ Mode: Instant PFP.", reply_markup=get_main_keyboard())
        elif text == "🗑️ Cancel Collage":
            user_images[user_id] = []
            await update.message.reply_text("🗑️ List Saaf.")
        elif text == "✅ Make Collage":
            if user_images.get(user_id):
                img = create_collage(user_images[user_id])
                if img: await context.bot.send_photo(chat_id=user_id, photo=img)
                user_images[user_id] = []
            else:
                await update.message.reply_text("⚠️ Pehle kuch tasveerein bhejein.")
        return

    # --- 🚦 RATE LIMIT CHECK APPLIED HERE ---
    # Sirf us waqt count hoga jab user waqai koi link ya photo bhejega
    if not check_rate_limit(user_id):
        await update.message.reply_text("⏳ Limit Reached!\n\nAap 7 dino mein sirf 5 requests bhej sakte hain. Kuch din baad dobara try karein.")
        return

    # 2. Collage Mode mein Data Save karna
    if state == "COLLAGE_MAKER":
        if update.message.photo:
            # (Photo download logic)
            await update.message.reply_text("✅ Photo Collage ke liye save ho gayi.")
        elif "x.com" in text or "twitter.com" in text:
            # (Link add logic)
            await update.message.reply_text("✅ Link Collage ke liye save ho gaya.")
        return

    # 3. Default PFP Mode
    if "x.com" in text or "twitter.com" in text:
        # (Direct PFP logic)
        await update.message.reply_text("✅ Instant PFP processing...")

if __name__ == '__main__':
    # ... Flask ...
    bot_app = ApplicationBuilder().token(BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_buttons_and_logic)) 
    bot_app.run_polling()
