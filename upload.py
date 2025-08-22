from flask import Flask, request, Response, redirect, url_for, render_template
from google.cloud import storage
from functools import wraps
from utils import requires_auth
import os
import csv
import io



@requires_auth
def upload_route():
    if request.method == "POST":
        file = request.files["file"]
        if not file or not file.filename.endswith(".csv"):
            return "❌ Invalid file type. Only CSVs allowed."

        BUCKET_NAME = os.environ.get("BUCKET_NAME", "your-bucket-name")
        CSV_FILENAME = "transactions.csv"
        storage_client = storage.Client()
        existing_rows = load_existing_rows(storage_client)

        uploaded_rows = set()
        reader = csv.reader(io.StringIO(file.read().decode('utf-8-sig')))
        header = next(reader, None)  # Read and store header
        if not header:
            return "❌ Invalid or empty CSV file."

        for row in reader:
            if row and any(cell.strip() for cell in row):
                uploaded_rows.add(tuple(row))

        new_rows = uploaded_rows - existing_rows
        if not new_rows:
            return "⚠️ No new rows found — all data is already uploaded."

        merged_rows = existing_rows.union(new_rows)

        output_buffer = io.StringIO()
        writer = csv.writer(output_buffer)
        writer.writerow(header)  # Ensure header is written once
        for row in sorted(merged_rows):
            writer.writerow(row)

        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(CSV_FILENAME)
        blob.upload_from_string(output_buffer.getvalue(), content_type="text/csv")

        return redirect(url_for("summary", msg=f"✅ {len(new_rows)} lines uploaded"))

    return render_template("upload.html")


def load_existing_rows(storage_client):
    BUCKET_NAME = os.environ.get("BUCKET_NAME", "your-bucket-name")
    CSV_FILENAME = "transactions.csv"
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(CSV_FILENAME)

    existing_rows = set()
    existing_header = None

    if blob.exists():
        content = blob.download_as_text()
        reader = csv.reader(io.StringIO(content))

        # Extract header
        existing_header = next(reader, None)
        for row in reader:
            if row and any(cell.strip() for cell in row):
                existing_rows.add(tuple(row))

    return existing_header, existing_rows
