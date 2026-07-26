import os
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, jsonify, send_from_directory
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_migrate import Migrate

import cloudinary
import cloudinary.uploader

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path)

if os.path.exists(os.path.join(BASE_DIR, "Frontend")):
    FRONTEND_DIR = os.path.join(BASE_DIR, "Frontend")
else:
    FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")

from config import Config

app.config.from_object(Config)

app.config.setdefault("JWT_ACCESS_TOKEN_EXPIRES", timedelta(hours=1))
# === MAIL CONFIG - FIXED FOR RENDER + GMAIL ===
app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER", "smtp.gmail.com")
app.config["MAIL_PORT"] = int(os.getenv("MAIL_PORT", 587))
app.config["MAIL_USE_TLS"] = os.getenv("MAIL_USE_TLS", "True") == "True"
app.config["MAIL_USE_SSL"] = os.getenv("MAIL_USE_SSL", "False") == "True"
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_DEFAULT_SENDER")

print(f"MAIL USER: {app.config['MAIL_USERNAME']}")
print(f"MAIL PASS SET: {bool(app.config['MAIL_PASSWORD'])}")

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "connect_args": {
        "sslmode": "disable",
    }
}

app.config["UPLOAD_FOLDER"] = os.path.join(BASE_DIR, "uploads")
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

print(f"✅ Serving frontend from: {FRONTEND_DIR}")
print(f"✅ Frontend exists: {os.path.exists(FRONTEND_DIR)}")

# === CLOUDINARY CONFIG - NEW ===
cloudinary.config(
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key = os.getenv("CLOUDINARY_API_KEY"),
    api_secret = os.getenv("CLOUDINARY_API_SECRET"),
    secure = True
)
print(f"CLOUDINARY CLOUD: {os.getenv('CLOUDINARY_CLOUD_NAME')}")

# Init extensions
CORS(app)
mail = Mail(app)
jwt = JWTManager(app)
bcrypt = Bcrypt(app)
app.bcrypt = bcrypt
app.mail = mail

# Import db AFTER config is loaded
from models import db, User, Product, Order, OrderItem, Review, PasswordResetToken, Setting, Slider

db.init_app(app)
migrate = Migrate(app, db)

# Import blueprints
from routes.auth import auth_bp
from routes.products import products_bp
from routes.orders import orders_bp
from routes.reviews import reviews_bp
from routes.settings import settings_bp
from routes.cart import cart_bp
from routes.admin import admin_bp
from routes.paystack import paystack_bp
from routes.sliders import sliders_bp


app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(products_bp, url_prefix="/api/products")
app.register_blueprint(orders_bp, url_prefix="/api/orders")
app.register_blueprint(reviews_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(cart_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(paystack_bp, url_prefix="/api/paystack")
app.register_blueprint(sliders_bp)


# === WATCHDOG ROUTES - STOPS RENDER FROM SLEEPING ===
@app.route("/health")
def health():
    return jsonify({"status": "ok", "message": "ShopByGold is alive"}), 200


@app.route("/api/health")
def api_health():
    return jsonify({"status": "ok"}), 200


# === END WATCHDOG ===


# @app.route("/uploads/<filename>")
# def uploaded_file(filename):
#     return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)



@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        # Try shop.html first, then index.html
        if os.path.exists(os.path.join(app.static_folder, "shop.html")):
            return send_from_directory(app.static_folder, "shop.html")
        return send_from_directory(app.static_folder, "index.html")


with app.app_context():
    try:
        # Dispose any bad connections
        db.engine.dispose()
        db.create_all()
        print("✅ Database tables created")
        print(f"MAIL USER: {app.config.get('MAIL_USERNAME')}")
        print(f"MAIL PASS SET: {bool(app.config.get('MAIL_PASSWORD'))}")
    except Exception as e:
        print(f"DB init error: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
