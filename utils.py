# utils.py
from functools import wraps
from flask import request, Response, session, redirect, url_for
from decimal import Decimal
import os

# Hardcoded credentials (or fetch from env variables)
def check_auth(username, password):
    expected_user = os.environ.get("UPLOAD_USER", "admin")
    expected_pass = os.environ.get("UPLOAD_PASS", "secret")
    return username == expected_user and password == expected_pass

# Decorator to protect routes via Basic Auth.
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

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def round2(x):
    return float(Decimal(x).quantize(Decimal('0.01')))

def percent(x):
    return f"{round2(x)}%"

def format_in_indian_system(value, symbol='₹'):
    value = round(value, 2)

    if symbol == '₹':
        if value >= 1e7:
            return f"{symbol}{value / 1e7:.2f} Cr"
        elif value >= 1e5:
            return f"{symbol}{value / 1e5:.2f} L"
        else:
            return f"{symbol}{value:,.2f}"
    else:
        # Standard formatting for AUD or others
        return f"{symbol}{value:,.2f}"

def parse_indian_value(s):
    s = s.strip()

    if s.startswith("₹"):
        s = s.replace("₹", "").strip()
        if "Cr" in s:
            return float(s.replace("Cr", "").strip()) * 1e7
        elif "L" in s:
            return float(s.replace("L", "").strip()) * 1e5
        else:
            return float(s.replace(",", ""))
    
    elif s.startswith("A$"):
        s = s.replace("A$", "").strip()
        return float(s.replace(",", ""))
    
    else:
        # Fallback to raw float if no known currency symbol
        return float(s.replace(",", ""))

def format_currency(value, currency_symbol="₹"):
    try:
        if currency_symbol == "A$":
            return f"A${value:,.2f}"
        elif currency_symbol == "₹":
            if value >= 1e7:
                return f"₹{value / 1e7:.2f} Cr"
            elif value >= 1e5:
                return f"₹{value / 1e5:.2f} L"
            else:
                return f"₹{value:,.2f}"
        else:
            return f"{currency_symbol}{value:,.2f}"
    except Exception:
        return value

app.jinja_env.filters["format_currency"] = format_currency

'''def format_in_indian_system(value):
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
'''
