import os
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Slider, User
import cloudinary.uploader

sliders_bp = Blueprint('sliders', __name__)

# Simple admin check - no import needed
def admin_required(fn):
    @jwt_required()
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or user.role != 'admin':
            return jsonify({'msg': 'Admin access required'}), 403
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper

def upload_to_cloudinary(file):
    try:
        result = cloudinary.uploader.upload(file, folder="shopbygold/sliders")
        return result['secure_url']
    except Exception as e:
        print(f"Cloudinary failed: {e}")
        return None

@sliders_bp.route('/api/sliders', methods=['GET'])
def get_sliders():
    sliders = Slider.query.filter_by(is_active=True).order_by(Slider.display_order.asc()).all()
    if not sliders:
        return jsonify([{
            'id': 0,
            'title': 'Welcome to ShopByGold',
            'subtitle': 'Let Get The Shopping Started!',
            'image_url': '',
            'link': ''
        }])
    return jsonify([s.to_dict() for s in sliders])

@sliders_bp.route('/api/admin/sliders', methods=['GET', 'POST'])
@admin_required
def manage_sliders():
    if request.method == 'GET':
        sliders = Slider.query.order_by(Slider.display_order.asc()).all()
        return jsonify([s.to_dict() for s in sliders])

    title = request.form.get('title', 'Welcome to ShopByGold')
    subtitle = request.form.get('subtitle', '')
    link = request.form.get('link', '')
    order = int(request.form.get('display_order', 0) or 0)
    file = request.files.get('image')

    if not file:
        return jsonify({'msg': 'Image required'}), 400
    
    image_url = upload_to_cloudinary(file)
    if not image_url:
        return jsonify({'msg': 'Image upload failed'}), 500

    slider = Slider(title=title, subtitle=subtitle, link=link, image_url=image_url, display_order=order)
    db.session.add(slider)
    db.session.commit()
    return jsonify(slider.to_dict()), 201

@sliders_bp.route('/api/admin/sliders/<int:id>', methods=['DELETE'])
@admin_required
def delete_slider(id):
    s = Slider.query.get_or_404(id)
    db.session.delete(s)
    db.session.commit()
    return jsonify({'msg': 'deleted'})