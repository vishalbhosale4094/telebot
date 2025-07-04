import os
from flask import Flask, request, jsonify
import requests
import telegram
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Telegram Bot Token
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7843180063:AAFZFcKj-3QgxqQ_e97yKxfETK6CfCZ7ans")
bot = telegram.Bot(token=BOT_TOKEN)

# Your medical AI website (frontend) - this is the correct URL
MEDICAL_AI_FRONTEND_URL = "https://medical-ai-chatbot-9nsp.onrender.com"

# This Telegram bot backend URL
TELEGRAM_BOT_BACKEND_URL = "https://telebot-5i34.onrender.com"

# Webhook secret for security
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "telegram-bot-secret-123")

# Medical responses for the Telegram bot
MEDICAL_RESPONSES = {
    "headache": "🏥 Common headache remedies include:\n• Rest in a quiet, dark room\n• Stay hydrated\n• Apply cold or warm compress\n• Consider over-the-counter pain relievers\n\n⚠️ Consult a doctor if headaches persist or worsen.",
    "fever": "🏥 For fever management:\n• Rest and stay hydrated\n• Take temperature regularly\n• Use fever reducers like acetaminophen or ibuprofen\n• Wear light clothing\n\n⚠️ Seek medical attention if fever is high or persistent.",
    "cold": "🏥 Common cold symptoms and care:\n• Rest and sleep\n• Drink plenty of fluids\n• Use a humidifier\n• Gargle with salt water\n• Consider vitamin C\n\n⚠️ See a doctor if symptoms worsen or last more than 10 days.",
    "cough": "🏥 Cough remedies:\n• Stay hydrated\n• Use honey (for adults)\n• Try throat lozenges\n• Use a humidifier\n• Avoid smoking and irritants\n\n⚠️ Consult a doctor for persistent or bloody cough.",
    "stomach": "🏥 Stomach issues:\n• Eat bland foods (BRAT diet)\n• Stay hydrated\n• Avoid dairy and fatty foods\n• Rest\n• Consider probiotics\n\n⚠️ See a doctor for severe pain or persistent symptoms.",
    "pain": "🏥 General pain management:\n• Rest the affected area\n• Apply ice or heat as appropriate\n• Over-the-counter pain relievers\n• Gentle stretching\n• Stay hydrated\n\n⚠️ Consult a healthcare provider for severe or chronic pain."
}


@app.route("/")
def home():
    return """
    <h1>✅ Medical AI Telegram Bot is Running!</h1>
    <p>This is the backend for the Telegram bot.</p>
    <p>Your medical AI website: <a href="{}" target="_blank">{}</a></p>
    <hr>
    <h3>Bot Management:</h3>
    <ul>
        <li><a href="/test-bot">Test Bot</a></li>
        <li><a href="/setup-webhook">Setup Webhook</a></li>
        <li><a href="/webhook-info">Webhook Info</a></li>
    </ul>
    """.format(MEDICAL_AI_FRONTEND_URL, MEDICAL_AI_FRONTEND_URL)


@app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():
    try:
        # Optional: Verify webhook secret
        secret_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if secret_header != WEBHOOK_SECRET:
            logger.warning("⚠️ Invalid webhook secret")
            # Don't return error - continue processing for now

        data = request.get_json()
        logger.info(f"✅ Received webhook data: {data}")

        if not data:
            logger.error("❌ No data received")
            return jsonify({"status": "error", "message": "No data"}), 400

        if "message" in data and "text" in data["message"]:
            chat_id = data["message"]["chat"]["id"]
            user_message = data["message"]["text"]
            user_name = data["message"]["from"].get("first_name", "User")

            logger.info(f"📝 Processing message from {user_name} ({chat_id}): {user_message}")

            # Generate response
            reply_text = generate_medical_response(user_message, user_name)

            # Send reply to Telegram user
            try:
                bot.send_message(chat_id=chat_id, text=reply_text, parse_mode='Markdown')
                logger.info("✅ Message sent successfully")
            except telegram.error.TelegramError as e:
                logger.error(f"❌ Telegram API error: {e}")
                # Try without markdown if parsing fails
                try:
                    bot.send_message(chat_id=chat_id, text=reply_text)
                    logger.info("✅ Message sent without markdown")
                except Exception as e2:
                    logger.error(f"❌ Failed to send message: {e2}")

        else:
            logger.info("ℹ️ Received non-text message or different update type")

        return jsonify({"status": "ok"})

    except Exception as e:
        logger.error(f"❌ Error in webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


def generate_medical_response(user_message, user_name=""):
    """Generate medical response based on user message"""
    message_lower = user_message.lower()

    # Handle special commands
    if message_lower in ["/start", "/help"]:
        return (f"🏥 **Welcome {user_name}! MedAssist AI Bot**\n\n"
                "I can help with basic medical information and health questions.\n\n"
                "**Try asking about:**\n"
                "• Common symptoms (headache, fever, cold)\n"
                "• Basic health advice\n"
                "• General medical questions\n\n"
                "⚠️ **Important:** I provide general information only. "
                "Always consult a qualified healthcare provider for medical concerns.")

    elif message_lower == "/website":
        return f"🌐 Visit our full medical AI website: {MEDICAL_AI_FRONTEND_URL}"

    elif message_lower == "/about":
        return ("ℹ️ **About MedAssist AI Bot**\n\n"
                "This bot provides basic medical information and health tips. "
                "It's designed to offer general guidance but should never replace "
                "professional medical advice.\n\n"
                "Created with ❤️ for health awareness.")

    # Check for specific medical topics
    for topic, response in MEDICAL_RESPONSES.items():
        if topic in message_lower:
            return f"Hi {user_name}! 👋\n\n{response}"

    # Check for common medical keywords
    if any(word in message_lower for word in ["sick", "ill", "hurt", "pain", "ache", "symptom"]):
        return (f"🏥 Hi {user_name}, I understand you have a health concern. "
                "While I can provide general information, "
                "it's important to consult with a healthcare professional for proper diagnosis and treatment.\n\n"
                f"For comprehensive medical AI assistance, visit: {MEDICAL_AI_FRONTEND_URL}\n\n"
                "Try asking about specific symptoms like 'headache', 'fever', or 'cold' for basic information.")

    # Check for emergency situations
    if any(word in message_lower for word in
           ["emergency", "urgent", "severe", "bleeding", "chest pain", "difficulty breathing"]):
        return ("🚨 **MEDICAL EMERGENCY**\n\n"
                "If you're experiencing a medical emergency:\n"
                "• Call emergency services immediately (911/102/108)\n"
                "• Go to the nearest emergency room\n"
                "• Don't delay seeking professional help\n\n"
                "This chatbot cannot handle emergencies!")

    # Greetings
    if any(word in message_lower for word in ["hello", "hi", "hey", "good morning", "good evening"]):
        return (f"👋 Hello {user_name}! Welcome to MedAssist AI Bot!\n\n"
                "I'm here to help with basic medical information. "
                "What health topic would you like to know about?")

    # Generic health response
    return (f"🏥 **Hi {user_name}! MedAssist AI**\n\n"
            "I can help with general health information. Try asking about:\n"
            "• Common symptoms (headache, fever, cold, cough)\n"
            "• Basic health advice\n"
            "• General wellness tips\n\n"
            f"For advanced medical AI assistance, visit: {MEDICAL_AI_FRONTEND_URL}\n\n"
            "⚠️ Always consult healthcare professionals for medical concerns.")


@app.route("/setup-webhook", methods=["GET"])
def setup_webhook():
    """Automatically set up webhook for this deployment"""
    try:
        webhook_url = f"{TELEGRAM_BOT_BACKEND_URL}/telegram-webhook"

        # Set webhook
        result = bot.set_webhook(
            url=webhook_url,
            secret_token=WEBHOOK_SECRET
        )

        if result:
            return jsonify({
                "status": "success",
                "message": f"Webhook set to: {webhook_url}",
                "next_step": "Your bot is now ready! Find it on Telegram and send /start",
                "bot_backend": TELEGRAM_BOT_BACKEND_URL,
                "medical_ai_frontend": MEDICAL_AI_FRONTEND_URL
            })
        else:
            return jsonify({"status": "error", "message": "Failed to set webhook"}), 500

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/webhook-info", methods=["GET"])
def webhook_info():
    """Get current webhook information"""
    try:
        info = bot.get_webhook_info()
        return jsonify({
            "url": info.url,
            "has_custom_certificate": info.has_custom_certificate,
            "pending_update_count": info.pending_update_count,
            "last_error_date": info.last_error_date.isoformat() if info.last_error_date else None,
            "last_error_message": info.last_error_message,
            "max_connections": info.max_connections,
            "allowed_updates": info.allowed_updates
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/test-bot", methods=["GET"])
def test_bot():
    """Test if bot is working"""
    try:
        bot_info = bot.get_me()
        return jsonify({
            "status": "success",
            "bot_name": bot_info.first_name,
            "bot_username": bot_info.username,
            "bot_id": bot_info.id,
            "can_join_groups": bot_info.can_join_groups,
            "can_read_all_group_messages": bot_info.can_read_all_group_messages,
            "supports_inline_queries": bot_info.supports_inline_queries
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    logger.info("🚀 Starting Medical AI Telegram Bot...")
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port, debug=False)