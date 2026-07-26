from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Product, User, OrderItem
from werkzeug.utils import secure_filename
import os
import time
import cloudinary.uploader

products_bp = Blueprint("products", __name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def upload_to_cloudinary(file, folder="shopbygold/products"):
    """Upload to Cloudinary and return secure URL"""
    try:
        result = cloudinary.uploader.upload(file, folder=folder, resource_type="image")
        return result["secure_url"]
    except Exception as e:
        print(f"Cloudinary upload failed: {e}")
        return None


# GET all products - public
@products_bp.route("/", methods=["GET"])
def get_products():
    products = Product.query.filter_by(is_active=True).all()
    # products = Product.query.all()
    return jsonify([p.to_dict() for p in products])


# GET single product - public
@products_bp.route("/<int:product_id>", methods=["GET"])
def get_product(product_id):
    product = Product.query.get_or_404(product_id)
    return jsonify(product.to_dict())


# POST create product with file upload - admin only
@products_bp.route("/", methods=["POST"])
@jwt_required()
def create_product():
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))

    if user.role != "admin":
        return jsonify({"msg": "Admins only"}), 403

    image_url = ""
    if "image" in request.files:
        file = request.files["image"]
        if file and file.filename != "":
            if not allowed_file(file.filename):
                return (
                    jsonify(
                        {"msg": "Invalid file type. Use png, jpg, jpeg, gif, webp"}
                    ),
                    400,
                )

            try:
                # Upload to Cloudinary
                image_url = upload_to_cloudinary(file)
                if not image_url:
                    return jsonify({"msg": "Image upload failed"}), 500
            except Exception as e:
                return jsonify({"msg": f"Image upload failed: {str(e)}"}), 500

    try:
        product = Product(
            name=request.form.get("name"),
            description=request.form.get("description", ""),
            price=float(request.form.get("price")),
            image_url=image_url,
            stock=int(request.form.get("stock", 0)),
            category=request.form.get("category", "general"),
        )
        db.session.add(product)
        db.session.commit()
        return jsonify(product.to_dict()), 201
    except Exception as e:
        return jsonify({"msg": f"Database error: {str(e)}"}), 400


# PUT edit product - admin only
@products_bp.route("/<int:product_id>", methods=["PUT"])
@jwt_required()
def update_product(product_id):
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))

    if user.role != "admin":
        return jsonify({"msg": "Admins only"}), 403

    product = Product.query.get_or_404(product_id)

    if "image" in request.files:
        file = request.files["image"]
        if file and file.filename != "":
            if not allowed_file(file.filename):
                return jsonify({"msg": "Invalid file type"}), 400

            # Safely delete old image
            if product.image_url and product.image_url.startswith("/uploads/"):
                try:
                    old_filename = product.image_url.split("/")[-1]
                    old_path = os.path.join(
                        current_app.config["UPLOAD_FOLDER"], old_filename
                    )
                    if os.path.exists(old_path):
                        os.remove(old_path)
                except:
                    pass  # Ignore if delete fails

            try:
                # Upload new image to Cloudinary
                image_url = upload_to_cloudinary(file)
                if not image_url:
                    return jsonify({"msg": "Image upload failed"}), 500
                product.image_url = image_url
            except Exception as e:
                return jsonify({"msg": f"Image upload failed: {str(e)}"}), 500

    if request.form.get("name"):
        product.name = request.form.get("name")
    if request.form.get("price"):
        product.price = float(request.form.get("price"))
    if request.form.get("stock"):
        product.stock = int(request.form.get("stock"))
    if request.form.get("category"):
        product.category = request.form.get("category")
    if request.form.get("description"):
        product.description = request.form.get("description")

    db.session.commit()
    return jsonify(product.to_dict())


# DELETE product - admin only
@products_bp.route("/<int:product_id>", methods=["DELETE"])
@jwt_required()
def delete_product(product_id):
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))

    if user.role != "admin":
        return jsonify({"msg": "Admins only"}), 403

    product = Product.query.get_or_404(product_id)

    # Soft delete - just hide it, don't remove from DB
    product.is_active = False
    db.session.commit()

    return jsonify({"msg": "Product hidden from store. Order history preserved."})

    # Check if product is in any orders - prevents FK error
    orders_with_product = OrderItem.query.filter_by(product_id=product_id).first()

    if orders_with_product:
        return (
            jsonify(
                {
                    "msg": "Cannot delete: This product exists in customer orders. Edit and set stock to 0 instead."
                }
            ),
            400,
        )

    # Safely delete image file
    if product.image_url and product.image_url.startswith("/uploads/"):
        try:
            filename = product.image_url.split("/")[-1]
            filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
            if os.path.exists(filepath):
                os.remove(filepath)
        except:
            pass  # Ignore file delete errors

    db.session.delete(product)
    db.session.commit()
    return jsonify({"msg": "Product deleted successfully"})


# REACTIVATE product - admin only
@products_bp.route("/<int:product_id>/restore", methods=["PUT"])
@jwt_required()
def restore_product(product_id):
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))

    if user.role != "admin":
        return jsonify({"msg": "Admins only"}), 403

    product = Product.query.get_or_404(product_id)
    product.is_active = True
    db.session.commit()

    return jsonify({"msg": "Product restored to store"})


# GET all products including inactive - admin only
@products_bp.route("/admin/all", methods=["GET"])
@jwt_required()
def get_all_products_admin():
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))

    if user.role != "admin":
        return jsonify({"msg": "Admins only"}), 403

    products = Product.query.all()  # Get everything
    return jsonify([p.to_dict() for p in products])


# search products - public
@products_bp.route("/search", methods=["GET"])
def search_products():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([]), 200

    # Search DB by name, description, category - NO is_active filter
    results = Product.query.filter(
        (Product.name.ilike(f"%{q}%"))
        | (Product.description.ilike(f"%{q}%"))
        | (Product.category.ilike(f"%{q}%"))
    ).all()

    return jsonify([p.to_dict() for p in results]), 200
