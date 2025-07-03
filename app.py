from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
import requests
import os
import asyncio
import logging
import json
from datetime import datetime
from threading import Thread
import traceback

# Logging setup
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "7843180063:AAFZFcKj-3QgxqQ_e97yKxfETK6CfCZ7ans")
RENDER_API_URL = "https://medical-ai-chatbot-9nsp.onrender.com/chat"
WEBHOOK_URL = "https://telebot-5i34.onrender.com/webhook"
PORT = int(os.environ.get("PORT", 5000))

# Globals
app = Flask(__name__)
user_histories = {}
telegram_app = None


def create_telegram_app():
    return Application.builder().token(TOKEN).build()


def test_api_connection():
    try:
        res = requests.post(RENDER_API_URL, json={"message": "test", "history": []}, timeout=10)
        logger.info(f"API test response: {res.status_code}")
        return res.status_code == 200
    except Exception as e:
        logger.error(f"API connection test failed: {e}")
        return False


async def start_command(update: Update, context):
    try:
        user_id = update.effective_user.id
        user_histories[user_id] = []
        logger.info(f"Start command received from user {user_id}")
        await update.message.reply_text("👋 Welcome to MedAssist! Please describe your symptoms.")
    except Exception as e:
        logger.error(f"Error in start command: {e}")


async def test_command(update: Update, context):
    try:
        logger.info("Test command received")
        await update.message.reply_text("✅ Bot is working! Webhook is receiving messages.")
    except Exception as e:
        logger.error(f"Error in test command: {e}")


async def handle_message(update: Update, context):
    try:
        user_id = update.effective_user.id
        message = update.message.text
        history = user_histories.get(user_id, [])

        logger.info(f"Message received from user {user_id}: {message}")

        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

        payload = {"message": message, "history": history}
        logger.info(f"Sending payload to API: {payload}")

        response = requests.post(RENDER_API_URL, json=payload, timeout=30)
        logger.info(f"API response status: {response.status_code}")

        if response.status_code != 200:
            logger.error(f"API error: {response.status_code} - {response.text}")
            await update.message.reply_text("⚠️ API Error. Please try again.")
            return

        data = response.json()
        logger.info(f"API response data: {data}")
        response_text = data.get('response', 'No response')

        # Build reply
        text = f"🧠 {response_text}\n\n"
        if data.get("Symptoms") and data["Symptoms"] != ".":
            text += f"🩺 *Symptoms:* {data['Symptoms']}\n\n"
        if data.get("Remedies"):
            text += f"💊 *Remedies:* {data['Remedies']}\n\n"
        if data.get("Precautions"):
            text += f"⚠️ *Precautions:* {data['Precautions']}\n\n"
        if data.get("medication"):
            meds = data['medication']
            text += f"💊 *Medication:* {', '.join(meds) if isinstance(meds, list) else meds}\n\n"
        if data.get("Disclaimer"):
            text += f"🧾 *Disclaimer:* {data['Disclaimer']}"

        # Update history
        history.append({"role": "user", "parts": [message]})
        history.append({"role": "model", "parts": [response_text]})
        user_histories[user_id] = history

        # Send reply
        if data.get("needs_follow_up") and data.get("follow_up_options"):
            keyboard = [[InlineKeyboardButton(opt, callback_data=opt)] for opt in data["follow_up_options"]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            await update.message.reply_text(text, parse_mode="Markdown")

        # Send images
        for url in data.get("image_urls", []):
            try:
                await update.message.reply_photo(url)
            except Exception as e:
                logger.warning(f"🖼️ Failed to send image: {e}")

    except Exception as e:
        logger.error(f"❌ Error in handle_message: {e}")
        logger.error(traceback.format_exc())
        try:
            await update.message.reply_text("⚠️ Something went wrong. Please try again.")
        except:
            logger.error("Failed to send error message to user")


async def handle_button(update: Update, context):
    try:
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        message = query.data
        history = user_histories.get(user_id, [])

        logger.info(f"Button pressed by user {user_id}: {message}")

        await context.bot.send_chat_action(chat_id=query.message.chat_id, action="typing")

        payload = {"message": message, "history": history}
        response = requests.post(RENDER_API_URL, json=payload, timeout=30)

        if response.status_code != 200:
            await query.message.reply_text("⚠️ API Error. Please try again.")
            return

        data = response.json()
        response_text = data.get('response', 'No response')

        # Build text
        text = f"🧠 {response_text}\n\n"
        if data.get("Symptoms") and data["Symptoms"] != ".":
            text += f"🩺 *Symptoms:* {data['Symptoms']}\n\n"
        if data.get("Remedies"):
            text += f"💊 *Remedies:* {data['Remedies']}\n\n"
        if data.get("Precautions"):
            text += f"⚠️ *Precautions:* {data['Precautions']}\n\n"
        if data.get("medication"):
            meds = data['medication']
            text += f"💊 *Medication:* {', '.join(meds) if isinstance(meds, list) else meds}\n\n"
        if data.get("Disclaimer"):
            text += f"🧾 *Disclaimer:* {data['Disclaimer']}"

        # Update history
        history.append({"role": "user", "parts": [message]})
        history.append({"role": "model", "parts": [response_text]})
        user_histories[user_id] = history

        # Send reply
        if data.get("needs_follow_up") and data.get("follow_up_options"):
            keyboard = [[InlineKeyboardButton(opt, callback_data=opt)] for opt in data["follow_up_options"]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            await query.message.reply_text(text, parse_mode="Markdown")

        for url in data.get("image_urls", []):
            try:
                await query.message.reply_photo(url)
            except Exception as e:
                logger.warning(f"🖼️ Failed to send image: {e}")

    except Exception as e:
        logger.error(f"❌ Error in button handler: {e}")
        logger.error(traceback.format_exc())
        try:
            await query.message.reply_text("⚠️ Something went wrong. Please try again.")
        except:
            logger.error("Failed to send error message to user")


@app.route('/')
def home():
    return jsonify({
        "status": "✅ MedAssist Webhook Server is Live",
        "timestamp": datetime.now().isoformat(),
        "webhook_url": WEBHOOK_URL
    })


@app.route('/health')
def health_check():
    return jsonify({
        "server": "healthy",
        "api_connection": "✅ connected" if test_api_connection() else "❌ disconnected",
        "timestamp": datetime.now().isoformat()
    })


@app.route('/debug-api')
def debug_api():
    try:
        payload = {"message": "I have a headache", "history": []}
        res = requests.post(RENDER_API_URL, json=payload, timeout=10)
        return jsonify({
            "status_code": res.status_code,
            "headers": dict(res.headers),
            "body": res.text
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        logger.info("Webhook received")
        json_data = request.get_json(force=True)
        if not json_data:
            logger.warning("No JSON data received")
            return "ok"

        logger.info(f"Webhook data: {json_data}")
        update = Update.de_json(json_data, telegram_app.bot)

        def process():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                logger.info("Processing update")
                loop.run_until_complete(telegram_app.process_update(update))
                loop.close()
            except Exception as e:
                logger.error(f"❌ Error processing update: {e}")
                logger.error(traceback.format_exc())

        Thread(target=process).start()
        return "ok"

    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        logger.error(traceback.format_exc())
        return "error", 500


async def setup_bot():
    global telegram_app
    telegram_app = create_telegram_app()

    telegram_app.add_handler(CommandHandler("start", start_command))
    telegram_app.add_handler(CommandHandler("test", test_command))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    telegram_app.add_handler(CallbackQueryHandler(handle_button))

    await telegram_app.initialize()

    # Delete any existing webhook
    logger.info("Deleting existing webhook...")
    await telegram_app.bot.delete_webhook()

    # Set new webhook
    logger.info(f"Setting webhook to: {WEBHOOK_URL}")
    webhook_info = await telegram_app.bot.set_webhook(WEBHOOK_URL)
    logger.info(f"Webhook set successfully: {webhook_info}")

    await telegram_app.start()
    logger.info("✅ Telegram bot is running.")


def main():
    async def runner():
        await setup_bot()

        # Start Flask in background thread (non-blocking)
        def run_flask():
            logger.info(f"🌐 Starting Flask server on port {PORT}")
            app.run(host="0.0.0.0", port=PORT, use_reloader=False, debug=False)

        flask_thread = Thread(target=run_flask, daemon=True)
        flask_thread.start()

        # Keep the main thread alive
        while True:
            await asyncio.sleep(1)

    try:
        asyncio.run(runner())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        logger.error(traceback.format_exc())


if __name__ == '__main__':
    main()