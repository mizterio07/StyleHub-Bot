import telebot
import random
import json
import time
import os
from datetime import datetime
from flask import Flask, request
from threading import Thread

# === CONFIGURATION FROM ENV VARIABLES ===
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHANNEL_ID = os.environ.get('CHANNEL_ID')
ADMIN_ID = int(os.environ.get('ADMIN_ID', '0'))
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')  # e.g., https://stylehub-bot.onrender.com

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
used_links = set()
is_paused = False
last_post_time = None

# === LOAD DEALS FROM JSON ===
def load_deals():
    try:
        with open("deals.json", "r", encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print("❌ Error loading deals:", e)
        return []

# === PICK NON-REPEATED DEAL ===
def get_random_deal():
    deals = load_deals()
    random.shuffle(deals)
    for deal in deals:
        link = deal.get("ek_link")
        if link and link not in used_links:
            used_links.add(link)
            return deal
    return None

# === POST A DEAL TO CHANNEL ===
def post_deal():
    global last_post_time
    deal = get_random_deal()

    if not deal:
        print("⚠️ No new deals left to post!")
        return

    caption = f"{deal['title']}\n\n🛍️ Shop Now: {deal['ek_link']}\n\n#StyleHubIND #fashion #deal"

    try:
        bot.send_message(chat_id=CHANNEL_ID, text=caption)
        last_post_time = datetime.now().strftime("%d %b %Y %I:%M %p")
        print(f"✅ Posted: {deal['title']}")
    except Exception as e:
        print("❌ Telegram send error:", e)

# === FLASK ROUTES ===
@app.route('/')
def home():
    return "🟢 StyleHub Webhook Bot is live!"

@app.route('/post')
def manual_post():
    post_deal()
    return "✅ Manual deal posted!"

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    json_str = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return '', 200

# === TELEGRAM COMMANDS ===
@bot.message_handler(commands=['start'])
def start(message):
    if message.from_user.id == ADMIN_ID:
        bot.reply_to(message, "👋 Bot is live with webhook. Use /nextdeal, /pause, /resume, /status")

@bot.message_handler(commands=['nextdeal'])
def nextdeal(message):
    if message.from_user.id == ADMIN_ID:
        post_deal()
        bot.reply_to(message, "✅ Deal posted!")

@bot.message_handler(commands=['pause'])
def pause(message):
    global is_paused
    if message.from_user.id == ADMIN_ID:
        is_paused = True
        bot.reply_to(message, "⏸️ Auto-posting paused.")

@bot.message_handler(commands=['resume'])
def resume(message):
    global is_paused
    if message.from_user.id == ADMIN_ID:
        is_paused = False
        bot.reply_to(message, "▶️ Auto-posting resumed.")

@bot.message_handler(commands=['status'])
def status(message):
    if message.from_user.id == ADMIN_ID:
        msg = f"📊 Last Post: {last_post_time or 'None yet'}\n🕒 Auto-post paused: {is_paused}"
        bot.reply_to(message, msg)

# === AUTO POST THREAD ===
def auto_post_loop():
    while True:
        if not is_paused:
            print("🕒 Auto-posting a new deal...")
            post_deal()
            time.sleep(3600)
        else:
            print("⏸️ Bot is paused.")
            time.sleep(60)

# === START EVERYTHING ===
if __name__ == '__main__':
    Thread(target=auto_post_loop).start()
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
    app.run(host='0.0.0.0', port=8080)
