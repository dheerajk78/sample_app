from flask import Blueprint, request, render_template, redirect, url_for, Response,current_app
from routes.auth import login_required
from storage import get_storage_backend
from tracker import get_portfolio_summary
from storage.config import get_backend_type
from google.cloud import storage
import io, csv
from datetime import datetime
import traceback

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def summary():
    backend = get_storage_backend()
    CSV_FILENAME=current_app.config["CSV_FILENAME"]
    BUCKET_NAME=current_app.config["BUCKET_NAME"]
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
        #summary_text = get_portfolio_summary(get_storage_backend(), filename=CSV_FILENAME)
        summary_data = get_portfolio_summary(get_storage_backend(), filename=CSV_FILENAME)


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
            #summary_text=summary_text,
            summary_data=summary_data,
            transaction_header=transaction_header,
            transaction_data=paged_data,
            page=page,
            total_pages=total_pages,
            msg=msg,
            backend_type=get_backend_type()
        )

    #except Exception as e:
        #full_trace = traceback.format_exc()
        #return Response(f"❌ Error:\n{full_trace}", status=500, mimetype='text/plain')
    except ValueError as e:
        return render_template("msg.html", msg=str(e))
        

@main_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    from flask import request, current_app
    backend = get_storage_backend()
    CSV_FILENAME = current_app.config["CSV_FILENAME"]
    BUCKET_NAME = current_app.config["BUCKET_NAME"]

    if request.method == "POST":
        file = request.files.get("file")
        if not file or not file.filename.endswith(".csv"):
            return redirect(url_for("main.summary", msg="❌ Invalid file type. Only CSVs allowed."))

        existing_header, existing_rows = backend.load_csv(CSV_FILENAME)

        file_data = file.read().decode('utf-8-sig')
        reader = csv.reader(io.StringIO(file_data))
        header = next(reader, None)

        if not header:
            return redirect(url_for("main.summary", msg="❌ Invalid or empty CSV file."))

        # Ensure asset_type exists in the header
        if "asset_type" not in header:
            header.append("asset_type")
            add_default_asset_type = True
        else:
            add_default_asset_type = False

        uploaded_rows = set()
        for row in reader:
            if not any(cell.strip() for cell in row):
                continue

            if add_default_asset_type:
                row.append("mutual_fund")
            uploaded_rows.add(tuple(row))

        new_rows = uploaded_rows - existing_rows
        if not new_rows:
            return redirect(url_for("main.summary", msg="⚠️ No new rows found — all data is already uploaded."))

        merged_rows = existing_rows.union(new_rows)
        backend.save_csv(CSV_FILENAME, header, merged_rows)

        return redirect(url_for("main.summary", msg=f"✅ {len(new_rows)} lines uploaded"))

    return render_template("upload.html")
