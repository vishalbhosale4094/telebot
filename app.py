from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    user_message = data.get('message', '')
    # Process the message, generate reply
    reply = generate_reply(user_message)
    return jsonify({"reply": reply})

def generate_reply(message):
    # Your chatbot logic or AI model
    return "Reply from website backend: " + message
