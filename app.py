from flask import Flask, request, Response, redirect, url_for, render_template
from storage import get_storage_backend
from google.cloud import storage
from tracker import get_portfolio_summary
from storage import get_storage_backend
from storage.config import get_backend_type, set_backend_type
from settings_manager import get_backend_toggle, set_backend_toggle
from utils import requires_auth
import os
import io
import csv
from datetime import datetime

app = Flask(__name__)
CSV_FILENAME = "transactions.csv"
BUCKET_NAME = os.environ.get("BUCKET_NAME", "your-bucket-name")

@app.route("/")
def summary():
    try:
        msg = request.args.get("msg")  # from redirect
        page = int(request.args.get("page", 1))
        per_page = 20

        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(CSV_FILENAME)

        if not blob.exists():
            return Response("⚠️ No transaction file found.", status=404)

        # Read file
        csv_data = blob.download_as_text()
        file_obj = io.StringIO(csv_data)

        # Portfolio summary
        #summary_text = get_portfolio_summary(file_obj)
        summary_text = get_portfolio_summary(get_storage_backend(), filename=CSV_FILENAME)


        # Read again for table
        file_obj.seek(0)
        reader = csv.reader(file_obj)
        rows = list(reader)
        transaction_header = rows[0]
        transaction_data = rows[1:]

        # Sort by date column
        date_idx = transaction_header.index("date")

        def parse_date(row):
            try:
                return datetime.strptime(row[date_idx], "%d-%m-%Y")
            except ValueError:
                return datetime.min

        transaction_data.sort(key=parse_date, reverse=True)

        total_rows = len(transaction_data)
        total_pages = (total_rows + per_page - 1) // per_page
        start = (page - 1) * per_page
        end = start + per_page
        paged_data = transaction_data[start:end]

        return render_template(
            "summary.html",
            summary_text=summary_text,
            transaction_header=transaction_header,
            transaction_data=paged_data,
            page=page,
            total_pages=total_pages,
            msg=msg,
            backend_type=get_backend_type()
        )

    except Exception as e:
        return Response(f"❌ Error: {str(e)}", status=500)


@app.route("/upload", methods=["GET", "POST"])
@requires_auth
def upload():
    backend = get_storage_backend()

    if request.method == "POST":
        file = request.files.get("file")
        if not file or not file.filename.endswith(".csv"):
            return redirect(url_for("summary", msg="❌ Invalid file type. Only CSVs allowed."))

        existing_header, existing_rows = backend.load_csv(CSV_FILENAME)

        uploaded_rows = set()
        reader = csv.reader(io.StringIO(file.read().decode('utf-8-sig')))
        header = next(reader, None)
        if not header:
            return redirect(url_for("summary", msg="❌ Invalid or empty CSV file."))

        for row in reader:
            if row and any(cell.strip() for cell in row):
                uploaded_rows.add(tuple(row))

        new_rows = uploaded_rows - existing_rows
        if not new_rows:
            return redirect(url_for("summary", msg="⚠️ No new rows found — all data is already uploaded."))

        merged_rows = existing_rows.union(new_rows)
        backend.save_csv(CSV_FILENAME, header, merged_rows)

        return redirect(url_for("summary", msg=f"✅ {len(new_rows)} lines uploaded"))

    return render_template("upload.html")


@app.route("/settings/backend", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        backend = request.form.get("backend")
        if backend in ["gcs", "firestore"]:
            set_backend_toggle(backend)
        return redirect(url_for("settings"))

    current_backend = get_backend_toggle()
    return render_template("settings.html", current_backend=current_backend)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
