import json
from RAG import RAG
from firebase_config import db
from get_client_data import GetData
from firebase_admin import firestore
from datetime import datetime, timezone
from flask import Flask, jsonify, request
from client_business_databse_config import client_db, about

app = Flask(__name__)
TEXT_FILE = "knowledge_base.txt"

# Load the dataset
# Create a route to match a users input to the Faq
# Match the users input to the faq
# Give back the response from the dataset as feedback


def get_user_id(data):
    return data.get('user_id') or data.get('whatsapp_id') or data.get('twitter_id')


def load_faq():
    with open('Ecommerce_FAQ_Chatbot_dataset.json', 'r') as faq_file:
        return json.load(faq_file)


def load_product_data(client_db):
    return GetData(client_db).run()


def store_message(dataset, user_id):
    for data in dataset:
        message_data = {
            "text": data["text"],
            "sender": data["sender"],  # "user" or "bot"
            "timestamp": datetime.now(timezone.utc),
        }

        chat_ref = db.collection("chat_sessions").document(
            user_id).collection("messages")
        chat_ref.add(message_data)

        # Update last active time
        db.collection("chat_sessions").document(user_id).set(
            {"last_active": datetime.now(timezone.utc)}, merge=True)

    return "Message stored successfully"


def get_chat_history(user_id):
    messages_ref = (
        db.collection("chat_sessions")
        .document(user_id)
        .collection("messages")
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(5)
    )

    messages = messages_ref.stream()
    chat_history = [{"text": msg.to_dict().get(
        "text", ""), "sender": msg.to_dict().get("sender", "")} for msg in messages]

    return chat_history[::-1]  # Oldest first


faq_data = load_faq()
products_data = load_product_data(client_db)
rag = RAG(TEXT_FILE, faq_data['questions'])
rag.update_knowledge_base(about, products_data)


@app.route('/faq', methods=['POST'])
def faq():
    print(f'[DEBUG] Received request data: {request.json}')
    user_question = request.json.get('question', '').lower()
    user_id = get_user_id(request.json)

    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    # Fetch chat history (handles empty cases)
    chat_history = get_chat_history(user_id)

    # Get AI-generated response
    response, updated_history = rag.run(
        user_question, chat_history)

    # Store both user message & bot response in Firestore
    store_message(updated_history, user_id)

    return jsonify({"response": response})


if __name__ == "__main__":
    app.run(debug=True)
