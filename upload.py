# upload.py

from flask import Flask, request, redirect, url_for, render_template
from storage import get_storage_backend
from utils import requires_auth

app = Flask(__name__)

CSV_FILENAME = "transactions.csv"

@app.route('/upload', methods=['GET', 'POST'])
@requires_auth
def upload_route():
    backend = get_storage_backend()

    if request.method == "POST":
        file = request.files.get("file")
        if not file or not file.filename.endswith(".csv"):
            return redirect(url_for("summary", msg=f"❌ Invalid file type. Only CSVs allowed."))

        existing_header, existing_rows = backend.load_csv(CSV_FILENAME)

        uploaded_rows = set()
        import csv, io
        reader = csv.reader(io.StringIO(file.read().decode('utf-8-sig')))
        header = next(reader, None)
        if not header:
            return redirect(url_for("summary", msg=f"❌ Invalid or empty CSV file."))

        for row in reader:
            if row and any(cell.strip() for cell in row):
                uploaded_rows.add(tuple(row))

        new_rows = uploaded_rows - existing_rows
        if not new_rows:
            return redirect(url_for("summary", msg=f"⚠️ No new rows found — all data is already uploaded."))

        merged_rows = existing_rows.union(new_rows)

        backend.save_csv(CSV_FILENAME, header, merged_rows)

        return redirect(url_for("summary", msg=f"✅ {len(new_rows)} lines uploaded"))

    return render_template("upload.html")
