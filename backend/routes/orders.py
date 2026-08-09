import os

from flask import Blueprint, request, jsonify, current_app
from utils.email import send_order_confirmation
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Order, OrderItem, Product, User
import requests
import json
import uuid
import traceback
from sqlalchemy import text

def fix_pg_sequences():
    try:
        db.session.execute(text("SELECT setval(pg_get_serial_sequence('order_items', 'id'), COALESCE((SELECT MAX(id) FROM order_items), 0) + 1, false)"))
        db.session.execute(text("SELECT setval(pg_get_serial_sequence('orders', 'id'), COALESCE((SELECT MAX(id) FROM orders), 0) + 1, false)"))
        db.session.commit()
    except Exception as e:
        print(f"Sequence fix: {e}")
        db.session.rollback()

orders_bp = Blueprint('orders', __name__, url_prefix='/api/orders')

# 1. INITIALIZE PAYSTACK PAYMENT - Frontend calls this first
@orders_bp.route('/paystack/initialize', methods=['POST'])
@jwt_required()
def initialize_paystack():
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        data = request.get_json() or {}

        if not data.get('items'):
            return jsonify({'msg': 'Cart is empty'}), 400

        # --- Calculate products total ---
        total = 0
        for item in data['items']:
            product_id = item.get('product_id') or item.get('id')
            quantity = int(item.get('quantity', 1))
            product = Product.query.get(product_id)
            if not product:
                return jsonify({'msg': f'Product {product_id} not found'}), 400
            total += float(product.price) * quantity

        # --- DYNAMIC SHIPPING FEE FROM ADMIN ---

        delivery_state = data.get('delivery_state') or 'Not set'
        delivery_fee = 0

        try:
            # 1. Try from request (frontend sends it)
            delivery_fee = float(data.get('delivery_fee', 0) or 0)
        except:
            delivery_fee = 0

        # 2. If not sent, get from your settings table (admin panel)
        if delivery_fee == 0:
            try:
                # your settings route saves as key='delivery_fee'
                from models import Setting
                row = Setting.query.filter_by(key='delivery_fee').first()
                if row:
                    delivery_fee = float(row.value)
            except:
                pass
        
        # 3. Fallback to your settings_bp logic
        if delivery_fee == 0:
            try:
                res = Setting.query.filter(Setting.key.ilike('%delivery%')).first()
                if res:
                    delivery_fee = float(res.value)
            except:
                delivery_fee = 1500

        total_with_fee = total + delivery_fee
        amount_kobo = int(total_with_fee * 100)

        # --- Paystack init ---
        secret = current_app.config.get("PAYSTACK_SECRET_KEY") or os.getenv("PAYSTACK_SECRET_KEY")
        if not secret:
            return jsonify({'msg': 'PAYSTACK_SECRET_KEY not set on server'}), 500

        headers = {
            'Authorization': f'Bearer {secret}',
            'Content-Type': 'application/json'
        }
        payload = {
            'email': user.email,
            'amount': amount_kobo,
            'metadata': {
                'user_id': user_id,
                'cart_items': data['items'],
                'customer_name': data.get('customer_name', ''),
                'customer_phone': data.get('customer_phone', ''),
                'customer_address': data.get('customer_address', ''),
                'delivery_fee': delivery_fee,
                'delivery_state': data.get('delivery_state', 'Not set'),
                'subtotal': total,
                'total': total_with_fee
            },
            'callback_url': f"{request.host_url.rstrip('/')}/verify.html"
        }

        res = requests.post('https://api.paystack.co/transaction/initialize', headers=headers, json=payload)
        paystack_data = res.json()

        if paystack_data.get('status'):
            return jsonify({
                'authorization_url': paystack_data['data']['authorization_url'],
                'reference': paystack_data['data']['reference'],
                'total': total_with_fee,
                'delivery_fee': delivery_fee
            }), 200
        else:
            return jsonify({'msg': f"Paystack: {paystack_data.get('message')}"}), 400

    except Exception as e:
        print(traceback.format_exc())
        # ALWAYS return JSON, never HTML
        return jsonify({'msg': f'Server error: {str(e)}'}), 500
    

# 2. VERIFY PAYMENT + CREATE ORDER
# 2. VERIFY PAYMENT + CREATE ORDER - FIXED FOR LIVE
@orders_bp.route('/paystack/verify/<reference>', methods=['GET'])
@jwt_required()
def verify_paystack(reference):
    import threading
    try:
        fix_pg_sequences()
        user_id = int(get_jwt_identity())
        
        secret = current_app.config.get("PAYSTACK_SECRET_KEY") or os.getenv("PAYSTACK_SECRET_KEY")
        if not secret:
            return jsonify({'msg': 'PAYSTACK_SECRET_KEY not set on Render'}), 500

        headers = {'Authorization': f'Bearer {secret}'}
        
        res = requests.get(
            f'https://api.paystack.co/transaction/verify/{reference}',
            headers=headers,
            timeout=20
        )
        paystack_data = res.json()
        
        if not paystack_data.get('status') or paystack_data['data']['status'] != 'success':
            return jsonify({'msg': 'Payment not successful'}), 400
            
        metadata = paystack_data['data'].get('metadata', {})
        cart_items = metadata.get('cart_items', [])
        
        # If order already exists, return it instantly
        existing_order = Order.query.filter_by(payment_reference=reference).first()
        if existing_order:
            try:
                return jsonify(existing_order.to_dict()), 200
            except:
                return jsonify({'order_id': existing_order.id, 'status': 'success'}), 200
        
        total_amount = paystack_data['data']['amount'] / 100
        
        order = Order(
            user_id=user_id,
            total=total_amount,
            status='paid',
            payment_reference=reference,
            customer_name=metadata.get('customer_name', ''),
            customer_phone=metadata.get('customer_phone', ''),
            customer_address=metadata.get('customer_address', ''),
            delivery_state=metadata.get('delivery_state', ''),
            delivery_fee=metadata.get('delivery_fee', 0)
        )
        db.session.add(order)
        db.session.flush()
        
        for item in cart_items:
            product_id = item.get('product_id') or item.get('id')
            quantity = int(item.get('quantity', 1))
            product = Product.query.get(product_id)
            if not product:
                continue
            # Never block order for stock
            if product.stock is not None and product.stock < quantity:
                product.stock = 100
            if product.stock is not None:
                product.stock -= quantity
            order_item = OrderItem(
                order_id=order.id,
                product_id=product_id,
                quantity=quantity,
                price=product.price
            )
            db.session.add(order_item)
        
        db.session.commit()

        # FIX: Send email in BACKGROUND THREAD
        def send_email_bg(app, order_id, user_id):
            try:
                with app.app_context():
                    customer = User.query.get(user_id)
                    order_obj = Order.query.get(order_id)
                    if customer and order_obj:
                        send_order_confirmation(app, order_obj, customer.email)
            except Exception as e:
                print(f"BG Email failed: {e}")

        threading.Thread(
            target=send_email_bg, 
            args=(current_app._get_current_object(), order.id, user_id),
            daemon=True
        ).start()
        
        # Return instantly - don't wait for email
        try:
            return jsonify(order.to_dict()), 200
        except:
            return jsonify({'order_id': order.id, 'status': 'success', 'msg': 'Payment verified'}), 200
        
    except Exception as e:
        db.session.rollback()
        print(traceback.format_exc())
        return jsonify({'msg': f'Verification error: {str(e)}'}), 500

# 3. CREATE ORDER - Cash on Delivery
@orders_bp.route('/create', methods=['POST'])
@jwt_required()
def create_order():
    try:
        fix_pg_sequences()
        user_id = get_jwt_identity()
        data = request.get_json()
        
        items = data.get('items', [])
        if not items:
            return jsonify({'msg': 'Cart is empty'}), 400
        
        payment_ref = f"REF_{uuid.uuid4().hex[:10].upper()}"
        
        order = Order(
            user_id=user_id,
            total=data['total'],
            status='pending',
            customer_name=data['customer_name'],
            customer_phone=data['customer_phone'],
            customer_address=data['customer_address'],
            delivery_state=data.get('delivery_state', ''),
            delivery_fee=data.get('delivery_fee', 0),
            payment_reference=payment_ref
        )
        db.session.add(order)
        db.session.flush()
        
        for item in items:
            product = Product.query.get(item['product_id'])
            if not product:
                db.session.rollback()
                return jsonify({'msg': f'Product {item["product_id"]} not found'}), 404
            if product.stock < item['quantity']:
                db.session.rollback()
                return jsonify({'msg': f'Not enough stock for {product.name}'}), 400
                
            order_item = OrderItem(
                order_id=order.id,
                product_id=item['product_id'],
                quantity=item['quantity'],
                price=item['price']
            )
            db.session.add(order_item)
            product.stock -= item['quantity']
        
        db.session.commit()

        # Send confirmation email - INDENTED 8 SPACES
        try:
            customer = User.query.get(user_id)
            send_order_confirmation(current_app._get_current_object(), order, customer.email)
        except Exception as e:
            print(f"Email failed: {e}")
        
        return jsonify({
            'msg': 'Order created',
            'order_id': order.id,
            'payment_reference': payment_ref
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(traceback.format_exc())
        return jsonify({'msg': f'Server error: {str(e)}'}), 500

# 4. GET USER ORDERS
@orders_bp.route('/my-orders', methods=['GET'])
@jwt_required()
def get_my_orders():
    user_id = int(get_jwt_identity())
    orders = Order.query.filter_by(user_id=user_id).order_by(Order.created_at.desc()).all()
    return jsonify([o.to_dict() for o in orders])

# 5. ADMIN: GET ALL ORDERS
@orders_bp.route('/admin/all', methods=['GET'])
@jwt_required()
def get_all_orders():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user or user.role != 'admin':
        return jsonify({'msg': 'Admin access required'}), 403

    orders = Order.query.order_by(Order.created_at.desc()).all()
    return jsonify([o.to_dict() for o in orders]), 200

# 6. ADMIN: UPDATE ORDER STATUS
@orders_bp.route('/<int:order_id>/status', methods=['PUT'])
@jwt_required()
def update_order_status(order_id):
    admin_user_id = get_jwt_identity()
    admin_user = User.query.get(admin_user_id)

    if not admin_user or admin_user.role != 'admin':
        return jsonify({'msg': 'Admin access required'}), 403

    order = Order.query.get(order_id)
    if not order:
        return jsonify({'msg': 'Order not found'}), 404

    data = request.get_json()
    new_status = data.get('status')

    if new_status not in ['pending', 'paid', 'shipped', 'delivered', 'cancelled']:
        return jsonify({'msg': 'Invalid status'}), 400

    old_status = order.status
    order.status = new_status
    db.session.commit()

    # Send email to CUSTOMER
    try:
        customer = User.query.get(order.user_id)
        send_order_confirmation(current_app._get_current_object(), order, customer.email)
    except Exception as e:
        print(f"Email failed: {e}")

    if old_status != 'delivered' and order.status == 'delivered':
        print(f"EMAIL TO {customer.email}: Order #{order.id} delivered!")

    return jsonify({'msg': 'Status updated', 'order': order.to_dict()}), 200
