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

# Initialize Flask
flask_app = Flask(__name__)

# ✅ Root route to avoid 'Not Found'
@flask_app.route('/', methods=['GET'])
def index():
    return "✅ MedAssist Backend is Running!"

# ✅ POST route for /chat endpoint
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
        "image_urls": ["https://www.example.com/sample.jpg"]  # Replace with real image URLs
    })

# Your Telegram Bot Token
BOT_TOKEN = "7843180063:AAFZFcKj-3QgxqQ_e97yKxfETK6CfCZ7ans"  # ✅ should match your BotFather token
  # <-- Replace with your actual bot token
RENDER_API_URL = "https://medical-ai-chatbot-9nsp.onrender.com/chat"


# In-memory user session history
user_histories = {}

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_histories[user_id] = []
    await update.message.reply_text("👋 Welcome to MedAssist! Please describe your symptom.")

# Handle normal messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    history = user_histories.get(user_id, [])
    payload = {"message": text, "history": history}

    try:
        response = requests.post(RENDER_API_URL, json=payload)
        data = response.json()

        # ✅ Build formatted response
        reply_text = f"🧠 {data.get('response', '')}\n\n"
        if data.get("Symptoms") and data["Symptoms"] != ".":
            reply_text += f"🩺 Symptoms:\n{data['Symptoms']}\n\n"
        if data.get("Remedies"):
            reply_text += f"💊 Remedies:\n{data['Remedies']}\n\n"
        if data.get("Precautions"):
            reply_text += f"⚠️ Precautions:\n{data['Precautions']}\n\n"
        if data.get("Guidelines"):
            reply_text += f"📘 Guidelines:\n{data['Guidelines']}\n\n"
        if data.get("medication"):
            reply_text += f"💊 Medication: {', '.join(data['medication'])}\n\n"
        if data.get("Disclaimer"):
            reply_text += f"🧾 Disclaimer:\n{data['Disclaimer']}\n\n"

        # ✅ Update history
        history.append({"role": "user", "parts": [text]})
        history.append({"role": "model", "parts": [data['response']]})
        user_histories[user_id] = history

        # ✅ Show follow-up buttons if needed
        if data.get("needs_follow_up") and data.get("follow_up_options"):
            keyboard = [
                [InlineKeyboardButton(opt, callback_data=opt)]
                for opt in data["follow_up_options"]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(reply_text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(reply_text)

        # ✅ Send images if available
        if "image_urls" in data:
            for url in data["image_urls"]:
                await update.message.reply_photo(url)

    except Exception as e:
        logging.error(f"Error in handle_message: {e}")
        await update.message.reply_text("⚠️ Error: Unable to process. Please try again later.")

# Handle button clicks
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    query_text = query.data
    update.message = query.message
    update.message.text = query_text
    await handle_message(update, context)

# Telegram bot thread
def run_telegram_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_button))

    # ✅ THIS IS WHERE YOU ADD IT
    app.run_polling()


# Start Flask and Telegram in parallel
if __name__ == '__main__':
    threading.Thread(target=run_telegram_bot).start()
    flask_app.run(host='0.0.0.0', port=5000)
