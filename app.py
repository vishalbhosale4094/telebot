from flask import Flask, request, jsonify
import requests
import telegram

app = Flask(__name__)

# Your Telegram Bot Token
BOT_TOKEN = "7843180063:AAFZFcKj-3QgxqQ_e97yKxfETK6CfCZ7ans"
bot = telegram.Bot(token=BOT_TOKEN)

# Your deployed website backend URL
WEBSITE_BACKEND_URL = "https://medical-ai-chatbot-9nsp.onrender.com/webhook"

@app.route("/")
def home():
    return "✅ Telegram bot is running and connected to Medical AI backend!"

@app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():
    data = request.get_json()

    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        user_message = data["message"]["text"]

        try:
            # Send message to your website backend
            backend_response = requests.post(
                WEBSITE_BACKEND_URL,
                json={"message": user_message},
                timeout=10
            )
            backend_reply = backend_response.json().get("reply", "⚠️ No reply from backend.")

        except Exception as e:
            backend_reply = f"❌ Error from backend: {str(e)}"

        # Send reply to Telegram user
        bot.send_message(chat_id=chat_id, text=backend_reply)

    return jsonify({"ok": True})

