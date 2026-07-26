from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Setting, ShippingFee

settings_bp = Blueprint('settings', __name__, url_prefix='/api/settings')

NIGERIA_STATES = [
    "Abia","Adamawa","Akwa Ibom","Anambra","Bauchi","Bayelsa","Benue","Borno",
    "Cross River","Delta","Ebonyi","Edo","Ekiti","Enugu","Gombe","Imo","Jigawa",
    "Kaduna","Kano","Katsina","Kebbi","Kogi","Kwara","Lagos","Nasarawa","Niger",
    "Ogun","Ondo","Osun","Oyo","Plateau","Rivers","Sokoto","Taraba","Yobe","Zamfara","FCT"
]

# Get all state fees
@settings_bp.route('/shipping-fees', methods=['GET'])
def get_all_shipping_fees():
    fees = {row.state: row.fee for row in ShippingFee.query.all()}
    # Fill missing states with default
    for st in NIGERIA_STATES:
        if st not in fees:
            fees[st] = 1500
    return jsonify(fees)

# Get fee for one state (for checkout)
@settings_bp.route('/shipping-fee/<state>', methods=['GET'])
def get_fee_by_state(state):
    row = ShippingFee.query.filter_by(state=state).first()
    if row:
        return jsonify({"state": state, "fee": row.fee})
    return jsonify({"state": state, "fee": 1500})

# Admin save all fees
@settings_bp.route('/shipping-fees', methods=['PUT'])
@jwt_required()
def update_shipping_fees():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or user.role!= 'admin':
        return jsonify({'msg': 'Admin only'}), 403

    data = request.get_json() # expects {"Lagos": 2000, "Ogun": 1500,...}
    for state, fee in data.items():
        if state not in NIGERIA_STATES:
            continue
        row = ShippingFee.query.filter_by(state=state).first()
        if not row:
            row = ShippingFee(state=state, fee=float(fee))
            db.session.add(row)
        else:
            row.fee = float(fee)
    db.session.commit()
    return jsonify({"msg": "Shipping fees updated"})

# Old endpoint - keep for backward compat (returns Lagos fee)
@settings_bp.route('/delivery-fee', methods=['GET'])
def get_delivery_fee():
    row = ShippingFee.query.filter_by(state='Lagos').first()
    fee = row.fee if row else 1500
    return jsonify({"delivery_fee": fee})