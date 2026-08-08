from models import db, User, Order, OrderItem, Cart, CartItem, Review, PasswordResetToken
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User
from functools import wraps

admin_bp = Blueprint('admin', __name__)

def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        current_user_id = int(get_jwt_identity())
        user = User.query.get(current_user_id)
        if not user or user.role != 'admin':
            return jsonify({"msg": "Admin only"}), 403
        return fn(*args, **kwargs)
    return wrapper

@admin_bp.route('/api/admin/users', methods=['GET'])
@admin_required
def get_all_users():
    users = User.query.order_by(User.id.desc()).all()
    result = []
    for u in users:
        result.append({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role,
            "is_admin": u.role == 'admin',
            "created_at": u.created_at.strftime("%Y-%m-%d") if u.created_at else ""
        })
    return jsonify(result), 200

@admin_bp.route('/api/admin/users/<int:user_id>/make-admin', methods=['PUT'])
@admin_required
def toggle_admin(user_id):
    data = request.get_json() or {}
    make_admin = data.get('is_admin', True)
    user = User.query.get(user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404
    current_user_id = int(get_jwt_identity())
    if user_id == current_user_id and not make_admin:
        return jsonify({"msg": "You can't remove yourself"}), 400
    user.role = 'admin' if make_admin else 'customer'
    db.session.commit()
    return jsonify({"msg": f"User {'promoted' if make_admin else 'demoted'}", "role": user.role}), 200

@admin_bp.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    try:
        current_user_id = int(get_jwt_identity())
        if user_id == current_user_id:
            return jsonify({"msg": "You can't delete yourself"}), 400
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({"msg": "User not found"}), 404

        # Delete everything linked to user first to avoid foreign key error
        from models import Order, OrderItem, Cart, CartItem, Review, PasswordResetToken, db

        # Delete user's orders and order items
        user_orders = Order.query.filter_by(user_id=user_id).all()
        for order in user_orders:
            OrderItem.query.filter_by(order_id=order.id).delete()
            db.session.delete(order)

        # Delete cart
        cart = Cart.query.filter_by(user_id=user_id).first()
        if cart:
            CartItem.query.filter_by(cart_id=cart.id).delete()
            db.session.delete(cart)

        # Delete reviews
        Review.query.filter_by(user_id=user_id).delete()
        
        # Delete reset tokens
        PasswordResetToken.query.filter_by(user_id=user_id).delete()

        # Finally delete user
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({"msg": "User deleted"}), 200

    except Exception as e:
        db.session.rollback()
        print(f"DELETE USER ERROR: {e}")
        return jsonify({"msg": f"Failed to delete: {str(e)}"}), 500
    
from models import Cart, CartItem, User
from datetime import datetime

@admin_bp.route('/api/admin/abandoned-carts', methods=['GET'])
@admin_bp.route('/abandoned-carts', methods=['GET'])
@jwt_required()
def get_abandoned_carts():
    try:
        from models import Cart, CartItem, User
        result = []
        carts = Cart.query.all()
        for cart in carts:
            items = CartItem.query.filter_by(cart_id=cart.id).all()
            if not items:
                continue
            cart_user = User.query.get(cart.user_id)
            email = cart_user.email if cart_user else f"User {cart.user_id}"
            phone = getattr(cart_user, 'phone', '') if cart_user else ''
            item_list = []
            total = 0
            for it in items:
                if it.product:
                    item_list.append(f"{it.product.name} x{it.quantity}")
                    total += float(it.product.price) * it.quantity
            
            result.append({
                "email": email,
                "phone": phone,
                "items": item_list,
                "total": total,
                "abandoned_for": "In cart"
            })
        return jsonify(result)
    except Exception as e:
        print(f"ABANDONED CART ERROR: {e}")
        return jsonify({"msg": str(e)}), 500