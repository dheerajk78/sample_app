from flask import Blueprint, request, session, redirect, url_for, flash, render_template, current_app
from functools import wraps

import os

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    VALID_USERNAME = current_app.config["USERNAME"]
    VALID_PASSWORD = current_app.config["PASSWORD"]
    if request.method == "POST":
        if request.form.get("username") == VALID_USERNAME and request.form.get("password") == VALID_PASSWORD:
            session["user"] = VALID_USERNAME
            return redirect(request.args.get("next") or url_for("main.summary"))
        flash("Invalid credentials", "error")
    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("main.summary"))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("auth.login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function
