from .gcs_backend import GCSBackend
from .firestore_backend import FirestoreBackend
import os

def get_storage_backend():
    backend_type = get_backend_toggle()  # 🔄 use dynamic toggle from Firestore

    if backend_type == "firestore":
        return FirestoreBackend()
    else:
        bucket_name = os.environ.get("BUCKET_NAME", "your-bucket-name")
        return GCSBackend(bucket_name)

