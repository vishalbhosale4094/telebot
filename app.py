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
from threading import Thread

# Telegram bot token and backend API
TOKEN = "7843180063:AAFZFcKj-3QgxqQ_e97yKxfETK6CfCZ7ans"
RENDER_API_URL = "https://medical-ai-chatbot-9nsp.onrender.com/chat"
WEBHOOK_URL = "https://telebot-5i34.onrender.com/webhook"

# Flask + Telegram setup
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
    message = update.message.text
    history = user_histories.get(user_id, [])

    payload = {"message": message, "history": history}

    try:
        res = requests.post(RENDER_API_URL, json=payload)
        data = res.json()

        text = f"🧠 {data.get('response', '')}\n\n"

        if data.get("Symptoms") and data["Symptoms"] != ".":
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
        await update.message.reply_text("⚠️ Sorry, something went wrong.")

# Handle button callbacks
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    update.message = query.message
    update.message.text = query.data
    await handle_message(update, context)

# Register all handlers
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
telegram_app.add_handler(CallbackQueryHandler(handle_button))

# Flask routes
@app.route('/')
def index():
    return "✅ Telegram Webhook is Running"

@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    telegram_app.update_queue.put(update)
    return "ok"

# Run bot and Flask using webhook (NO polling)
async def main():
    await telegram_app.initialize()
    await telegram_app.bot.delete_webhook()
    await telegram_app.bot.set_webhook(WEBHOOK_URL)

    # Start Flask in separate thread
    Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))).start()

    # Start Telegram app
    await telegram_app.start()
    await telegram_app.updater.wait_for_stop()  # ✅ Do NOT use polling

if __name__ == '__main__':
    asyncio.run(main())
