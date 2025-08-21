from flask import Flask, request, Response, render_template_string
from google.cloud import storage
from tracker import get_portfolio_summary
from upload import upload_route
import os
import io

app = Flask(__name__)
BUCKET_NAME = os.environ.get("BUCKET_NAME", "your-bucket-name")
CSV_FILENAME = "transactions.csv"

@app.route("/")
def summary():
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(CSV_FILENAME)

        if not blob.exists():
            return Response("⚠️ No transaction file found.", status=404)

        # Download from GCS and pass as StringIO to the summary generator
        csv_data = blob.download_as_text()
        file_obj = io.StringIO(csv_data)
        summary_text = get_portfolio_summary(file_obj)
        return Response(summary_text, mimetype="text/plain")

    except Exception as e:
        return Response(f"❌ Error: {str(e)}", status=500)

@app.route("/upload", methods=["GET", "POST"])
def upload():
    return upload_route()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
