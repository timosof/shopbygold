import os
from flask import send_from_directory
from datetime import timedelta, datetime
from dotenv import load_dotenv
from flask import Flask, jsonify, send_from_directory, request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_migrate import Migrate
FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY")

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

database_url = app.config.get("SQLALCHEMY_DATABASE_URI", "")
if "render.com" in database_url or "postgres" in database_url:
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "connect_args": {"sslmode": "require"}
    }
else:
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "connect_args": {"sslmode": "disable"}
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
from models import Newsletter, db, User, Product, Order, OrderItem, Review, PasswordResetToken, Setting, Slider


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

# ===== STEP 3: AI CHAT THAT KNOWS YOUR REAL CART =====
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from models import Cart, CartItem, Product

ai_abandoned_carts = {} # for guests only

@app.route('/api/ai-chat', methods=['POST'])
def handle_ai_chat():
    data = request.get_json()
    user_msg = data.get('message', '')
    frontend_cart = data.get('cart', [])

    real_cart = []
    try:
        verify_jwt_in_request(optional=True)
        user_id_raw = get_jwt_identity()
        if user_id_raw:
            user_id = int(user_id_raw)
            cart = Cart.query.filter_by(user_id=user_id).first()
            if cart:
                items = CartItem.query.filter_by(cart_id=cart.id).all()
                for it in items:
                    if it.product:
                        real_cart.append({"name": it.product.name, "price": float(it.product.price), "quantity": it.quantity})
    except:
        pass

    if not real_cart:
        real_cart = frontend_cart

    cart_text = ", ".join([f"{c['name']} x{c.get('quantity',1)}" for c in real_cart]) if real_cart else "empty"

    # === GROQ - FIXED MODEL ===
    try:
        from groq import Groq
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise Exception("GROQ_API_KEY not set on Render")

        client = Groq(api_key=api_key)

        sample_products = Product.query.limit(5).all()
        products_text = ", ".join([f"{p.name} (₦{p.price})" for p in sample_products]) if sample_products else "many gold jewelry"

        prompt = f"""You are ShopByGold AI assistant for Nigeria.
        Products: {products_text}
        Customer cart: {cart_text}
        Customer says: {user_msg}
        Be friendly, short (2-3 sentences). Help with products, Paystack, Pay on Delivery, delivery.
        If cart has items, mention them naturally."""

        completion = client.chat.completions.create(
            model="openai/gpt-oss-20b", # NEW - fast + cheap for ecommerce chat, replaces llama-3.3-70b
            # you can also use "openai/gpt-oss-120b" if you want smarter, or "groq/compound-mini" if you want web search
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200
        )
        reply = completion.choices[0].message.content
        print(f"Groq AI replied: {reply}")
        return jsonify({"reply": reply, "cart_count": len(real_cart)})

    

    except Exception as e:
        print(f"AI Groq error: {e}") # This will show in Render logs
        # Smart fallback
        msg_lower = user_msg.lower()
        if 'paystack' in msg_lower:
            reply = "Yes, we accept Paystack - Card, Transfer, USSD. Secure and fast! 💳"
        elif 'delivery' in msg_lower or 'pod' in msg_lower:
            reply = "Yes! Pay on Delivery available nationwide. Pay when it arrives 🚚"
        elif real_cart:
            items = ", ".join([c['name'] for c in real_cart][:2])
            reply = f"You have {items} in your cart. Want to checkout? We have Paystack and Pay on Delivery."
        else:
            keyword = user_msg.split()[-1] if user_msg.split() else ""
            found = Product.query.filter(Product.name.ilike(f"%{keyword}%")).first() if keyword else None
            if found:
                reply = f"Yes! We have {found.name} for ₦{found.price}. In stock: {found.stock}. Want to add to cart?"
            else:
                reply = "Hello! I can help with your cart, Paystack, Pay on Delivery, or find products for you. What do you need?"

    return jsonify({"reply": reply, "cart_count": len(real_cart)})

@app.route('/api/ai-cart/save', methods=['POST'])
def save_ai_cart():
    # For guests, save by IP. For logged in users, we don't need this - we read directly from DB
    data = request.get_json()
    cart = data.get('cart', [])
    user_id = request.remote_addr
    if user_id not in ai_abandoned_carts or len(ai_abandoned_carts[user_id].get("cart", []))!= len(cart):
        ai_abandoned_carts[user_id] = {"cart": cart, "time": datetime.now(), "reminded": False}
    return jsonify({"status": "saved"})

@app.route('/api/ai-cart/check', methods=['POST'])
def check_ai_cart():
    try:
        verify_jwt_in_request(optional=True)
        user_id_raw = get_jwt_identity()
        if user_id_raw:
            user_id = int(user_id_raw)
            cart = Cart.query.filter_by(user_id=user_id).first()
            if cart:
                items = CartItem.query.filter_by(cart_id=cart.id).all()
                if items:
                    key = f"user_{user_id}"
                    now = datetime.now()

                    # If never seen this cart, start timer
                    if key not in ai_abandoned_carts:
                        ai_abandoned_carts[key] = {"time": now}
                        print(f"Timer started for user {user_id}")
                        return jsonify({"abandoned": False})

                    # Check how long
                    time_diff = (now - ai_abandoned_carts[key]["time"]).total_seconds()
                    print(f"User {user_id}: {int(time_diff)}s since last reminder")

                    # REMIND EVERY 15 SECONDS FOR TESTING
                    if time_diff > 200:
                        ai_abandoned_carts[key]["time"] = now # reset timer for next 15 sec
                        names = ", ".join([it.product.name for it in items[:2] if it.product])
                        print(f"REMINDING user {user_id} about {names}")
                        return jsonify({
                            "abandoned": True,
                            "message": f"Hi, you still have {names} in your cart 🛒. Pay with Paystack or Pay on Delivery?"
                        })
                    return jsonify({"abandoned": False})
                else:
                    # Cart empty, delete timer
                    key = f"user_{user_id}"
                    if key in ai_abandoned_carts:
                        del ai_abandoned_carts[key]
    except Exception as e:
        print(f"CHECK ERROR: {e}")

    return jsonify({"abandoned": False})
# ===== END STEP 3 =====

@app.route('/api/admin/fix-sequence', methods=['GET'])
def fix_sequence():
    try:
        from sqlalchemy import text
        # fix products id sequence
        db.session.execute(text("SELECT setval(pg_get_serial_sequence('products', 'id'), COALESCE((SELECT MAX(id) FROM products),0) + 1, false)"))
        db.session.commit()
        max_id = db.session.execute(text("SELECT MAX(id) FROM products")).scalar()
        return {"msg": f"Fixed! Next id will be {max_id+1}", "max_id": max_id}
    except Exception as e:
        return {"error": str(e)}, 500
        

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
    db.create_all()
    # AUTO FIX Postgres sequence bug for order_items
    try:
        from sqlalchemy import text
        db.session.execute(text("SELECT setval(pg_get_serial_sequence('order_items', 'id'), COALESCE((SELECT MAX(id) FROM order_items), 0) + 1, false)"))
        db.session.execute(text("SELECT setval(pg_get_serial_sequence('orders', 'id'), COALESCE((SELECT MAX(id) FROM orders), 0) + 1, false)"))
        db.session.commit()
        print("DB sequences fixed")
    except Exception as e:
        print(f"Sequence fix skipped: {e}")
        db.session.rollback()


# email alert for new newsletter subscription
import threading

def send_alert_async(email_to_notify):
    try:
        import os, smtplib
        from email.mime.text import MIMEText
        sender = os.getenv("MAIL_USER", "timothyokanlawon99@gmail.com")
        app_password = os.getenv("MAIL_PASSWORD") or os.getenv("EMAIL_PASSWORD") or os.getenv("GOOGLE_APP_PASSWORD")
        if not app_password:
            print("No mail password in env")
            return
        msg = MIMEText(f"New newsletter subscriber: {email_to_notify}\n\nFrom ShopByGold")
        msg['Subject'] = "New Subscriber - ShopByGold"
        msg['From'] = sender
        msg['To'] = sender
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            server.login(sender, app_password)
            server.send_message(msg)
        print("Alert sent for", email_to_notify)
    except Exception as e:
        print("Background mail failed:", e)

@app.route('/api/newsletter/subscribe', methods=['POST'])
def subscribe_newsletter():
    data = request.get_json() or {}
    email = data.get('email','').strip().lower()
    if not email or '@' not in email:
        return jsonify({"msg": "Invalid email"}), 400
    try:
        exists = Newsletter.query.filter_by(email=email).first()
        if exists:
            return jsonify({"msg": "You already subscribed"}), 200
        db.session.add(Newsletter(email=email))
        db.session.commit()
        # Send email in background - no delay
        threading.Thread(target=send_alert_async, args=(email,), daemon=True).start()
        return jsonify({"msg": "Subscribed successfully!"}), 200
    except Exception as e:
        db.session.rollback()
        print("Subscribe error:", e)
        return jsonify({"msg": f"Error: {str(e)}"}), 500

# show in admin 
@app.route('/api/newsletter/list', methods=['GET'])
def list_newsletter():
    try:
        subs = Newsletter.query.order_by(Newsletter.created_at.desc()).all()
        result = []
        for s in subs:
            result.append({
                "email": s.email,
                "created_at": s.created_at.isoformat() if hasattr(s, 'created_at') and s.created_at else "N/A",
                "date": str(s.created_at) if hasattr(s, 'created_at') else "N/A"
            })
        print(f"Returning {len(result)} subscribers")
        return jsonify(result), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("LIST ERROR:", e)
        return jsonify({"msg": f"Error: {str(e)}"}), 500

@app.route('/api/newsletter/delete', methods=['DELETE'])
def delete_newsletter():
    data = request.get_json() or {}
    email = data.get('email','').lower()
    sub = Newsletter.query.filter_by(email=email).first()
    if sub:
        db.session.delete(sub)
        db.session.commit()
    return jsonify({"msg":"Deleted"})

# push notivation route
@app.route('/firebase-messaging-sw.js')
def firebase_sw():
    return send_from_directory('.', 'firebase-messaging-sw.js', mimetype='application/javascript')

# @app.route('/api/newsletter/list', methods=['GET'])
# def list_newsletter():
#     try:
#         subs = Newsletter.query.order_by(Newsletter.created_at.desc()).all()
#         result = []
#         for s in subs:
#             result.append({
#                 "email": s.email,
#                 "created_at": s.created_at.isoformat() if hasattr(s, 'created_at') and s.created_at else "N/A",
#                 "date": str(s.created_at) if hasattr(s, 'created_at') else "N/A"
#             })
#         print(f"Returning {len(result)} subscribers")
#         return jsonify(result), 200
#     except Exception as e:
#         import traceback
#         traceback.print_exc()
#         print("LIST ERROR:", e)
#         return jsonify({"msg": f"Error: {str(e)}"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
