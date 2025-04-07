from flask import Blueprint, request, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
import jwt
import os

admin_bp = Blueprint('admin_bp', __name__)

# Database connection
client = MongoClient(os.getenv('MONGO_URI', 'mongodb+srv://itsenock254:<2467Havoc.>@cluster0.no4qaur.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0'))
db = client['user_database']

# Make sure this UPLOAD_FOLDER constant is the same used in your items blueprint.
UPLOAD_FOLDER = 'uploads'

def decode_token(token):
    try:
        token = token.split(" ")[1]  # Remove the "Bearer " prefix
        payload = jwt.decode(token, os.getenv('JWT_SECRET_KEY', 'your_jwt_secret_key'), algorithms=['HS256'])
        return payload['user_id']
    except Exception as e:
        print(f"Token decoding error: {e}")
        return None

def serialize_document(doc):
    """Convert ObjectId fields in a document to strings."""
    if not doc:
        return None
    doc['_id'] = str(doc['_id'])
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            doc[key] = str(value)
    return doc

# ----------------------------
# NEW: Get all items endpoint
# This route returns bought and unbought (not sold) items.
@admin_bp.route('/items', methods=['GET'])
def get_all_items():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token missing!'}), 401

    user_id = decode_token(token)
    if not user_id:
        return jsonify({'error': 'Invalid token!'}), 401

    # Query: bought items (is_sold: true) and unbought (where is_sold is not true)
    bought_items = list(db.items.find({'is_sold': True}))
    unbought_items = list(db.items.find({'is_sold': {'$ne': True}}))
    
    # Serialize documents
    bought_items = [serialize_document(item) for item in bought_items]
    unbought_items = [serialize_document(item) for item in unbought_items]

    return jsonify({'bought_items': bought_items, 'unbought_items': unbought_items}), 200

# ----------------------------
# Existing routes (users, transactions, pending, approve, reject)

@admin_bp.route('/users', methods=['GET'])
def get_logged_in_users():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token missing!'}), 401

    user_id = decode_token(token)
    if not user_id:
        return jsonify({'error': 'Invalid token!'}), 401

    users = list(db.users.find({}))
    for user in users:
        user['_id'] = str(user['_id'])
        user.pop('password', None)  # Remove sensitive information
    return jsonify(users), 200

@admin_bp.route('/transactions', methods=['GET'])
def get_transactions():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token missing!'}), 401

    user_id = decode_token(token)
    if not user_id:
        return jsonify({'error': 'Invalid token!'}), 401

    # Sort transactions by paid_at descending (most recent first)
    transactions = list(db.orders.find({}).sort('paid_at', -1))
    serialized_transactions = []
    for transaction in transactions:
        tx = serialize_document(transaction)

        # Attach buyer details
        buyer_id = tx.get('buyer_id')
        if buyer_id:
            buyer = db.users.find_one({'_id': ObjectId(buyer_id)}, {'password': 0})
            if buyer:
                tx['buyer'] = {
                    'fullname': buyer.get('fullname', 'Unknown'),
                    'email': buyer.get('email', 'Unknown'),
                    'phone': buyer.get('phone', buyer.get('phone_number', 'Unknown'))
                }
            else:
                tx['buyer'] = {'fullname': 'Unknown', 'email': 'Unknown', 'phone': 'Unknown'}
        else:
            tx['buyer'] = {'fullname': 'Unknown', 'email': 'Unknown', 'phone': 'Unknown'}

        # Attach seller details
        seller_id = tx.get('seller_id')
        if seller_id:
            seller = db.users.find_one({'_id': ObjectId(seller_id)}, {'password': 0})
            if seller:
                tx['seller'] = {
                    'fullname': seller.get('fullname', 'Unknown'),
                    'email': seller.get('email', 'Unknown'),
                    'phone': seller.get('phone', seller.get('phone_number', 'Unknown'))
                }
            else:
                tx['seller'] = {'fullname': 'Unknown', 'email': 'Unknown', 'phone': 'Unknown'}
        else:
            tx['seller'] = {'fullname': 'Unknown', 'email': 'Unknown', 'phone': 'Unknown'}

        # Attach item details
        item_id = tx.get('item_id')
        if item_id:
            item = db.items.find_one({'_id': ObjectId(item_id)})
            tx['item'] = item.get('name', 'Unknown') if item else 'Unknown'
        else:
            tx['item'] = 'Unknown'

        serialized_transactions.append(tx)

    return jsonify(serialized_transactions), 200


@admin_bp.route('/items/pending', methods=['GET'])
def get_pending_items():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token missing!'}), 401
    user_id = decode_token(token)
    if not user_id:
        return jsonify({'error': 'Invalid token!'}), 401

    items = list(db.items.find({'status': 'pending'}))
    serialized_items = [serialize_document(item) for item in items]
    return jsonify(serialized_items), 200

@admin_bp.route('/items/approve/<item_id>', methods=['POST'])
def approve_item(item_id):
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token missing!'}), 401
    user_id = decode_token(token)
    if not user_id:
        return jsonify({'error': 'Invalid token!'}), 401

    result = db.items.update_one({'_id': ObjectId(item_id)}, {'$set': {'status': 'approved'}})
    if result.modified_count == 0:
        return jsonify({'error': 'Failed to approve item.'}), 400

    return jsonify({'message': 'Item approved successfully.'}), 200

@admin_bp.route('/items/reject/<item_id>', methods=['POST'])
def reject_item(item_id):
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token missing!'}), 401
    user_id = decode_token(token)
    if not user_id:
        return jsonify({'error': 'Invalid token!'}), 401

    # Reject route: remove the item along with associated images
    item = db.items.find_one({'_id': ObjectId(item_id)})
    if not item:
        return jsonify({'error': 'Item not found!'}), 404

    if 'images' in item:
        for image_path in item['images']:
            filepath = os.path.join(UPLOAD_FOLDER, os.path.basename(image_path))
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except Exception as e:
                print(f"Error removing image {filepath}: {e}")

    result = db.items.delete_one({'_id': ObjectId(item_id)})
    if result.deleted_count == 0:
        return jsonify({'error': 'Failed to remove item.'}), 400

    return jsonify({'message': 'Item removed successfully.'}), 200

# New DELETE endpoint for admin to remove any item (bought or unbought)
@admin_bp.route('/item/<item_id>', methods=['DELETE'])
def remove_item(item_id):
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token missing!'}), 401

    user_id = decode_token(token)
    if not user_id:
        return jsonify({'error': 'Invalid token!'}), 401

    item = db.items.find_one({'_id': ObjectId(item_id)})
    if not item:
        return jsonify({'error': 'Item not found!'}), 404

    # Remove associated images from the uploads folder
    if 'images' in item:
        for image_path in item['images']:
            filepath = os.path.join(UPLOAD_FOLDER, os.path.basename(image_path))
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except Exception as e:
                print(f"Error removing image {filepath}: {e}")

    result = db.items.delete_one({'_id': ObjectId(item_id)})
    if result.deleted_count == 0:
        return jsonify({'error': 'Failed to remove item.'}), 400

    return jsonify({'message': 'Item removed successfully.'}), 200
