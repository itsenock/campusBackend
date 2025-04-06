
from flask import Blueprint, request, jsonify
from bson.objectid import ObjectId
from pymongo import MongoClient
import jwt
import os
from datetime import datetime


cart_bp = Blueprint('cart_bp', __name__)

client = MongoClient(os.getenv('mongodb://itsenock254:2467havoc@cluster0-shard-00-00.dadth.mongodb.net:27017,user_database?ssl=true&replicaSet=atlas-tvdsu5-shard-0&authSource=admin&retryWrites=true&w=majority'))
db = client['user_database']

def decode_token(token):
    try:
        token = token.split(" ")[1]  # Remove "Bearer " prefix
        payload = jwt.decode(
            token,
            os.getenv('JWT_SECRET_KEY', 'your_jwt_secret_key'),
            algorithms=['HS256']
        )
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.DecodeError:
        return None
    except Exception as e:
        print(f"Error decoding token: {e}")
        return None
@cart_bp.route('/user/cart', methods=['GET'])
def get_user_cart():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is missing!'}), 401

    user_id = decode_token(token)
    if not user_id:
        return jsonify({'error': 'Invalid token!'}), 401

    cart_items = list(db.cart.find({'user_id': ObjectId(user_id)}))

    for item in cart_items:
        product = db.items.find_one({'_id': ObjectId(item['product_id'])})
        if product:
            item['available'] = product.get('available', True) 
            item['price'] = product['price']
            item['name'] = product['name']
            item['images'] = product['images']
        else:
            item['available'] = False

        item['_id'] = str(item['_id'])
        item['user_id'] = str(item['user_id'])
        item['product_id'] = str(item['product_id'])

    return jsonify(cart_items), 200

    for item in cart_items:
        product = db.items.find_one({'_id': ObjectId(item['product_id'])})
        if product:

            item['available'] = product.get('available', True) 
            item['price'] = product['price']
            item['name'] = product['name']
            item['images'] = product['images']
        else:
            item['available'] = False

        item['_id'] = str(item['_id'])
        item['user_id'] = str(item['user_id'])
        item['product_id'] = str(item['product_id'])

    return jsonify(cart_items), 200

@cart_bp.route('/user/cart', methods=['POST'])
def add_to_cart():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is missing!'}), 401

    user_id = decode_token(token)
    if not user_id:
        return jsonify({'error': 'Invalid token!'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    existing_item = db.cart.find_one({
        'user_id': ObjectId(user_id),
        'product_id': ObjectId(data['product_id'])
    })

    if existing_item:
        return jsonify({'error': 'Item already exists in cart'}), 400

    cart_item = {
        'user_id': ObjectId(user_id),
        'product_id': ObjectId(data['product_id']),
        'name': data['name'],
        'price': data['price'],
        'quantity': data['quantity'],
        'images': data['images']
    }

    result = db.cart.insert_one(cart_item)
    cart_item['_id'] = str(result.inserted_id)
    cart_item['user_id'] = str(cart_item['user_id'])
    cart_item['product_id'] = str(cart_item['product_id'])

    return jsonify(cart_item), 201

@cart_bp.route('/user/cart/<item_id>', methods=['PUT'])
def update_cart_item(item_id):
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is missing!'}), 401

    user_id = decode_token(token)
    if not user_id:
        return jsonify({'error': 'Invalid token!'}), 401

    data = request.get_json()
    new_quantity = data.get('quantity')
    if not new_quantity or new_quantity <= 0:
        return jsonify({'error': 'Invalid quantity provided.'}), 400

    result = db.cart.update_one(
        {'_id': ObjectId(item_id), 'user_id': ObjectId(user_id)},
        {'$set': {'quantity': new_quantity}}
    )
    if result.matched_count == 0:
        return jsonify({'error': 'Cart item not found.'}), 404

    return jsonify({'message': 'Cart item updated successfully.'}), 200

@cart_bp.route('/user/cart/<item_id>', methods=['DELETE'])
def remove_from_cart(item_id):
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is missing!'}), 401

    user_id = decode_token(token)
    if not user_id:
        return jsonify({'error': 'Invalid token!'}), 401

    result = db.cart.delete_one({'_id': ObjectId(item_id), 'user_id': ObjectId(user_id)})
    if result.deleted_count == 0:
        return jsonify({'error': 'Cart item not found.'}), 404

    return jsonify({'message': 'Item removed from cart successfully.'}), 200

@cart_bp.route('/user/cart', methods=['DELETE'])
def clear_cart():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is missing!'}), 401

    user_id = decode_token(token)
    if not user_id:
        return jsonify({'error': 'Invalid token!'}), 401

    db.cart.delete_many({'user_id': ObjectId(user_id)})

    return jsonify({'message': 'Cart cleared successfully.'}), 200

@cart_bp.route('/user/wishlist', methods=['GET'])
def get_user_wishlist():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is missing!'}), 401

    user_id = decode_token(token)
    if not user_id:
        return jsonify({'error': 'Invalid token!'}), 401

    wishlist_items = list(db.wishlist.find({'user_id': ObjectId(user_id)}))
    for item in wishlist_items:
        item['_id'] = str(item['_id'])
        item['user_id'] = str(item['user_id'])
        item['product_id'] = str(item['product_id'])
    return jsonify(wishlist_items), 200

@cart_bp.route('/user/wishlist', methods=['POST'])
def add_to_wishlist():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is missing!'}), 401

    user_id = decode_token(token)
    if not user_id:
        return jsonify({'error': 'Invalid token!'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    existing_item = db.wishlist.find_one({
        'user_id': ObjectId(user_id),
        'product_id': ObjectId(data['product_id'])
    })

    if existing_item:
        return jsonify({'error': 'Item already exists in wishlist'}), 400

    wishlist_item = {
        'user_id': ObjectId(user_id),
        'product_id': ObjectId(data['product_id']),
        'name': data['name'],
        'price': data['price'],
        'images': data['images']
    }

    result = db.wishlist.insert_one(wishlist_item)
    wishlist_item['_id'] = str(result.inserted_id)
    wishlist_item['user_id'] = str(wishlist_item['user_id'])
    wishlist_item['product_id'] = str(wishlist_item['product_id'])

    return jsonify(wishlist_item), 201

@cart_bp.route('/user/wishlist/<item_id>', methods=['DELETE'])
def remove_from_wishlist(item_id):
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is missing!'}), 401

    user_id = decode_token(token)
    if not user_id:
        return jsonify({'error': 'Invalid token!'}), 401

    result = db.wishlist.delete_one({'_id': ObjectId(item_id), 'user_id': ObjectId(user_id)})
    if result.deleted_count == 0:
        return jsonify({'error': 'Wishlist item not found.'}), 404

    return jsonify({'message': 'Item removed from wishlist successfully.'}), 200

@cart_bp.route('/user/order', methods=['POST'])
def save_order():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is missing!'}), 401

    user_id = decode_token(token)
    if not user_id:
        return jsonify({'error': 'Invalid token!'}), 401

    data = request.get_json()
    if not data or 'items' not in data or 'totalAmount' not in data or 'paymentReference' not in data:
        return jsonify({'error': 'Incomplete order data!'}), 400

    # Prepare the order document
    order = {
        'user_id': ObjectId(user_id),
        'items': data['items'],
        'totalAmount': data['totalAmount'],
        'paymentReference': data['paymentReference'],
        'status': 'completed',
        'created_at': datetime.utcnow()
    }

    # Save the order in the database
    result = db.orders.insert_one(order)
    order['_id'] = str(result.inserted_id)

    return jsonify({'message': 'Order saved successfully!', 'order': order}), 201
