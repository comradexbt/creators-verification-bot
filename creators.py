# ==========================================
# --- DUMMY FLASK SERVER (For Render) ---
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running perfectly on Render!"

def run_server():
    # Render automatically PORT assign karta hai
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = Thread(target=run_server)
    t.start()

if __name__ == '__main__':
    # 1. Pehle Flask server start karein taake Render Timeout na ho
    keep_alive()
    
    # 2. Apna bot start karein
    bot_app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_buttons_and_logic)) 
    
    print("🚀 NAYA BOT START HO GAYA HAI!")
    bot_app.run_polling(drop_pending_updates=True)
