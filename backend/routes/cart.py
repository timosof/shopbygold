from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Cart, CartItem, Product

cart_bp = Blueprint("cart", __name__)


def get_or_create_cart(user_id):
    # FIX: JWT returns string, convert to int
    user_id = int(user_id)
    cart = Cart.query.filter_by(user_id=user_id).first()
    if not cart:
        cart = Cart(user_id=user_id)
        db.session.add(cart)
        db.session.commit()
    return cart


@cart_bp.route("/api/cart", methods=["GET"])
@jwt_required()
def get_cart():
    user_id = get_jwt_identity()
    cart = get_or_create_cart(user_id)
    return jsonify(cart.to_dict()), 200


@cart_bp.route("/api/cart/add", methods=["POST"])
@jwt_required()
def add_to_cart():
    user_id = get_jwt_identity()
    data = request.get_json()
    product_id = data.get("product_id")
    quantity = int(data.get("quantity", 1))

    product = Product.query.get(product_id)
    if not product:
        return jsonify({"msg": "Product not found"}), 404
    
    # BLOCK SOLD OUT
    if product.stock <= 0:
        return jsonify({"msg": f"{product.name} is sold out"}), 400

    cart = get_or_create_cart(user_id)
    cart_item = CartItem.query.filter_by(cart_id=cart.id, product_id=product_id).first()

    existing_qty = cart_item.quantity if cart_item else 0
    if existing_qty + quantity > product.stock:
        return jsonify({"msg": f"Only {product.stock} left in stock. You already have {existing_qty} in cart"}), 400
    
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(
            cart_id=cart.id,
            product_id=product_id,
            quantity=quantity,
            price=float(product.price),
        )
        db.session.add(cart_item)

    db.session.commit()
    # Refresh cart
    cart = Cart.query.get(cart.id)
    return jsonify({"msg": "Added to cart", "cart": cart.to_dict()}), 200



@cart_bp.route("/api/cart/update", methods=["PUT"])
@jwt_required()
def update_cart_item():
    user_id = get_jwt_identity()
    data = request.get_json()
    item_id = data.get("item_id")
    quantity = int(data.get("quantity", 0))

    cart = get_or_create_cart(user_id)
    cart_item = CartItem.query.filter_by(id=item_id, cart_id=cart.id).first()

    if not cart_item:
        return jsonify({"msg": "Item not found"}), 404

    if quantity <= 0:
        db.session.delete(cart_item)
    else:
        cart_item.quantity = quantity

    db.session.commit()
    cart = Cart.query.get(cart.id)
    return jsonify({"msg": "Cart updated", "cart": cart.to_dict()}), 200


@cart_bp.route("/api/cart/remove/<int:item_id>", methods=["DELETE"])
@jwt_required()
def remove_from_cart(item_id):
    user_id = get_jwt_identity()
    cart = get_or_create_cart(user_id)
    cart_item = CartItem.query.filter_by(id=item_id, cart_id=cart.id).first()

    if not cart_item:
        return jsonify({"msg": "Item not found"}), 404

    db.session.delete(cart_item)
    db.session.commit()
    cart = Cart.query.get(cart.id)
    return jsonify({"msg": "Item removed", "cart": cart.to_dict()}), 200


@cart_bp.route("/api/cart/clear", methods=["DELETE"])
@jwt_required()
def clear_cart():
    user_id = get_jwt_identity()
    cart = get_or_create_cart(user_id)
    CartItem.query.filter_by(cart_id=cart.id).delete()
    db.session.commit()
    return jsonify({"msg": "Cart cleared", "cart": cart.to_dict()}), 200
