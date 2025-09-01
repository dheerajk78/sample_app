# storage/config.py

from google.cloud import firestore

FIRESTORE_COLLECTION = "settings"
FIRESTORE_DOC_ID = "storage_backend"

def get_backend_type():
    db = firestore.Client()
    doc = db.collection(FIRESTORE_COLLECTION).document(FIRESTORE_DOC_ID).get()
    if doc.exists:
        return doc.to_dict().get("backend", "gcs")
    return "gcs"  # default fallback

def set_backend_type(value):
    db = firestore.Client()
    db.collection(FIRESTORE_COLLECTION).document(FIRESTORE_DOC_ID).set({"backend": value})
