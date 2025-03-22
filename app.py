import os
import time
import json
import threading
from RAG import RAG
from dotenv import load_dotenv
from firebase_config import db
from get_client_data import GetData
from firebase_admin import firestore
from datetime import datetime, timezone
from flask import Flask, jsonify, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

load_dotenv()

# Load the dataset
# Create a route to match a users input to the Faq
# Match the users input to the faq
# Give back the response from the dataset as feedback


def get_user_id(data):
    return data.get('user_id') or data.get('whatsapp_id') or data.get('twitter_id')


def load_faq():
    with open(os.getenv('FAQS_PATH'), 'r') as faq_file:
        return json.load(faq_file)


def load_product_data():
    return get_data_instance.run()


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


def create_knowledge_base_and_vectors():
    '''
    Function to create or update the knowledge

    returns:
     - Rag class
    '''
    print("[INFO] Updating knowledge base and vector store...")
    # Fetch new data from Firebase or Google Sheets
    faq_data = load_faq()
    rag_class = RAG(text_file=os.getenv('TEXT_FILE'),
                    dataset=faq_data['questions'])
    products, about = load_product_data()

    # Update text file and ChromaDB
    rag_class.update_knowledge_base(about, products)
    rag_class.create_vector_store()

    print("[INFO] Successfully Created Knowledge Base")
    return rag_class


def poll_google_sheets(initial_interval, max_interval, checks_before_scale=5):
    """Poll Google Sheets for updates every `interval` seconds."""
    interval = initial_interval
    unchanged_count = 0

    while True:
        print(f"[INFO] Checking Google Sheets (Interval: {interval} sec)...")
        new_data = get_data_instance.get_latest_google_sheets()

        if not new_data:
            unchanged_count += 1
            print(
                f"[INFO] No changes detected ({unchanged_count}/{checks_before_scale}).")
        elif new_data:
            print('[INFO] Updating Knowledge Base with New Data')
            unchanged_count = 0
            faq_data = load_faq()
            rag_class = RAG(text_file=os.getenv('TEXT_FILE'),
                            dataset=faq_data['questions'])
            products, about = load_product_data()

            # Update text file and ChromaDB
            rag_class.update_knowledge_base(about, products)
            rag_class.create_vector_store()
            print("[INFO] Knowledge base updated successfully.")

        if unchanged_count >= checks_before_scale:
            unchanged_count = 0
            # Double but cap at max_interval
            interval = min(interval * 2, max_interval)
            print(f"[INFO] Increasing polling interval to {interval} sec.")

        time.sleep(interval)


get_data_instance = GetData(storage_type=os.getenv('STORAGE_TYPE'))
rag = create_knowledge_base_and_vectors()


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


@app.route('/whatsapp', methods=['POST'])
def whatsapp():
    incoming_msg = request.form.get('Body', '').lower()
    user_id = request.form.get('From')
    print(f'[DEBUG] Received request data: {incoming_msg}, from {user_id}')

    chat_history = get_chat_history(user_id)

    response, updated_history = rag.run(incoming_msg, chat_history)

    store_message(updated_history, user_id)

    twilio_response = MessagingResponse()
    twilio_response.message(response)

    return str(twilio_response)


# Use Render's assigned port or default to 5000
port = int(os.environ.get("PORT", 5000))

if __name__ == "__main__":
    # Start Google Sheets Polling in a separate thread
    polling_thread = threading.Thread(
        target=poll_google_sheets, args=(3600, 86400, 5), daemon=True)
    polling_thread.start()

    app.run(host="0.0.0.0", port=port, debug=True)
