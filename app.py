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

# Your deployed backend chatbot endpoint
WEBSITE_BACKEND_BASE = "https://medical-ai-chatbot-9nsp.onrender.com"

# Extended list of possible endpoints for medical AI chatbots
POSSIBLE_ENDPOINTS = [
    f"{WEBSITE_BACKEND_BASE}/api/chat",
    f"{WEBSITE_BACKEND_BASE}/chat",
    f"{WEBSITE_BACKEND_BASE}/webhook",
    f"{WEBSITE_BACKEND_BASE}/api/message",
    f"{WEBSITE_BACKEND_BASE}/message",
    f"{WEBSITE_BACKEND_BASE}/api/ask",
    f"{WEBSITE_BACKEND_BASE}/ask",
    f"{WEBSITE_BACKEND_BASE}/api/query",
    f"{WEBSITE_BACKEND_BASE}/query",
    f"{WEBSITE_BACKEND_BASE}/api/respond",
    f"{WEBSITE_BACKEND_BASE}/respond",
    f"{WEBSITE_BACKEND_BASE}/api/completion",
    f"{WEBSITE_BACKEND_BASE}/completion",
    f"{WEBSITE_BACKEND_BASE}/api/generate",
    f"{WEBSITE_BACKEND_BASE}/generate",
    f"{WEBSITE_BACKEND_BASE}/api/diagnosis",
    f"{WEBSITE_BACKEND_BASE}/diagnosis",
    f"{WEBSITE_BACKEND_BASE}/api/symptom",
    f"{WEBSITE_BACKEND_BASE}/symptom",
    f"{WEBSITE_BACKEND_BASE}/api/health",
    f"{WEBSITE_BACKEND_BASE}/health",
    f"{WEBSITE_BACKEND_BASE}/api/medical",
    f"{WEBSITE_BACKEND_BASE}/medical"
]


@app.route("/")
def home():
    return "✅ Telegram bot is up and running!"


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

            # Special commands for debugging
            if user_message.lower() == "/test":
                reply_text = "🤖 Bot is working! Testing backend connection..."
                bot.send_message(chat_id=chat_id, text=reply_text)

                # Test backend and send results
                test_results = test_backend_endpoints(user_message)
                bot.send_message(chat_id=chat_id, text=test_results)
                return jsonify({"status": "ok"})

            elif user_message.lower() == "/endpoints":
                reply_text = f"🔍 Testing {len(POSSIBLE_ENDPOINTS)} possible endpoints...\n\nThis may take a moment..."
                bot.send_message(chat_id=chat_id, text=reply_text)

                # Test all endpoints and send results
                detailed_results = test_all_endpoints_detailed()
                bot.send_message(chat_id=chat_id, text=detailed_results)
                return jsonify({"status": "ok"})

            else:
                # Get response from backend
                reply_text = get_backend_response(user_message)

                # Send reply to Telegram user
                try:
                    bot.send_message(chat_id=chat_id, text=reply_text)
                    logger.info("✅ Message sent successfully")
                except telegram.error.TelegramError as e:
                    logger.error(f"❌ Telegram API error: {e}")
                    return jsonify({"status": "error", "message": str(e)}), 500

        else:
            logger.info("ℹ️ Received non-text message or different update type")

        return jsonify({"status": "ok"})

    except Exception as e:
        logger.error(f"❌ Error in webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


def get_backend_response(user_message):
    """Get response from backend with comprehensive endpoint testing"""

    # Try different possible payload formats
    payloads = [
        {"message": user_message},
        {"text": user_message},
        {"query": user_message},
        {"input": user_message},
        {"question": user_message},
        {"prompt": user_message},
        {"content": user_message},
        {"user_input": user_message},
        {"user_message": user_message}
    ]

    for endpoint in POSSIBLE_ENDPOINTS:
        for payload in payloads:
            try:
                logger.info(f"🔄 Trying endpoint: {endpoint} with payload: {payload}")

                response = requests.post(
                    endpoint,
                    json=payload,
                    timeout=15,
                    headers={
                        'Content-Type': 'application/json',
                        'Accept': 'application/json',
                        'User-Agent': 'TelegramBot/1.0'
                    }
                )

                logger.info(f"🔙 Response from {endpoint}: {response.status_code}")

                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        logger.info(f"✅ Success! Response: {response_data}")

                        # Try different possible response field names
                        possible_fields = [
                            "reply", "response", "answer", "message", "text",
                            "result", "output", "content", "data", "completion",
                            "diagnosis", "advice", "recommendation"
                        ]

                        for field in possible_fields:
                            if field in response_data:
                                return f"🏥 {response_data[field]}"

                        # If no recognized field, return the whole response
                        return f"🏥 {str(response_data)}"

                    except ValueError:
                        # If not JSON, return the text response
                        if response.text.strip():
                            return f"🏥 {response.text}"

                elif response.status_code == 404:
                    logger.info(f"❌ Endpoint {endpoint} not found")
                    continue
                elif response.status_code == 405:
                    logger.info(f"❌ Method not allowed for {endpoint}")
                    continue
                else:
                    logger.error(f"❌ Error from {endpoint}: {response.status_code} - {response.text}")
                    continue

            except requests.exceptions.Timeout:
                logger.error(f"❌ Timeout for {endpoint}")
                continue
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ Request error for {endpoint}: {str(e)}")
                continue

    # If all endpoints fail, return helpful message
    return ("🤖 I couldn't find the right API endpoint for your medical AI backend.\n\n"
            "💡 Try these commands:\n"
            "/test - Test backend connection\n"
            "/endpoints - Check all possible endpoints\n\n"
            "📝 Your backend might need a specific endpoint path or data format.")


def test_backend_endpoints(test_message="Hello, this is a test"):
    """Test a few key endpoints and return results"""
    results = []
    key_endpoints = [
        f"{WEBSITE_BACKEND_BASE}/api/chat",
        f"{WEBSITE_BACKEND_BASE}/chat",
        f"{WEBSITE_BACKEND_BASE}/webhook",
        f"{WEBSITE_BACKEND_BASE}/api/message"
    ]

    for endpoint in key_endpoints:
        try:
            response = requests.post(
                endpoint,
                json={"message": test_message},
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )
            results.append(f"✅ {endpoint}: {response.status_code}")
            if response.status_code == 200:
                results.append(f"   Response: {response.text[:100]}...")
        except Exception as e:
            results.append(f"❌ {endpoint}: {str(e)}")

    return "\n".join(results)


def test_all_endpoints_detailed():
    """Test all endpoints with detailed results"""
    working_endpoints = []
    failed_endpoints = []

    test_message = "What are the symptoms of a common cold?"

    for endpoint in POSSIBLE_ENDPOINTS:
        try:
            response = requests.post(
                endpoint,
                json={"message": test_message},
                timeout=8,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code == 200:
                working_endpoints.append(f"✅ {endpoint}")
            else:
                failed_endpoints.append(f"❌ {endpoint} ({response.status_code})")

        except Exception as e:
            failed_endpoints.append(f"❌ {endpoint} (error)")

    result = f"🔍 Endpoint Test Results:\n\n"

    if working_endpoints:
        result += f"✅ Working endpoints:\n" + "\n".join(working_endpoints) + "\n\n"

    result += f"❌ Failed: {len(failed_endpoints)}\n"
    result += f"✅ Working: {len(working_endpoints)}\n\n"

    if not working_endpoints:
        result += ("💡 No working endpoints found. Your backend might:\n"
                   "- Use a different endpoint path\n"
                   "- Expect different data format\n"
                   "- Require authentication\n"
                   "- Be temporarily down")

    return result


@app.route("/set-webhook", methods=["GET", "POST"])
def set_webhook():
    """Endpoint to set up the webhook with Telegram"""
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
            "last_error_message": info.last_error_message,
            "max_connections": info.max_connections,
            "allowed_updates": info.allowed_updates
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    logger.warning("⚠️ SECURITY WARNING: Bot token is hardcoded. Use environment variables in production!")

    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port, debug=True)