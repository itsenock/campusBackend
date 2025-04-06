from flask import Blueprint, request, jsonify, current_app
from bson.objectid import ObjectId
import requests
from datetime import datetime
import os
from dotenv import load_dotenv
import jwt
import logging

payment_bp = Blueprint('payment_bp', __name__)
load_dotenv()

PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY')
logging.basicConfig(level=logging.INFO)

def decode_token(token):
    try:
        if not token or "Bearer " not in token:
            raise ValueError("Missing or invalid token format.")
        
        token = token.split(" ")[1]
        payload = jwt.decode(
            token,
            os.getenv('JWT_SECRET_KEY', 'your_jwt_secret_key'),
            algorithms=['HS256']
        )
        return payload.get('user_id')
    except jwt.ExpiredSignatureError:
        logging.error("JWT token has expired.")
        return None
    except Exception as e:
        logging.error(f"Token decoding error: {e}")
        return None

@payment_bp.route('/verify-payment', methods=['POST'])
def verify_payment():
    data = request.get_json()
    reference = data.get('reference')

    if not reference:
        return jsonify({'error': 'No reference provided.'}), 400

    headers = {
        'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}',
    }

    try:
        response = requests.get(f'https://api.paystack.co/transaction/verify/{reference}', headers=headers)
        response_data = response.json()

        if response_data.get('status') and response_data['data']['status'] == 'success':
            transaction_data = response_data['data']
            metadata = transaction_data.get('metadata', {})
            cart_items = metadata.get('cart_items', [])

            # Debugging logs
            print(f"Transaction Data: {transaction_data}")
            print(f"Metadata: {metadata}")
            print(f"Cart Items: {cart_items}")

            if not cart_items or len(cart_items) == 0:
                return jsonify({'error': 'Cart items missing or invalid metadata.'}), 400

            paid_at = transaction_data.get('paid_at', datetime.utcnow().isoformat())
            
            db = current_app.config['DB_CLIENT']['user_database']
            buyer_id = decode_token(request.headers.get('Authorization'))

            if not buyer_id:
                return jsonify({'error': 'Buyer not identified (invalid token).'}), 401

            orders = []
            for item in cart_items:
                product_id = item.get('product_id')
                if not product_id:
                    continue

                product = db.items.find_one({'_id': ObjectId(product_id)})
                if product:
                    seller_id = str(product.get('user_id'))
                    
                    orders.append({
                        'buyer_id': ObjectId(buyer_id),
                        'seller_id': ObjectId(seller_id),
                        'item_id': ObjectId(product_id),
                        'amount': transaction_data['amount'] / 100,
                        'currency': transaction_data['currency'],
                        'reference': transaction_data['reference'],
                        'status': 'success',
                        'paid_at': paid_at,
                        'created_at': datetime.utcnow()
                    })

            # Insert all orders into the database
            if orders:
                db.orders.insert_many(orders)
                print(f"Orders successfully inserted: {orders}")

            return jsonify({'status': 'success'}), 200

        # If payment verification fails
        return jsonify({'error': 'Payment verification failed.'}), 400

    except Exception as e:
        print(f"Error during payment verification: {e}")
        return jsonify({'error': 'An error occurred during verification.'}), 500
