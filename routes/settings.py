from flask import Blueprint, request, redirect, url_for, render_template, current_app
from utils.auth import login_required
from storage.config import get_backend_type, set_backend_type

settings_bp = Blueprint("settings", __name__)

@settings_bp.route("/settings/backend", methods=["GET", "POST"])
@login_required
def backend():
    if request.method == "POST":
        backend = request.form.get("backend")
        if backend in ["gcs", "firestore"]:
            set_backend_type(backend)
        return redirect(url_for("main.summary"))
    current_backend = get_backend_type()
    return render_template("settings.html", current_backend=current_backend)
