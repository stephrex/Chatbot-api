import os
import firebase_admin
from dotenv import load_dotenv
from firebase_admin import credentials, firestore

load_dotenv()

config_json = {
    "type": os.getenv("CHAT_TYPE"),
    "project_id": os.getenv("CHAT_PROJECT_ID"),
    "private_key_id": os.getenv("CHAT_KEY_ID"),
    "private_key": os.getenv("CHAT_PRIVATE_KEY"),
    "client_email": os.getenv("CHAT_CLIENT_EMAIL"),
    "client_id": os.getenv("CHAT_CLIENT_ID"),
    "auth_uri": os.getenv("CHAT_AUTH_URI"),
    "token_uri": os.getenv("CHAT_TOKEN_URI"),
    "auth_provider_x509_cert_url": os.getenv("CHAT_AUTH_PROVIDER_X509_CERT_URL"),
    "client_x509_cert_url": os.getenv("CHAT_CLIENT_X509_CERT_URL"),
    "universe_domain": os.getenv("CHAT_UNIVERSAL_DOMAIN")
}


cred = credentials.Certificate(config_json)
firebase_admin.initialize_app(cred)

# Initialize with a unique name
if "chat_app" not in firebase_admin._apps:
    chat_app = firebase_admin.initialize_app(cred, name="chat_app")

db = firestore.client(chat_app)  # Pass the named app
