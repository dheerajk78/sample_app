from flask import Flask, request, Response, render_template_string,render_template
from google.cloud import storage
from tracker import get_portfolio_summary
from upload import upload_route
import os
import io
import csv

app = Flask(__name__)
BUCKET_NAME = os.environ.get("BUCKET_NAME", "your-bucket-name")
CSV_FILENAME = "transactions.csv"

@app.route("/")
def summary():
    try:
        page = int(request.args.get("page", 1))  # pagination: current page
        per_page = 20  # number of rows per page

        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(CSV_FILENAME)

        if not blob.exists():
            return Response("⚠️ No transaction file found.", status=404)

        # Read CSV
        csv_data = blob.download_as_text()
        file_obj = io.StringIO(csv_data)

        # Generate summary text
        summary_text = get_portfolio_summary(file_obj)

        # Read for table
        file_obj.seek(0)
        reader = csv.reader(file_obj)
        rows = list(reader)
        transaction_header = rows[0]
        transaction_data = rows[1:]

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
            total_pages=total_pages
        )

    except Exception as e:
        return Response(f"❌ Error: {str(e)}", status=500)
        
@app.route("/upload", methods=["GET", "POST"])
def upload():
    return upload_route()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
