# utils.py
from functools import wraps
from flask import request, Response
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
