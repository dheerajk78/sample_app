from flask import Blueprint, request, render_template, redirect, url_for, Response
from utils.auth import login_required
from storage import get_storage_backend
from tracker import get_portfolio_summary
import io, csv
from datetime import datetime

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def summary():
    backend = get_storage_backend()
    try:
        msg = request.args.get("msg")
        page = int(request.args.get("page", 1))
        per_page = 20

        header, rows = backend.load_csv("transactions.csv")
        if not rows:
            return Response("⚠️ No transaction file found.", status=404)

        date_idx = header.index("date")

        def parse_date(row):
            try:
                return datetime.strptime(row[date_idx], "%d-%m-%Y")
            except ValueError:
                return datetime.min

        rows = sorted(rows, key=parse_date, reverse=True)
        total_rows = len(rows)
        paged_data = rows[(page-1)*per_page:page*per_page]

        summary_text = get_portfolio_summary(backend, filename="transactions.csv")

        return render_template("summary.html", summary_text=summary_text,
                               transaction_header=header, transaction_data=paged_data,
                               page=page, total_pages=(total_rows + per_page - 1)//per_page,
                               msg=msg, backend_type=backend.backend_name)
    except Exception as e:
        return Response(f"❌ Error: {str(e)}", status=500)

@main_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    from flask import request
    backend = get_storage_backend()

    if request.method == "POST":
        file = request.files.get("file")
        if not file or not file.filename.endswith(".csv"):
            return redirect(url_for("main.summary", msg="❌ Invalid file type."))

        existing_header, existing_rows = backend.load_csv("transactions.csv")
        uploaded_rows = set()
        reader = csv.reader(io.StringIO(file.read().decode("utf-8-sig")))
        header = next(reader, None)
        for row in reader:
            if row and any(cell.strip() for cell in row):
                uploaded_rows.add(tuple(row))

        new_rows = uploaded_rows - existing_rows
        if not new_rows:
            return redirect(url_for("main.summary", msg="⚠️ No new rows found."))

        backend.save_csv("transactions.csv", header, existing_rows.union(new_rows))
        return redirect(url_for("main.summary", msg=f"✅ {len(new_rows)} lines uploaded"))
    return render_template("upload.html")
