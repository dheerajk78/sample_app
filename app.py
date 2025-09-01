from flask import Flask
from routes.main import main_bp
from routes.auth import auth_bp
from routes.settings import settings_bp

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Replace in prod

# Register Blueprints
app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(settings_bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
