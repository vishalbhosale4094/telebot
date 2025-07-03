from flask import Flask, request, jsonify
import requests
import telegram

app = Flask(__name__)

# Telegram Bot Token
BOT_TOKEN = "7843180063:AAFZFcKj-3QgxqQ_e97yKxfETK6CfCZ7ans"
bot = telegram.Bot(token=BOT_TOKEN)

# Your deployed backend chatbot endpoint
WEBSITE_BACKEND_URL = "https://medical-ai-chatbot-9nsp.onrender.com/webhook"

@app.route("/")
def home():
    return "✅ Telegram bot is up and running!"

@app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():
    data = request.get_json()

    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        user_message = data["message"]["text"]

        try:
            backend_response = requests.post(
                WEBSITE_BACKEND_URL,
                json={"message": user_message},
                timeout=10
            )

            if backend_response.status_code == 200:
                reply_text = backend_response.json().get("reply", "⚠️ No reply from backend.")
            else:
                reply_text = f"❌ Backend error: {backend_response.status_code}"

        except Exception as e:
            reply_text = f"❌ Exception: {str(e)}"

        # Send reply to Telegram user
        bot.send_message(chat_id=chat_id, text=reply_text)

    return jsonify({"status": "ok"})


# ✅ This part was missing in your code — needed to run the Flask server
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
