from flask import Flask, session
from config import Config
from datetime import timedelta
from routes.main import main_bp
from routes.auth import auth_bp
from routes.settings import settings_bp


app = Flask(__name__)

#Load the config object and use it within BP's using current_app
app.config.from_object(Config) 

# Below is to enforce session logout after inactivity
@app.before_request
def make_session_permanent():
    session.permanent = True

# Register Blueprints
app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(settings_bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
