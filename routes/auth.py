from flask import Blueprint, request, session, redirect, url_for, flash, render_template, current_app
import os

auth_bp = Blueprint("auth", __name__)
VALID_USERNAME = current_app.config["USERNAME"]
VALID_PASSWORD = current_app.config["PASSWORD"]

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
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
