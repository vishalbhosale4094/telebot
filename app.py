from flask import Flask, request
import telegram
import requests

app = Flask(__name__)
BOT_TOKEN = '7843180063:AAFZFcKj-3QgxqQ_e97yKxfETK6CfCZ7ans'
bot = telegram.Bot(token=BOT_TOKEN)

@app.route('/telegram-webhook', methods=['POST'])
def telegram_webhook():
    data = request.json
    chat_id = data['message']['chat']['id']
    user_text = data['message']['text']

    # Send user text to your website backend
    backend_response = requests.post('https://medical-ai-chatbot-9nsp.onrender.com/webhook', json={'message': user_text})
    reply_text = backend_response.json().get('reply', 'Sorry, no reply.')

    # Send reply to Telegram
    bot.send_message(chat_id=chat_id, text=reply_text)
    return "OK"
