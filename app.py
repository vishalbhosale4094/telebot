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
import time

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "7843180063:AAFZFcKj-3QgxqQ_e97yKxfETK6CfCZ7ans")
RENDER_API_URL = "https://medical-ai-chatbot-9nsp.onrender.com/chat"
WEBHOOK_URL = "https://telebot-5i34.onrender.com/webhook"
PORT = int(os.environ.get("PORT", 5000))

# Global variables
app = Flask(__name__)
user_histories = {}
telegram_app = None


# Initialize Telegram Application
def create_telegram_app():
    try:
        application = Application.builder().token(TOKEN).build()
        logger.info("✅ Telegram application created successfully")
        return application
    except Exception as e:
        logger.error(f"❌ Failed to create Telegram application: {e}")
        raise


# Test API connectivity
def test_api_connection():
    try:
        test_payload = {"message": "test", "history": []}
        response = requests.post(RENDER_API_URL, json=test_payload, timeout=10)
        if response.status_code == 200:
            logger.info("✅ API connection test successful")
            return True
        else:
            logger.warning(f"⚠️ API test returned status {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ API connection test failed: {e}")
        return False


# /start command handler
async def start_command(update: Update, context):
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


# Test command handler
async def test_command(update: Update, context):
    try:
        await update.message.reply_text("✅ Bot is working! Webhook is receiving messages.")
        logger.info(f"✅ Test command executed for user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"❌ Error in test command: {e}")


# Message handler
async def handle_message(update: Update, context):
    try:
        user_id = update.effective_user.id
        username = update.effective_user.username or "Unknown"
        message = update.message.text
        history = user_histories.get(user_id, [])

        logger.info(f"📝 Processing message from user {user_id} (@{username}): {message[:50]}...")

        # Send typing action
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

        payload = {"message": message, "history": history}

        # Make API request with timeout
        try:
            response = requests.post(RENDER_API_URL, json=payload, timeout=30)

            if response.status_code != 200:
                logger.warning(f"API returned status {response.status_code}")
                await update.message.reply_text("⚠️ Sorry, the medical service is temporarily unavailable.")
                return

        except requests.exceptions.Timeout:
            logger.error("⏱️ API request timed out")
            await update.message.reply_text("⚠️ Request timed out. Please try again.")
            return

        except requests.exceptions.RequestException as e:
            logger.error(f"🌐 Network error: {e}")
            await update.message.reply_text("⚠️ Network error. Please try again.")
            return

        # Parse response
        try:
            data = response.json()
            logger.info(f"📊 API response received for user {user_id}")
        except json.JSONDecodeError:
            logger.error(f"❌ Invalid JSON response")
            await update.message.reply_text("⚠️ Invalid response received. Please try again.")
            return

        # Build response text
        response_text = data.get('response', 'No response available')
        text = f"🧠 {response_text}\n\n"

        # Add additional information
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

        # Send response
        try:
            if data.get("needs_follow_up") and data.get("follow_up_options"):
                keyboard = [[InlineKeyboardButton(opt, callback_data=opt)]
                            for opt in data["follow_up_options"]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
            else:
                await update.message.reply_text(text, parse_mode="Markdown")
        except Exception as send_error:
            logger.error(f"❌ Error sending formatted message: {send_error}")
            # Try sending without markdown
            await update.message.reply_text(text.replace("*", ""))

        # Send images if available
        if data.get("image_urls"):
            for url in data["image_urls"]:
                try:
                    await update.message.reply_photo(url)
                except Exception as img_error:
                    logger.error(f"🖼️ Failed to send image: {img_error}")

        logger.info(f"✅ Message processed successfully for user {user_id}")

    except Exception as e:
        logger.error(f"❌ Unexpected error in handle_message: {e}")
        try:
            await update.message.reply_text("⚠️ Something went wrong. Please try again.")
        except:
            pass


# Button handler
async def handle_button(update: Update, context):
    try:
        query = update.callback_query
        await query.answer()

        # Create a new message object
        message = query.message
        message.text = query.data

        # Create new update for processing
        new_update = Update(
            update_id=update.update_id,
            message=message,
            effective_user=update.effective_user,
            effective_chat=update.effective_chat
        )

        await handle_message(new_update, context)
        logger.info(f"🔘 Button processed: {query.data}")

    except Exception as e:
        logger.error(f"❌ Error in button handler: {e}")


# Flask routes
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
            logger.warning("⚠️ Empty webhook data received")
            return "ok"

        logger.info("📨 Webhook data received")

        # Process the update
        update = Update.de_json(json_data, telegram_app.bot)

        # Run in thread to avoid blocking
        def process_update():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(telegram_app.process_update(update))
                loop.close()
            except Exception as e:
                logger.error(f"❌ Error processing update: {e}")

        thread = Thread(target=process_update)
        thread.daemon = True
        thread.start()

        return "ok"

    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return "error", 500


# Setup function
async def setup_bot():
    global telegram_app

    try:
        logger.info("🚀 Setting up MedAssist Telegram Bot...")

        # Create telegram app
        telegram_app = create_telegram_app()

        # Add handlers
        telegram_app.add_handler(CommandHandler("start", start_command))
        telegram_app.add_handler(CommandHandler("test", test_command))
        telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        telegram_app.add_handler(CallbackQueryHandler(handle_button))

        # Initialize
        await telegram_app.initialize()

        # Set webhook
        await telegram_app.bot.delete_webhook()
        await telegram_app.bot.set_webhook(WEBHOOK_URL)

        logger.info(f"🔗 Webhook set to: {WEBHOOK_URL}")

        # Start the app
        await telegram_app.start()
        logger.info("✅ Telegram bot setup completed")

    except Exception as e:
        logger.error(f"❌ Setup failed: {e}")
        raise


# Main function
def main():
    try:
        # Setup bot
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(setup_bot())

        # Start Flask server
        logger.info(f"🌐 Starting Flask server on port {PORT}")
        app.run(host="0.0.0.0", port=PORT, debug=False)

    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        raise


if __name__ == '__main__':
    main()