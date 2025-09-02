from datetime import timedelta
import os

class Config:
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "supersecretkey")
    BUCKET_NAME = os.environ.get("BUCKET_NAME", "your-bucket-name")
    CSV_FILENAME = "transactions.csv"
    USERNAME = os.environ.get("UPLOAD_USER", "admin")
    PASSWORD = os.environ.get("UPLOAD_PASS", "secret")
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=5)
