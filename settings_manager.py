# settings_manager.py
from google.cloud import firestore

def get_backend_toggle():
    db = firestore.Client()
    doc = db.collection("settings").document("storage_backend").get()
    if doc.exists:
        return doc.to_dict().get("backend", "gcs")
    return "gcs"  # default

def set_backend_toggle(value):
    db = firestore.Client()
    db.collection("settings").document("storage_backend").set({"backend": value})
