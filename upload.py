from flask import Flask, request, Response, redirect, url_for, render_template_string
from google.cloud import storage
from functools import wraps
from utils import check_auth
import os
import csv

BUCKET_NAME = os.environ.get("BUCKET_NAME", "your-bucket-name")
CSV_FILENAME = "transactions.csv"

@requires_auth
def upload():
    if request.method == "POST":
        file = request.files["file"]
        if not file or not file.filename.endswith(".csv"):
            return "❌ Invalid file type. Only CSVs allowed."

        storage_client = storage.Client()
        existing_rows = load_existing_rows(storage_client)

        uploaded_rows = set()
        reader = csv.reader(io.StringIO(file.read().decode('utf-8')))
        for row in reader:
            uploaded_rows.add(tuple(row))

        new_rows = uploaded_rows - existing_rows
        if not new_rows:
            return "⚠️ No new rows found — all data is already uploaded."

        # Merge and write back to GCS
        merged_rows = existing_rows.union(new_rows)
        output_buffer = io.StringIO()
        writer = csv.writer(output_buffer)
        for row in sorted(merged_rows):  # Optional: sort for stability
            writer.writerow(row)

        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(CSV_NAME)
        blob.upload_from_string(output_buffer.getvalue(), content_type="text/csv")

        #return f"✅ Uploaded successfully! {len(new_rows)} new rows added."
        return redirect(url_for("summary", msg=f"{row_count} lines uploaded"))

    return render_template_string("upload.html")


def load_existing_rows(storage_client):
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(CSV_NAME)
    existing_rows = set()
    if blob.exists():
        content = blob.download_as_text()
        reader = csv.reader(io.StringIO(content))
        for row in reader:
            existing_rows.add(tuple(row))
    return existing_rows
