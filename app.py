import os
from flask import Flask, request, jsonify
import requests
import telegram
import logging
import json
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Telegram Bot Token
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7843180063:AAFZFcKj-3QgxqQ_e97yKxfETK6CfCZ7ans")
bot = telegram.Bot(token=BOT_TOKEN)

# Your medical AI website (frontend)
WEBSITE_FRONTEND_URL = "https://medical-ai-chatbot-9nsp.onrender.com"

# Simple medical responses for common questions
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
    return "✅ Medical AI Telegram Bot is running!"


@app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():
    try:
        data = request.get_json()
        logger.info(f"✅ Received webhook data: {data}")

        if not data:
            logger.error("❌ No data received")
            return jsonify({"status": "error", "message": "No data"}), 400

        if "message" in data and "text" in data["message"]:
            chat_id = data["message"]["chat"]["id"]
            user_message = data["message"]["text"]

            logger.info(f"📝 Processing message from {chat_id}: {user_message}")

            # Handle special commands
            if user_message.lower() in ["/start", "/help"]:
                reply_text = ("🏥 **MedAssist AI Bot**\n\n"
                              "I can help with basic medical information and health questions.\n\n"
                              "**Try asking about:**\n"
                              "• Common symptoms (headache, fever, cold)\n"
                              "• Basic health advice\n"
                              "• General medical questions\n\n"
                              "⚠️ **Important:** I provide general information only. "
                              "Always consult a qualified healthcare provider for medical concerns.")

            elif user_message.lower() == "/website":
                reply_text = f"🌐 Visit our full medical AI website: {WEBSITE_FRONTEND_URL}"

            else:
                # Generate medical response
                reply_text = generate_medical_response(user_message)

            # Send reply to Telegram user
            try:
                bot.send_message(chat_id=chat_id, text=reply_text, parse_mode='Markdown')
                logger.info("✅ Message sent successfully")
            except telegram.error.TelegramError as e:
                logger.error(f"❌ Telegram API error: {e}")
                # Try without markdown if parsing fails
                bot.send_message(chat_id=chat_id, text=reply_text)

        else:
            logger.info("ℹ️ Received non-text message or different update type")

        return jsonify({"status": "ok"})

    except Exception as e:
        logger.error(f"❌ Error in webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


def generate_medical_response(user_message):
    """Generate medical response based on user message"""
    message_lower = user_message.lower()

    # Check for specific medical topics
    for topic, response in MEDICAL_RESPONSES.items():
        if topic in message_lower:
            return response

    # Check for common medical keywords
    if any(word in message_lower for word in ["sick", "ill", "hurt", "pain", "ache", "symptom"]):
        return ("🏥 I understand you have a health concern. While I can provide general information, "
                "it's important to consult with a healthcare professional for proper diagnosis and treatment.\n\n"
                f"For comprehensive medical AI assistance, visit: {WEBSITE_FRONTEND_URL}\n\n"
                "Try asking about specific symptoms like 'headache', 'fever', or 'cold' for basic information"
                "For advanced medical AI assistance, visit: https: // medical-ai-chatbot-9nsp.onrender.com.")

    # Check for medication questions
    if any(word in message_lower for word in ["medicine", "medication", "drug", "pill", "tablet"]):
        return ("💊 For medication information:\n"
                "• Always consult a pharmacist or doctor\n"
                "• Read medication labels carefully\n"
                "• Don't mix medications without professional advice\n"
                "• Report side effects to your healthcare provider\n\n"
                "⚠️ Never take medical advice from chatbots for medications.")

    # Check for emergency situations
    if any(word in message_lower for word in
           ["emergency", "urgent", "severe", "bleeding", "chest pain", "difficulty breathing"]):
        return ("🚨 **EMERGENCY SITUATIONS**\n\n"
                "If you're experiencing a medical emergency:\n"
                "• Call emergency services immediately\n"
                "• Go to the nearest emergency room\n"
                "• Don't delay seeking professional help\n\n"
                "This chatbot cannot handle emergencies!")

    # Generic health response
    return ("🏥 **MedAssist AI**\n\n"
            "I can help with general health information. Try asking about:\n"
            "• Common symptoms (headache, fever, cold, cough)\n"
            "• Basic health advice\n"
            "• General wellness tips\n\n"
            f"For advanced medical AI assistance, visit: {WEBSITE_FRONTEND_URL}\n\n"
            "⚠️ Always consult healthcare professionals for medical concerns.")


# API endpoint to manually trigger backend connection test
@app.route("/find-backend-api", methods=["GET"])
def find_backend_api():
    """Try to find the actual API endpoint by inspecting the website"""
    try:
        # Get the main page
        response = requests.get(WEBSITE_FRONTEND_URL, timeout=10)

        if response.status_code == 200:
            # Look for common API patterns in the HTML/JS
            content = response.text.lower()

            possible_apis = []

            # Check for common API patterns
            if 'api/' in content:
                possible_apis.append("Found 'api/' in content")
            if 'chat' in content:
                possible_apis.append("Found 'chat' in content")
            if 'webhook' in content:
                possible_apis.append("Found 'webhook' in content")
            if 'openai' in content:
                possible_apis.append("Uses OpenAI API")
            if 'claude' in content:
                possible_apis.append("Uses Claude API")

            # Try to find script files that might contain API endpoints
            import re
            script_matches = re.findall(r'src="([^"]*\.js)"', content)

            result = {
                "status": "success",
                "website_accessible": True,
                "possible_api_indicators": possible_apis,
                "script_files": script_matches[:5],  # First 5 script files
                "recommendation": "Your website appears to be a frontend interface. You may need to create a separate API endpoint for the Telegram bot, or check if your backend has a different API URL."
            }

        else:
            result = {
                "status": "error",
                "website_accessible": False,
                "error": f"Website returned status {response.status_code}"
            }

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })


@app.route("/set-webhook", methods=["GET", "POST"])
def set_webhook():
    """Set up webhook with Telegram"""
    try:
        webhook_url = request.args.get('url') or (request.json.get('url') if request.is_json else None)

        if not webhook_url:
            return jsonify({
                "error": "Please provide webhook URL",
                "example": "/set-webhook?url=https://your-domain.com/telegram-webhook"
            }), 400

        result = bot.set_webhook(url=webhook_url)

        if result:
            return jsonify({"status": "success", "message": f"Webhook set to {webhook_url}"})
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
            "last_error_message": info.last_error_message
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    logger.info("🚀 Starting Medical AI Telegram Bot...")
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port, debug=True)