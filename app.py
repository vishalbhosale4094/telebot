import os
from flask import Flask, request, jsonify
import requests
import telegram
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Telegram Bot Token - MOVE THIS TO ENVIRONMENT VARIABLE FOR SECURITY
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7843180063:AAFZFcKj-3QgxqQ_e97yKxfETK6CfCZ7ans")
bot = telegram.Bot(token=BOT_TOKEN)

# Your deployed backend chatbot endpoint - UPDATED PATHS
WEBSITE_BACKEND_BASE = "https://medical-ai-chatbot-9nsp.onrender.com"
# Try different possible endpoints
POSSIBLE_ENDPOINTS = [
    f"{WEBSITE_BACKEND_BASE}/api/chat",
    f"{WEBSITE_BACKEND_BASE}/chat",
    f"{WEBSITE_BACKEND_BASE}/webhook",
    f"{WEBSITE_BACKEND_BASE}/api/message",
    f"{WEBSITE_BACKEND_BASE}/message"
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
    """Get response from backend with multiple endpoint attempts"""

    # Try different possible payload formats
    payloads = [
        {"message": user_message},
        {"text": user_message},
        {"query": user_message},
        {"input": user_message},
        {"question": user_message}
    ]

    for endpoint in POSSIBLE_ENDPOINTS:
        for payload in payloads:
            try:
                logger.info(f"🔄 Trying endpoint: {endpoint} with payload: {payload}")

                response = requests.post(
                    endpoint,
                    json=payload,
                    timeout=30,
                    headers={'Content-Type': 'application/json'}
                )

                logger.info(f"🔙 Response from {endpoint}: {response.status_code}")
                logger.info(f"🔙 Response body: {response.text}")

                if response.status_code == 200:
                    try:
                        response_data = response.json()

                        # Try different possible response field names
                        possible_fields = ["reply", "response", "answer", "message", "text", "result"]

                        for field in possible_fields:
                            if field in response_data:
                                return response_data[field]

                        # If no recognized field, return the whole response
                        return str(response_data)

                    except ValueError:
                        # If not JSON, return the text response
                        return response.text

                elif response.status_code == 404:
                    logger.info(f"❌ Endpoint {endpoint} not found, trying next...")
                    continue
                else:
                    logger.error(f"❌ Error from {endpoint}: {response.status_code}")
                    continue

            except requests.exceptions.Timeout:
                logger.error(f"❌ Timeout for {endpoint}")
                continue
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ Request error for {endpoint}: {str(e)}")
                continue

    # If all endpoints fail, try a direct GET request to test if the backend is alive
    try:
        health_check = requests.get(WEBSITE_BACKEND_BASE, timeout=10)
        if health_check.status_code == 200:
            return "🤖 I can see your medical AI website is running, but I couldn't connect to the chat API. Please check your backend endpoint configuration."
        else:
            return f"❌ Backend appears to be down (status: {health_check.status_code})"
    except:
        return "❌ Cannot connect to backend service. Please check if your medical AI backend is running."


@app.route("/test-all-endpoints", methods=["GET"])
def test_all_endpoints():
    """Test all possible backend endpoints"""
    results = {}
    test_message = "Hello, this is a test message"

    for endpoint in POSSIBLE_ENDPOINTS:
        for payload_type, payload in [
            ("message", {"message": test_message}),
            ("text", {"text": test_message}),
            ("query", {"query": test_message})
        ]:
            try:
                response = requests.post(endpoint, json=payload, timeout=10)
                key = f"{endpoint}_{payload_type}"
                results[key] = {
                    "status": response.status_code,
                    "response": response.text[:200] + "..." if len(response.text) > 200 else response.text
                }
            except Exception as e:
                results[f"{endpoint}_{payload_type}"] = {"error": str(e)}

    return jsonify(results)


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


@app.route("/test-backend", methods=["GET"])
def test_backend():
    """Test if backend is responding"""
    try:
        response = requests.get(WEBSITE_BACKEND_BASE, timeout=10)
        return jsonify({
            "status": "success",
            "backend_status": response.status_code,
            "backend_response": response.text[:500] + "..." if len(response.text) > 500 else response.text,
            "backend_url": WEBSITE_BACKEND_BASE
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })


if __name__ == '__main__':
    logger.warning("⚠️ SECURITY WARNING: Bot token is hardcoded. Use environment variables in production!")

    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port, debug=True)