# blueprints/items.py
from flask import Blueprint, request, jsonify, send_from_directory
from bson.objectid import ObjectId
from pymongo import MongoClient
import os
from werkzeug.utils import secure_filename

item_bp = Blueprint('item_bp', __name__)

client = MongoClient(os.getenv('mongodb://itsenock254:2467havoc@cluster0-shard-00-00.dadth.mongodb.net:27017,user_database?ssl=true&replicaSet=atlas-tvdsu5-shard-0&authSource=admin&retryWrites=true&w=majority'))
db = client['user_database']

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def decode_token(token):
    import jwt
    try:
        token = token.split(" ")[1]
        payload = jwt.decode(token, os.getenv('JWT_SECRET_KEY', 'your_jwt_secret_key'), algorithms=['HS256'])
        return payload['user_id']
    except Exception as e:
        print(f"Error decoding token: {e}")
        return None

@item_bp.route('/uploads/<filename>', methods=['GET'])
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@item_bp.route('/user/item', methods=['POST'])
def save_item():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is missing!'}), 401
    user_id = decode_token(token)
    if not user_id:
        return jsonify({'error': 'Invalid or expired token!'}), 401
    data = request.form.to_dict()
    images = request.files.getlist('images')
    image_paths = []
    for image in images:
        filename = secure_filename(image.filename)
        image_path = os.path.join(UPLOAD_FOLDER, filename)
        image.save(image_path)
        image_paths.append(f'/uploads/{filename}')
    item = {
        'user_id': ObjectId(user_id),
        'name': data['name'],
        'category': data['category'],
        'condition': data['condition'],
        'description': data['description'],
        'price': data['price'],
        'warranty': data.get('warranty'),
        'images': image_paths,
        'quantity': data['quantity'],
        'status': 'pending'   # New items start as pending admin approval
    }
    result = db.items.insert_one(item)
    item['_id'] = str(result.inserted_id)
    item['user_id'] = str(item['user_id'])
    return jsonify(item), 201

@item_bp.route('/user/items', methods=['GET'])
def get_user_items():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is missing!'}), 401
    user_id = decode_token(token)
    if not user_id:
        return jsonify({'error': 'Invalid or expired token!'}), 401
    items = list(db.items.find({'user_id': ObjectId(user_id)}))
    for item in items:
        item['_id'] = str(item['_id'])
        item['user_id'] = str(item['user_id'])
    return jsonify(items), 200

@item_bp.route('/user/item/<item_id>', methods=['DELETE'])
def delete_user_item(item_id):
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is missing!'}), 401
    user_id = decode_token(token)
    if not user_id:
        return jsonify({'error': 'Invalid or expired token!'}), 401
    item = db.items.find_one({'_id': ObjectId(item_id), 'user_id': ObjectId(user_id)})
    if not item:
        return jsonify({'error': 'Item not found or not authorized to delete this item.'}), 404
    # Remove images from server
    for image in item['images']:
        image_path = image.replace('/uploads/', '')
        try:
            os.remove(os.path.join(UPLOAD_FOLDER, image_path))
        except Exception as e:
            print(f"Error removing image: {e}")
    db.items.delete_one({'_id': ObjectId(item_id), 'user_id': ObjectId(user_id)})
    return jsonify({'message': 'Item deleted successfully.'}), 200

@item_bp.route('/products', methods=['GET'])
def get_products():
    # Only return items that have been approved and are not marked as sold
    items = list(db.items.find({'status': 'approved', 'is_sold': {'$ne': True}}))
    for item in items:
        item['_id'] = str(item['_id'])
        item['user_id'] = str(item['user_id'])
    return jsonify(items), 200


@item_bp.route('/product/<item_id>', methods=['GET'])
def get_product(item_id):
    try:
        item = db.items.find_one({'_id': ObjectId(item_id)})
        if not item:
            return jsonify({'error': 'Product not found!'}), 404
        item['_id'] = str(item['_id'])
        item['user_id'] = str(item['user_id'])
        return jsonify(item), 200
    except Exception as e:
        return jsonify({'error': 'Invalid product ID.', 'message': str(e)}), 400

@item_bp.route('/verify-payment', methods=['POST'])
def verify_payment():
    data = request.get_json()
    reference = data.get('reference')

    if not reference:
        return jsonify({'error': 'No reference provided.'}), 400

    # Simulate verifying the payment with the payment gateway
    try:
        payment_successful = True  # Replace with actual verification result

        if payment_successful:
            # Retrieve the product/item ID from the payment metadata sent by the frontend
            item_id = data.get('item_id')  # Make sure this is passed from the frontend
            if not item_id:
                return jsonify({'error': 'No item ID provided.'}), 400

            # Mark the item as sold
            db.items.update_one({'_id': ObjectId(item_id)}, {'$set': {'is_sold': True}})
            return jsonify({'status': 'success', 'message': 'Payment verified and item marked as sold.'}), 200
        else:
            return jsonify({'error': 'Payment verification failed.'}), 400
    except Exception as e:
        print(f"Error verifying payment: {e}")
        return jsonify({'error': 'An error occurred during payment verification.'}), 500
