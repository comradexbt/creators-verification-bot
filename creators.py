import os, logging, math, requests, time, json, re
from io import BytesIO
from flask import Flask
from threading import Thread
from PIL import Image
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
# NAYA TOKEN YAHAN ADD HO GAYA HAI
BOT_TOKEN = "TELEGRAM_BOT_TOKEN_PLACEHOLDER"
TARGET_ADMIN_ID = 7323039280

user_images = {}
user_states = {}

# ==========================================
# --- RATE LIMITER (FILE + MEMORY) ---
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
    
    if user_id_str not in user_history:
        user_history[user_id_str] = []
        
    # 7 din ki limit (604800 seconds)
    user_history[user_id_str] = [t for t in user_history[user_id_str] if current_time - t < 604800]
    
    count = len(user_history[user_id_str])
    if count >= 5:
        return True, count
        
    user_history[user_id_str].append(current_time)
    new_count = len(user_history[user_id_str])
    
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(user_history, f)
    except:
        pass
        
    return False, new_count

# ==========================================
# --- KEYBOARDS ---
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
def create_collage(image_list):
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
# --- COMMAND HIDER (Only shows /start) ---
# ==========================================
async def post_init(application):
    # Sirf /start menu mein show hoga
    await application.bot.set_my_commands([
        BotCommand("start", "Start the verification process")
    ])

# ==========================================
# --- HANDLERS ---
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    if user_id == TARGET_ADMIN_ID: 
        user_states[user_id] = "INSTANT_PFP"
        user_images[user_id] = []
        await update.message.reply_text("👑 *Admin Bot Ready!* Welcome back.", parse_mode='Markdown', reply_markup=get_main_keyboard())
    else:
        # ACHA WALA WELCOME MESSAGE
        welcome_msg = (
            "🌟 *Welcome to Web3 Creators Verification!* 🌟\n\n"
            "Please send your Twitter/X username or profile link to get verified.\n\n"
            "🛡️ _Note: To prevent spam, you can send a maximum of 5 requests per week._"
        )
        await update.message.reply_text(welcome_msg, parse_mode='Markdown')

async def handle_buttons_and_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text if update.message.text else "No text/Link"

    # --- 1. ADMIN LOGIC ---
    if user_id == TARGET_ADMIN_ID:
        
        # 📌 ADMIN REPLY TO USER FEATURE 📌
        # Agar Admin kisi user ki request ka reply (Reply button daba kar) de raha hai
        if update.message.reply_to_message and update.message.reply_to_message.text:
            original_text = update.message.reply_to_message.text
            # Message se user ID dhundhna
            match = re.search(r"User ID: (\d+)", original_text)
            
            if match:
                target_user_id = int(match.group(1))
                reply_text = update.message.text
                
                # ACHA WALA APPROVAL/LINK MESSAGE (Jo user ko jayega)
                approval_msg = (
                    "🎉 *Congratulations!* 🎉\n\n"
                    "We have reviewed your application and the Admin has sent a response:\n\n"
                    f"🔗 {reply_text}\n\n"
                    "Welcome to the community! 🚀"
                )
                try:
                    await context.bot.send_message(chat_id=target_user_id, text=approval_msg, parse_mode='Markdown')
                    await update.message.reply_text("✅ Link/Message sent to the user successfully!")
                except Exception as e:
                    await update.message.reply_text(f"❌ Failed to send message. User might have blocked the bot.")
                return

        # Regular Admin Buttons Logic
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
            
        return # Admin ka baaki code yahin ruk jayega

    # --- 2. NORMAL USER LOGIC ---
    if user_id != TARGET_ADMIN_ID:
        is_limited, count = check_and_add_limit(user_id)
        
        if is_limited:
            # ACHA WALA SORRY MESSAGE (Limit poori hone par)
            sorry_msg = (
                "🙏 *Apologies! Limit Reached* 🙏\n\n"
                "You have used your maximum limit of 5 requests for this week. "
                "Please try again after 7 days.\n\n"
                "We appreciate your patience! ⏳"
            )
            await update.message.reply_text(sorry_msg, parse_mode='Markdown')
            return 

        # ACHA WALA SUBMIT MESSAGE
        submit_msg = f"📝 *Application Submitted! ({count}/5)*\n\nPlease wait while our team reviews it. ⏳"
        await update.message.reply_text(submit_msg, parse_mode='Markdown')
        
        username = update.message.from_user.username
        user_mention = f"@{username}" if username else "No Username"
        
        # Admin ko msg jayega with User ID taake Admin reply kar sake
        admin_alert = (
            f"📩 *New Request ({count}/5)*\n"
            f"👤 *Username:* {user_mention}\n"
            f"🆔 *User ID:* {user_id}\n\n"
            f"📄 *Data:* {text}"
        )
        await context.bot.send_message(chat_id=TARGET_ADMIN_ID, text=admin_alert, parse_mode='Markdown')
        return 

if __name__ == '__main__':
    # post_init se auto command hide/show ho jayengi
    bot_app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_buttons_and_logic)) 
    
    print("🚀 NAYA BOT START HO GAYA HAI!")
    bot_app.run_polling(drop_pending_updates=True)
