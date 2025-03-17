import firebase_admin
from firebase_admin import firestore
from datetime import datetime, timedelta, timezone

db = firestore.client()


def delete_old_chats():
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
    chat_sessions = db.collection("chat_sessions").where(
        "last_active", "<", cutoff_time).stream()

    for session in chat_sessions:
        db.collection("chat_sessions").document(session.id).delete()
        print(f"Deleted chat session {session.id}")


delete_old_chats()
