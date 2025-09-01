from flask import Flask
from config import Config
from routes.main import main_bp
from routes.auth import auth_bp
from routes.settings import settings_bp

app = Flask(__name__)
app.config.from_object(Config) #Load the config object and use it within BP's using current_app

# Register Blueprints
app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(settings_bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
