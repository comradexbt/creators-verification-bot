import os, logging, re, math, asyncio, requests, time, json
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

# ==========================================
# --- SUPER STRICT RATE LIMITER (MEMORY + FILE) ---
# ==========================================
DATA_FILE = "rate_limits.json"
user_history = {}

# 1. Start hotay hi purana data load karega
if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE, "r") as f:
            user_history = json.load(f)
            print("Loaded previous history!")
    except:
        print("Starting fresh history.")

def check_and_add_limit(user_id):
    """Memory aur File dono mein limit update karega"""
    user_id_str = str(user_id)
    current_time = time.time()
    
    if user_id_str not in user_history:
        user_history[user_id_str] = []
        
    # 7 din se purane messages nikal dein (7 days = 604800 seconds)
    user_history[user_id_str] = [t for t in user_history[user_id_str] if current_time - t < 604800]
    
    # Current count check karein
    count = len(user_history[user_id_str])
    
    # Agar 5 ya zyada ho gaye toh Block kar do
    if count >= 5:
        return True, count
        
    # Agar limit hai, toh naya message add karein
    user_history[user_id_str].append(current_time)
    new_count = len(user_history[user_id_str])
    
    # File mein save karein taake restart par zaya na ho
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(user_history, f)
    except Exception as e:
        print("File save error:", e)
        
    return False, new_count

# ==========================================
# --- DYNAMIC KEYBOARDS ---
# ==========================================
def get_main_keyboard():
    return ReplyKeyboardMarkup([[KeyboardButton("🖼️ Start Collage Maker")]], resize_keyboard=True, persistent=True)

def get_collage_keyboard():
    return ReplyKeyboardMarkup([
        ["✅ Make Collage", "🗑️ Cancel Collage"],
        ["🔙 Back to PFP Mode"]
    ], resize_keyboard=True, persistent=True)

# ==========================================
# --- COLLAGE LOGIC ---
# ==========================================
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

# ==========================================
# --- HANDLERS ---
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    if user_id == TARGET_ADMIN_ID: 
        user_states[user_id] = "INSTANT_PFP"
        user_images[user_id] = []
        await update.message.reply_text("👋 Admin Bot Ready!", reply_markup=get_main_keyboard())
    else:
        await update.message.reply_text(
            "👋 Welcome!\n\nSend your Twitter/X username/link to get verified.\n(Limit: 5 requests per 7 days)"
        )

async def handle_buttons_and_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text if update.message.text else "No text/Link"

    # --- 1. NORMAL USER LOGIC ---
    if user_id != TARGET_ADMIN_ID:
        
        # Limit Check function call
        is_limited, count = check_and_add_limit(user_id)
        
        if is_limited:
            await update.message.reply_text("🚨 Your limit has been reached. Please try again after 7 days.")
            return # Yahan par code ruk jaye ga. Admin ko msg nahi jayega.

        # 🛑 TEST EMOJI + LIVE COUNTER: User ko numbers show honge
        await update.message.reply_text(f"🛡️ Application submitted. ({count}/5) Please wait.")
        
        username = update.message.from_user.username
        user_mention = f"@{username}" if username else f"User ID: {user_id}"
        
        await context.bot.send_message(
            chat_id=TARGET_ADMIN_ID, 
            text=f"📩 Request ({count}/5) from {user_mention}:\n\n{text}"
        )
        return 

    # --- 2. ADMIN LOGIC ---
    state = user_states.get(user_id, "INSTANT_PFP")

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

    if state == "COLLAGE_MAKER":
        if update.message.photo:
            pass
        elif "x.com" in text or "twitter.com" in text:
            pass
        return

    if "x.com" in text or "twitter.com" in text:
        pass

if __name__ == '__main__':
    bot_app = ApplicationBuilder().token(BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_buttons_and_logic)) 
    
    print("🚀 NEW BOT SCRIPT STARTED! Old instances should be stopped.")
    bot_app.run_polling(drop_pending_updates=True)
