import os
import requests
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

paystack_bp = Blueprint('paystack_bp', __name__)

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")

@paystack_bp.route('/verify/<reference>', methods=['GET'])
@jwt_required()
def verify_paystack_payment(reference):
    if not PAYSTACK_SECRET_KEY:
        return jsonify({"verified": False, "msg": "PAYSTACK_SECRET_KEY not set on server"}), 500

    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    try:
        r = requests.get(
            f"https://api.paystack.co/transaction/verify/{reference}",
            headers=headers,
            timeout=15
        )
        data = r.json()

        print(f"Paystack verify {reference}: {data}")

        if data.get("status") is True and data.get("data", {}).get("status") == "success":
            # Payment is real and successful
            return jsonify({
                "verified": True,
                "amount": data["data"]["amount"] / 100, # in Naira
                "reference": data["data"]["reference"],
                "channel": data["data"].get("channel")
            }), 200
        else:
            return jsonify({
                "verified": False,
                "msg": data.get("message", "Verification failed"),
                "paystack_data": data
            }), 400

    except Exception as e:
        print(f"Paystack error: {e}")
        return jsonify({"verified": False, "error": str(e)}), 500