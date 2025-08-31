# storage/config.py
import json
import os

CONFIG_FILE = "settings.json"

def get_backend_type():
    if not os.path.exists(CONFIG_FILE):
        return "gcs"
    with open(CONFIG_FILE, "r") as f:
        return json.load(f).get("backend", "gcs")

def set_backend_type(backend_type: str):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"backend": backend_type}, f)
