from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler,
    MessageHandler, ContextTypes, filters
)
import requests
import os
import nest_asyncio
import asyncio

# 🔐 Bot Token and URLs
TOKEN = "7843180063:AAFZFcKj-3QgxqQ_e97yKxfETK6CfCZ7ans"
RENDER_API_URL = "https://medical-ai-chatbot-9nsp.onrender.com"
WEBHOOK_URL = "https://telebot-5i34.onrender.com"

r = requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}")
print(r.json())


# 🔧 Setup
nest_asyncio.apply()
app = Flask(__name__)
user_histories = {}
telegram_app = Application.builder().token(TOKEN).build()

# 🎯 /start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_histories[user_id] = []
    await update.message.reply_text("👋 Welcome to MedAssist! Please describe your symptoms.")

# 📩 Handle Message
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message.text
    history = user_histories.get(user_id, [])

    payload = {"message": message, "history": history}
    try:
        res = requests.post(RENDER_API_URL, json=payload)
        data = res.json()

        text = f"🧠 {data.get('response', '')}\n\n"
        if data.get("Symptoms") and data['Symptoms'] != ".":
            text += f"🩺 *Symptoms:* {data['Symptoms']}\n\n"
        if data.get("Remedies"):
            text += f"💊 *Remedies:* {data['Remedies']}\n\n"
        if data.get("Precautions"):
            text += f"⚠️ *Precautions:* {data['Precautions']}\n\n"
        if data.get("Guidelines"):
            text += f"📘 *Guidelines:* {data['Guidelines']}\n\n"
        if data.get("medication"):
            text += f"💊 *Medication:* {', '.join(data['medication'])}\n\n"
        if data.get("Disclaimer"):
            text += f"🧾 *Disclaimer:*\n{data['Disclaimer']}"

        history.append({"role": "user", "parts": [message]})
        history.append({"role": "model", "parts": [data["response"]]})
        user_histories[user_id] = history

        if data.get("needs_follow_up") and data.get("follow_up_options"):
            keyboard = [[InlineKeyboardButton(opt, callback_data=opt)] for opt in data["follow_up_options"]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            await update.message.reply_text(text, parse_mode="Markdown")

        if "image_urls" in data:
            for url in data["image_urls"]:
                await update.message.reply_photo(url)

    except Exception as e:
        await update.message.reply_text("⚠️ Sorry, something went wrong. Please try again.")

# 🔘 Handle Button Callback
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    update.message = query.message
    update.message.text = query.data
    await handle_message(update, context)

# ⏯️ Register Handlers
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
telegram_app.add_handler(CallbackQueryHandler(handle_button))

# 🌐 Flask Webhook Routes
@app.route('/')
def home():
    return "✅ MedAssist Bot Server Running (Webhook Mode)"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(force=True)
    print("📨 Webhook data received:", data)

    update = Update.de_json(data, telegram_app.bot)
    asyncio.get_event_loop().create_task(telegram_app.process_update(update))
    return "ok"



# 🧠 Main Async Runner
async def main():
    await telegram_app.initialize()
    await telegram_app.bot.delete_webhook()
    await telegram_app.bot.set_webhook(WEBHOOK_URL)
    await telegram_app.start()

    # Run Flask app in async-friendly way
    from threading import Thread
    Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))).start()

    # 💤 Keep running forever
    await telegram_app.updater.start_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        webhook_url=WEBHOOK_URL
    )


if __name__ == '__main__':
    asyncio.run(main())
