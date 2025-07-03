from flask import Flask, request, jsonify
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
import json
from datetime import datetime

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


# Test API connectivity
def test_api_connection():
    try:
        test_payload = {"message": "test", "history": []}
        response = requests.post(RENDER_API_URL, json=test_payload, timeout=10)
        if response.status_code == 200:
            logger.info("✅ API connection test successful")
            return True
        else:
            logger.error(f"❌ API test failed with status {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ API connection test failed: {e}")
        return False


# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        username = update.effective_user.username or "Unknown"
        user_histories[user_id] = []

        welcome_message = "👋 Welcome to MedAssist! Please describe your symptoms."
        await update.message.reply_text(welcome_message)

        logger.info(f"✅ Start command executed for user {user_id} (@{username})")

    except Exception as e:
        logger.error(f"❌ Error in start command: {e}")
        try:
            await update.message.reply_text("Sorry, there was an error. Please try again.")
        except:
            pass


# Handle user text
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        username = update.effective_user.username or "Unknown"
        message = update.message.text
        history = user_histories.get(user_id, [])

        logger.info(f"📝 Processing message from user {user_id} (@{username}): {message[:50]}...")

        # Show typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

        payload = {"message": message, "history": history}

        # Make API request with retry logic
        max_retries = 2
        for attempt in range(max_retries):
            try:
                logger.info(f"🔄 API request attempt {attempt + 1}/{max_retries}")
                response = requests.post(RENDER_API_URL, json=payload, timeout=30)

                if response.status_code == 200:
                    break
                else:
                    logger.warning(f"API returned status {response.status_code}, response: {response.text}")
                    if attempt == max_retries - 1:
                        await update.message.reply_text(
                            "⚠️ Sorry, the medical service is temporarily unavailable. Please try again later."
                        )
                        return

            except requests.exceptions.Timeout:
                logger.error(f"⏱️ API request timed out (attempt {attempt + 1})")
                if attempt == max_retries - 1:
                    await update.message.reply_text(
                        "⚠️ The request is taking too long. Please try again with a shorter message."
                    )
                    return

            except requests.exceptions.RequestException as e:
                logger.error(f"🌐 Network error (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    await update.message.reply_text(
                        "⚠️ Network error. Please check your connection and try again."
                    )
                    return

            # Wait before retry
            if attempt < max_retries - 1:
                await asyncio.sleep(2)

        # Parse response
        try:
            data = response.json()
            logger.info(f"📊 API response received for user {user_id}")
        except json.JSONDecodeError:
            logger.error(f"❌ Invalid JSON response: {response.text}")
            await update.message.reply_text("⚠️ Sorry, received invalid response. Please try again.")
            return

        # Build response text
        response_text = data.get('response', 'No response available')
        text = f"🧠 {response_text}\n\n"

        # Add additional information if available
        if data.get("Symptoms") and data['Symptoms'] != ".":
            text += f"🩺 *Symptoms:* {data['Symptoms']}\n\n"
        if data.get("Remedies"):
            text += f"💊 *Remedies:* {data['Remedies']}\n\n"
        if data.get("Precautions"):
            text += f"⚠️ *Precautions:* {data['Precautions']}\n\n"
        if data.get("Guidelines"):
            text += f"📘 *Guidelines:* {data['Guidelines']}\n\n"
        if data.get("medication"):
            medications = data['medication']
            if isinstance(medications, list):
                text += f"💊 *Medication:* {', '.join(medications)}\n\n"
            else:
                text += f"💊 *Medication:* {medications}\n\n"
        if data.get("Disclaimer"):
            text += f"🧾 *Disclaimer:*\n{data['Disclaimer']}"

        # Update conversation history
        history.append({"role": "user", "parts": [message]})
        history.append({"role": "model", "parts": [response_text]})
        user_histories[user_id] = history

        # Send response with buttons (if any)
        if data.get("needs_follow_up") and data.get("follow_up_options"):
            keyboard = [[InlineKeyboardButton(opt, callback_data=opt)]
                        for opt in data["follow_up_options"]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            await update.message.reply_text(text, parse_mode="Markdown")

        # Send images if available
        if data.get("image_urls"):
            for url in data["image_urls"]:
                try:
                    await update.message.reply_photo(url)
                except Exception as img_error:
                    logger.error(f"🖼️ Failed to send image {url}: {img_error}")

        logger.info(f"✅ Message processed successfully for user {user_id}")

    except Exception as e:
        logger.error(f"❌ Unexpected error in handle_message: {e}")
        try:
            await update.message.reply_text("⚠️ Sorry, something went wrong. Please try again.")
        except:
            pass


# Handle button clicks
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()

        # Create a message-like object for the button click
        button_message = query.message
        button_message.text = query.data

        # Create new update object
        new_update = Update(
            update_id=update.update_id,
            message=button_message,
            effective_user=update.effective_user,
            effective_chat=update.effective_chat
        )

        await handle_message(new_update, context)
        logger.info(f"🔘 Button click processed: {query.data}")

    except Exception as e:
        logger.error(f"❌ Error in handle_button: {e}")


# Register Telegram handlers
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
telegram_app.add_handler(CallbackQueryHandler(handle_button))


# Flask Routes
@app.route('/')
def home():
    return jsonify({
        "status": "✅ MedAssist Webhook Server is Live",
        "timestamp": datetime.now().isoformat(),
        "webhook_url": WEBHOOK_URL
    })


@app.route('/health')
def health_check():
    api_status = test_api_connection()
    return jsonify({
        "server": "healthy",
        "api_connection": "✅ connected" if api_status else "❌ disconnected",
        "timestamp": datetime.now().isoformat()
    })


@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        json_data = request.get_json(force=True)

        if not json_data:
            logger.warning("⚠️ Received empty webhook data")
            return "ok"

        # Log webhook data (remove sensitive info)
        safe_data = {k: v for k, v in json_data.items() if k != 'message' or not isinstance(v, dict)}
        logger.info(f"📨 Webhook received: {safe_data}")

        update = Update.de_json(json_data, telegram_app.bot)

        # Handle async processing
        def run_async():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(telegram_app.process_update(update))
                loop.close()
            except Exception as e:
                logger.error(f"❌ Error processing update: {e}")

        thread = Thread(target=run_async)
        thread.daemon = True
        thread.start()

        return "ok"

    except Exception as e:
        logger.error(f"❌ Error in webhook: {e}")
        return "error", 500


# Main function
async def main():
    try:
        logger.info("🚀 Starting MedAssist Telegram Bot...")

        # Test API connection
        if not test_api_connection():
            logger.warning("⚠️ API connection test failed, but continuing...")

        # Initialize bot
        await telegram_app.initialize()

        # Set webhook
        await telegram_app.bot.delete_webhook()
        await telegram_app.bot.set_webhook(WEBHOOK_URL)

        logger.info(f"🔗 Webhook set to: {WEBHOOK_URL}")

        # Start Flask server
        port = int(os.environ.get("PORT", 5000))
        flask_thread = Thread(target=lambda: app.run(host="0.0.0.0", port=port, debug=False))
        flask_thread.daemon = True
        flask_thread.start()

        logger.info(f"🌐 Flask server started on port {port}")

        # Start telegram app
        await telegram_app.start()
        logger.info("✅ Telegram bot started successfully")

        # Keep alive
        while True:
            await asyncio.sleep(60)
            logger.info("💓 Bot is alive")

    except Exception as e:
        logger.error(f"❌ Fatal error in main: {e}")
        raise


if __name__ == '__main__':
    asyncio.run(main())