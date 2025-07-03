from flask import Flask, request, jsonify
import threading
import logging
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
import httpx

# Enable detailed logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Initialize Flask app
flask_app = Flask(__name__)

# Simple health check endpoint
@flask_app.route('/', methods=['GET'])
def index():
    return "✅ MedAssist Backend is Running!"

# Example chatbot endpoint
@flask_app.route('/chat', methods=['POST'])
def handle_chat():
    data = request.get_json()
    return jsonify({
        "response": "Okay. Can you describe the pain more?",
        "Symptoms": "Headache",
        "Remedies": "Rest, drink water",
        "Precautions": "Avoid stress",
        "Guidelines": "Maintain sleep",
        "medication": ["Ibuprofen", "Paracetamol"],
        "needs_follow_up": True,
        "follow_up_options": ["Forehead", "Back of Head", "All Over"],
        "Disclaimer": "I am an AI assistant, not a real doctor.",
        "image_urls": ["https://www.example.com/sample.jpg"]
    })

# Telegram bot token and Render API URL
BOT_TOKEN = '7843180063:AAFZFcKj-3QgxqQ_e97yKxfETK6CfCZ7ans'
RENDER_API_URL = "https://medical-ai-chatbot-9nsp.onrender.com/chat"

# In-memory user session tracking
user_histories = {}

# Telegram handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_histories[user_id] = []
    await update.message.reply_text("👋 Welcome to MedAssist! Please describe your symptom.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    history = user_histories.get(user_id, [])
    payload = {"message": text, "history": history}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(RENDER_API_URL, json=payload, timeout=20)
        data = response.json()

        reply = f"🧠 {data.get('response', '')}\n\n"
        if data.get("Symptoms") and data["Symptoms"] != ".":
            reply += f"🩺 Symptoms: {data['Symptoms']}\n\n"
        if data.get("Remedies"):
            reply += f"💊 Remedies: {data['Remedies']}\n\n"
        if data.get("Precautions"):
            reply += f"⚠️ Precautions: {data['Precautions']}\n\n"
        if data.get("Guidelines"):
            reply += f"📘 Guidelines: {data['Guidelines']}\n\n"
        if data.get("medication"):
            reply += f"💊 Medication: {', '.join(data['medication'])}\n\n"
        if data.get("Disclaimer"):
            reply += f"🧾 Disclaimer: {data['Disclaimer']}\n\n"

        history.extend([
            {"role": "user", "parts": [text]},
            {"role": "model", "parts": [data['response']]}
        ])
        user_histories[user_id] = history

        if data.get("needs_follow_up") and data.get("follow_up_options"):
            keyboard = [
                [InlineKeyboardButton(opt, callback_data=opt)]
                for opt in data["follow_up_options"]
            ]
            markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(reply, reply_markup=markup)
        else:
            await update.message.reply_text(reply)

        if "image_urls" in data:
            for url in data["image_urls"]:
                await update.message.reply_photo(url)

    except Exception as e:
        logging.error(f"Error in handle_message: {e}")
        await update.message.reply_text("⚠️ Failed to process your message. Please try again.")

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    query_text = query.data
    history = user_histories.get(user_id, [])
    payload = {"message": query_text, "history": history}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(RENDER_API_URL, json=payload, timeout=20)
        data = response.json()

        reply = f"🧠 {data.get('response', '')}\n\n"
        if data.get("Symptoms") and data["Symptoms"] != ".":
            reply += f"🩺 Symptoms: {data['Symptoms']}\n\n"
        if data.get("Remedies"):
            reply += f"💊 Remedies: {data['Remedies']}\n\n"
        if data.get("Precautions"):
            reply += f"⚠️ Precautions: {data['Precautions']}\n\n"
        if data.get("Guidelines"):
            reply += f"📘 Guidelines: {data['Guidelines']}\n\n"
        if data.get("medication"):
            reply += f"💊 Medication: {', '.join(data['medication'])}\n\n"
        if data.get("Disclaimer"):
            reply += f"🧾 Disclaimer: {data['Disclaimer']}\n\n"

        history.extend([
            {"role": "user", "parts": [query_text]},
            {"role": "model", "parts": [data['response']]}
        ])
        user_histories[user_id] = history

        if data.get("needs_follow_up") and data.get("follow_up_options"):
            keyboard = [
                [InlineKeyboardButton(opt, callback_data=opt)]
                for opt in data["follow_up_options"]
            ]
            markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(reply, reply_markup=markup)
        else:
            await query.message.reply_text(reply)

        if "image_urls" in data:
            for url in data["image_urls"]:
                await query.message.reply_photo(url)

    except Exception as e:
        logging.error(f"Error in handle_button: {e}")
        await query.message.reply_text("⚠️ Failed to process your follow-up. Please try again.")

# Telegram bot worker
def run_telegram_bot():
    print("🚀 Starting Telegram bot thread...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.run_polling()

# Main launcher
if __name__ == '__main__':
    threading.Thread(target=run_telegram_bot).start()
    print("🌐 Starting Flask server...")
    flask_app.run(host='0.0.0.0', port=5000)
