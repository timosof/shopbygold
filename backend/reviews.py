from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Review, Product, User
from datetime import datetime

reviews_bp = Blueprint('reviews', __name__, url_prefix='/api/reviews')

@reviews_bp.route('/', methods=['POST'])
@jwt_required()
def create_review():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    # Check if user already reviewed this product
    existing = Review.query.filter_by(user_id=user_id, product_id=data['product_id']).first()
    if existing:
        return jsonify({'msg': 'You already reviewed this product'}), 400
    
    # Check if product exists
    product = Product.query.get(data['product_id'])
    if not product:
        return jsonify({'msg': 'Product not found'}), 404
    
    review = Review(
        user_id=user_id,
        product_id=data['product_id'],
        rating=data['rating'],
        comment=data['comment']
    )
    db.session.add(review)
    db.session.commit()
    
    return jsonify({'msg': 'Review added', 'review': review.to_dict()}), 201

@reviews_bp.route('/<int:product_id>', methods=['GET'])
def get_product_reviews(product_id):
    reviews = Review.query.filter_by(product_id=product_id).order_by(Review.created_at.desc()).all()
    return jsonify([r.to_dict() for r in reviews]), 200