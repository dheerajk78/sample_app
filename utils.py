# utils.py
from functools import wraps
from flask import request, Response
from decimal import Decimal
import os

# Hardcoded credentials (or fetch from env variables)
def check_auth(username, password):
    expected_user = os.environ.get("UPLOAD_USER", "admin")
    expected_pass = os.environ.get("UPLOAD_PASS", "secret")
    return username == expected_user and password == expected_pass

# Decorator to protect routes
def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return Response(
                "🔒 Authentication required",
                401,
                {"WWW-Authenticate": 'Basic realm="Login Required"'}
            )
        return f(*args, **kwargs)
    return decorated

def round2(x):
    return float(Decimal(x).quantize(Decimal('0.01')))

def percent(x):
    return f"{round2(x)}%"

def format_in_indian_system(value):
    if value >= 1e7:
        return f"₹{value / 1e7:.2f} Cr"
    elif value >= 1e5:
        return f"₹{value / 1e5:.2f} L"
    else:
        return f"₹{value:,.2f}"

def parse_indian_value(s):
    s = s.replace("₹", "").strip()
    if "Cr" in s:
        return float(s.replace("Cr", "").strip()) * 1e7
    elif "L" in s:
        return float(s.replace("L", "").strip()) * 1e5
    else:
        return float(s.replace(",", ""))

