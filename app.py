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
import logging

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Token and Endpoints
TOKEN = "7843180063:AAFZFcKj-3QgxqQ_e97yKxfETK6CfCZ7ans"
RENDER_API_URL = "https://medical-ai-chatbot-9nsp.onrender.com/chat"
WEBHOOK_URL = "https://telebot-5i34.onrender.com/webhook"

# Flask App + Telegram App
app = Flask(__name__)
nest_asyncio.apply()
telegram_app = Application.builder().token(TOKEN).build()
user_histories = {}


# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_histories[update.effective_user.id] = []
        await update.message.reply_text("👋 Welcome to MedAssist! Please describe your symptoms.")
        logger.info(f"Start command executed for user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Error in start command: {e}")


# Handle user text
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        message = update.message.text
        history = user_histories.get(user_id, [])

        logger.info(f"Processing message from user {user_id}: {message}")

        payload = {"message": message, "history": history}

        # Add timeout to the request
        res = requests.post(RENDER_API_URL, json=payload, timeout=30)

        if res.status_code != 200:
            logger.error(f"API request failed with status {res.status_code}")
            await update.message.reply_text("⚠️ Sorry, the medical service is temporarily unavailable.")
            return

        data = res.json()
        logger.info(f"API response received: {data}")

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

        # Save history
        history.append({"role": "user", "parts": [message]})
        history.append({"role": "model", "parts": [data.get("response", "")]})
        user_histories[user_id] = history

        # Send message with buttons (if any)
        if data.get("needs_follow_up") and data.get("follow_up_options"):
            keyboard = [[InlineKeyboardButton(opt, callback_data=opt)] for opt in data["follow_up_options"]]
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            await update.message.reply_text(text, parse_mode="Markdown")

        # Send images (if any)
        if "image_urls" in data:
            for url in data["image_urls"]:
                try:
                    await update.message.reply_photo(url)
                except Exception as img_error:
                    logger.error(f"Failed to send image {url}: {img_error}")

        logger.info(f"Message processed successfully for user {user_id}")

    except requests.exceptions.Timeout:
        logger.error("API request timed out")
        await update.message.reply_text("⚠️ Sorry, the request timed out. Please try again.")
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        await update.message.reply_text("⚠️ Sorry, there was a network error. Please try again.")
    except Exception as e:
        logger.error(f"Error in handle_message: {e}")
        await update.message.reply_text("⚠️ Sorry, something went wrong. Please try again.")


# Handle button clicks
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()

        # Create a new update object for the button click
        new_update = Update(
            update_id=update.update_id,
            message=query.message,
            callback_query=query
        )
        new_update.message.text = query.data

        await handle_message(new_update, context)
        logger.info(f"Button click processed: {query.data}")

    except Exception as e:
        logger.error(f"Error in handle_button: {e}")


# Register Telegram handlers
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
telegram_app.add_handler(CallbackQueryHandler(handle_button))


# Flask Routes
@app.route('/')
def home():
    return "✅ MedAssist Webhook Server is Live"


@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        json_data = request.get_json(force=True)
        logger.info(f"Received webhook data: {json_data}")

        if not json_data:
            logger.warning("Received empty webhook data")
            return "ok"

        update = Update.de_json(json_data, telegram_app.bot)

        # Create new event loop for this thread if needed
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Process the update
        asyncio.run_coroutine_threadsafe(telegram_app.process_update(update), loop)

        return "ok"

    except Exception as e:
        logger.error(f"Error in webhook: {e}")
        return "error", 500


# Main async runner
async def main():
    try:
        await telegram_app.initialize()
        await telegram_app.bot.delete_webhook()
        await telegram_app.bot.set_webhook(WEBHOOK_URL)

        logger.info(f"Webhook set to: {WEBHOOK_URL}")

        # Start Flask in a separate thread
        flask_thread = Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000))))
        flask_thread.daemon = True
        flask_thread.start()

        await telegram_app.start()
        logger.info("Telegram bot started successfully")

        # Keep the main thread alive
        while True:
            await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"Error in main: {e}")


if __name__ == '__main__':
    asyncio.run(main())