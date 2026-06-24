import telebot
import os
import time

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

# Jab bot start ho
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Bot Online! Links bhejein...")

# Links process karna
@bot.message_handler(func=lambda message: True)
def process_links(message):
    if str(message.chat.id) != "7323039280":
        return

    links = message.text.split()
    for item in links:
        username = item.replace("@", "").split("/")[-1].split("?")[0]
        # Direct URL (size=original for HQ)
        image_url = f"https://unavatar.io/twitter/{username}?size=original"
        
        try:
            bot.send_photo(message.chat.id, image_url, caption=f"✨ @{username}")
            time.sleep(1.5)
        except:
            bot.reply_to(message, f"❌ Nahi mila: {username}")

# GitHub Actions ke liye polling ka sahi tareeqa
if __name__ == "__main__":
    print("Polling started...")
    # none_stop=True aur timeout se bot stable rahega
    bot.polling(none_stop=True, timeout=60)
