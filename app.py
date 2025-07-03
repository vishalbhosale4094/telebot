import os
import asyncio
import logging
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# --- Configuration ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7843180063:AAFZFcKj-3QgxqQ_e97yKxfETK6CfCZ7ans")
WEBHOOK_URL = os.environ.get("RENDER_EXTERNAL_URL") # Using Render's built-in env var is best

# Enable detailed logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# --- In-Memory Session Storage ---
user_histories = {}


# --- Bot Brain / Core Logic ---
def get_bot_response(user_message: str, history: list) -> dict:
    logger.info(f"CORE LOGIC: Generating response for: '{user_message}'")
    # This is the example response from your original code.
    return {
        "response": f"Okay, I've received '{user_message}'. Can you describe the pain more specifically?",
        "Symptoms": "Headache",
        "Remedies": "Rest, drink plenty of water",
        "Precautions": "Avoid bright screens and loud noises",
        "Guidelines": "Maintain a regular sleep schedule",
        "medication": ["Ibuprofen", "Paracetamol"],
        "needs_follow_up": True,
        "follow_up_options": ["Forehead", "Back of Head", "All Over"],
        "Disclaimer": "I am an AI assistant, not a real doctor. Please consult a professional for medical advice.",
        "image_urls": [],
    }


# --- Telegram Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command."""
    logger.info("HANDLER: Reached /start handler.")
    user_id = update.effective_user.id
    user_histories[user_id] = []
    await update.message.reply_text("👋 Welcome to MedAssist! Please describe your symptom.")
    logger.info("HANDLER: Finished /start handler successfully.")


async def process_and_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    history = user_histories.get(user_id, [])

    logger.info(f"PROCESSOR: Processing text: '{text}' for user {user_id}")
    await context.bot.send_chat_action(chat_id=chat_id, action='typing')

    try:
        data = get_bot_response(text, history)
        reply_parts = [f"🧠 {data.get('response', '')}"]
        if data.get("Symptoms") and data["Symptoms"] != ".": reply_parts.append(f"🩺 *Symptoms:* {data['Symptoms']}")
        if data.get("Remedies"): reply_parts.append(f"💊 *Remedies:* {data['Remedies']}")
        if data.get("Precautions"): reply_parts.append(f"⚠️ *Precautions:* {data['Precautions']}")
        if data.get("Guidelines"): reply_parts.append(f"📘 *Guidelines:* {data['Guidelines']}")
        if data.get("medication"): reply_parts.append(f"💊 *Medication:* {', '.join(data['medication'])}")
        if data.get("Disclaimer"): reply_parts.append(f"🧾 *Disclaimer:* {data['Disclaimer']}")
        reply = "\n\n".join(reply_parts)

        history.extend([{"role": "user", "parts": [text]}, {"role": "model", "parts": [data.get('response', '')]}])
        user_histories[user_id] = history

        markup = None
        if data.get("needs_follow_up") and data.get("follow_up_options"):
            keyboard = [[InlineKeyboardButton(opt, callback_data=opt)] for opt in data["follow_up_options"]]
            markup = InlineKeyboardMarkup(keyboard)

        await update.effective_message.reply_text(reply, reply_markup=markup, parse_mode='Markdown')
        logger.info(f"PROCESSOR: Successfully sent reply to user {user_id}.")
    except Exception as e:
        logger.error(f"PROCESSOR: An error occurred: {e}", exc_info=True) # exc_info=True will print the full error
        await update.effective_message.reply_text("⚠️ An error occurred while processing your request. Please try again.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("HANDLER: Reached handle_message handler.")
    await process_and_reply(update, context, update.message.text)


async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("HANDLER: Reached handle_button handler.")
    query = update.callback_query
    await query.answer()
    await process_and_reply(update, context, query.data)


# --- Flask App & Webhook Setup ---
if not WEBHOOK_URL:
    raise ValueError("Missing RENDER_EXTERNAL_URL environment variable.")

flask_app = Flask(__name__)
ptb_app = Application.builder().token(BOT_TOKEN).build()
ptb_app.add_handler(CommandHandler("start", start))
ptb_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
ptb_app.add_handler(CallbackQueryHandler(handle_button))

@flask_app.route('/')
def index():
    return "✅ MedAssist Backend with Webhook is Running!"

@flask_app.route('/telegram', methods=['POST'])
async def telegram_webhook():
    logger.info("WEBHOOK: Received a request on /telegram endpoint.")
    try:
        update = Update.de_json(request.get_json(force=True), ptb_app.bot)
        await ptb_app.process_update(update)
        logger.info("WEBHOOK: Successfully processed update.")
        return "OK", 200
    except Exception as e:
        logger.error(f"WEBHOOK: Error processing update: {e}", exc_info=True)
        return "Error", 500


async def setup_webhook():
    webhook_path = "/telegram"
    full_webhook_url = f"{WEBHOOK_URL.rstrip('/')}{webhook_path}"
    logger.info(f"SETUP: Setting webhook to: {full_webhook_url}")
    await ptb_app.bot.set_webhook(url=full_webhook_url, allowed_updates=Update.ALL_TYPES)
    logger.info("SETUP: Webhook set successfully.")

if __name__ == '__main__':
    asyncio.run(setup_webhook())
    logger.info("MAIN: Starting Flask server for production...")
    # The Gunicorn command you use in Render will run this part.
    # flask_app.run(...) is only for local testing, not production.