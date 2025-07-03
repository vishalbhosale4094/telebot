from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
import requests
import os
import nest_asyncio
import asyncio
from threading import Thread

# Config
TOKEN = "7843180063:AAFZFcKj-3QgxqQ_e97yKxfETK6CfCZ7ans"
RENDER_API_URL = "https://medical-ai-chatbot-9nsp.onrender.com/chat"
WEBHOOK_URL = "https://telebot-5i34.onrender.com/webhook"

app = Flask(__name__)
nest_asyncio.apply()
telegram_app = Application.builder().token(TOKEN).build()
user_histories = {}

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_histories[user_id] = []
    await update.message.reply_text("👋 Welcome to MedAssist! Please describe your symptoms.")

# Handle text messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    history = user_histories.get(user_id, [])

    payload = {"message": text, "history": history}

    try:
        res = requests.post(RENDER_API_URL, json=payload)
        data = res.json()

        reply = f"🧠 {data.get('response', '')}\n\n"
        if data.get("Symptoms") and data['Symptoms'] != ".":
            reply += f"🩺 *Symptoms:* {data['Symptoms']}\n\n"
        if data.get("Remedies"):
            reply += f"💊 *Remedies:* {data['Remedies']}\n\n"
        if data.get("Precautions"):
            reply += f"⚠️ *Precautions:* {data['Precautions']}\n\n"
        if data.get("Guidelines"):
            reply += f"📘 *Guidelines:* {data['Guidelines']}\n\n"
        if data.get("medication"):
            reply += f"💊 *Medication:* {', '.join(data['medication'])}\n\n"
        if data.get("Disclaimer"):
            reply += f"🧾 *Disclaimer:* {data['Disclaimer']}"

        history.append({"role": "user", "parts": [text]})
        history.append({"role": "model", "parts": [data["response"]]})
        user_histories[user_id] = history

        if data.get("needs_follow_up") and data.get("follow_up_options"):
            keyboard = [[InlineKeyboardButton(opt, callback_data=opt)] for opt in data["follow_up_options"]]
            await update.message.reply_text(reply, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            await update.message.reply_text(reply, parse_mode="Markdown")

        for url in data.get("image_urls", []):
            await update.message.reply_photo(url)

    except Exception as e:
        await update.message.reply_text("⚠️ Sorry, something went wrong.")

# Handle follow-up buttons
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    update.message = query.message
    update.message.text = query.data
    await handle_message(update, context)

# Register handlers
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
telegram_app.add_handler(CallbackQueryHandler(handle_button))

# Flask routes
@app.route('/')
def index():
    return "✅ Telegram Bot Webhook Running"

@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    telegram_app.update_queue.put(update)
    return "ok"

# Run everything
async def main():
    await telegram_app.initialize()
    await telegram_app.bot.delete_webhook()
    await telegram_app.bot.set_webhook(WEBHOOK_URL)

    Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))).start()
    await telegram_app.start()

if __name__ == '__main__':
    asyncio.run(main())
