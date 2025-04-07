from flask import Blueprint, request, jsonify
from pymongo import MongoClient
from bson import ObjectId  # Correctly import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import os
import random
import string
from threading import Thread
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from models.user import User

load_dotenv()

auth_bp = Blueprint('auth_bp', __name__)

# Initialize MongoDB
client = MongoClient(os.getenv('MONGO_URI','mongodb+srv://itsenock254:<2467Havoc.>@cluster0.no4qaur.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0'))
db = client['user_database']

# Email Configurations
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))

# JWT Secret Key
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your_jwt_secret_key')


def generate_token(user_id):
    """
    Generate JWT token with user_id.
    """
    token = jwt.encode({'user_id': str(user_id)}, JWT_SECRET_KEY, algorithm='HS256')
    return token


def decode_token(token):
    """
    Decode the JWT token to extract user_id.
    """
    try:
        if token.startswith("Bearer "):
            token = token.split(" ")[1]  # Remove "Bearer " prefix
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
        return payload['user_id']
    except Exception as e:
        print(f"Error decoding token: {e}")
        return None


def send_async_email(message):
    """
    Send email asynchronously.
    """
    def send_email():
        try:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                server.send_message(message)
            print("Email sent successfully")
        except Exception as e:
            print(f"Error sending email: {e}")
    Thread(target=send_email).start()


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user and save their details.
    """
    data = request.get_json()
    fullname = data.get('fullname')
    email = data.get('email')
    phone_number = data.get('phone_number')  # NOTE: Ensure the frontend passes "phone_number"
    password = data.get('password')
    confirm_password = data.get('confirmPassword')

    if not all([fullname, email, phone_number, password, confirm_password]):
        return jsonify({'error': 'All fields are required.'}), 400

    if password != confirm_password:
        return jsonify({'error': 'Passwords do not match.'}), 400

    if db.users.find_one({'$or': [{'email': email}, {'fullname': fullname}]}):
        return jsonify({'error': 'User with this email or full name already exists.'}), 400

    hashed_password = generate_password_hash(password)
    new_user = User(fullname, email, phone_number, hashed_password)
    result = new_user.save()
    if not result or not result.inserted_id:
        return jsonify({'error': 'Registration failed. Please try again.'}), 500

    token = generate_token(result.inserted_id)
    return jsonify({'message': 'Registration successful.', 'token': token}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Log in the user by verifying their credentials.
    """
    data = request.get_json()
    email_or_fullname = data.get('email')
    password = data.get('password')

    if not email_or_fullname or not password:
        return jsonify({'error': 'Email/fullname and password are required.'}), 400

    user = User.find_by_email_or_fullname(email_or_fullname)
    if user and check_password_hash(user['password'], password):
        token = generate_token(user['_id'])
        return jsonify({'message': 'Login successful.', 'token': token}), 200

    return jsonify({'error': 'Invalid credentials.'}), 401


@auth_bp.route('/me', methods=['GET'])
def get_logged_in_user():
    """
    Retrieve the currently logged-in user's details using their token.
    """
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is missing!'}), 401

    user_id = decode_token(token)
    if not user_id:
        return jsonify({'error': 'Invalid token!'}), 401

    try:
        user = User.find_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found!'}), 404

        # Exclude sensitive fields and convert _id to string
        user['_id'] = str(user['_id'])
        user.pop('password', None)
        return jsonify(user), 200
    except Exception as e:
        print(f"Error finding user by ID: {e}")
        return jsonify({'error': 'Internal server error.'}), 500


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """
    Reset the user's password and send them a temporary password via email.
    """
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({'error': 'Please provide an email.'}), 400

    user = db.users.find_one({'email': email})
    if not user:
        return jsonify({'error': 'User not found.'}), 404

    temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    hashed_password = generate_password_hash(temp_password)
    db.users.update_one({'_id': user['_id']}, {'$set': {'password': hashed_password}})

    message = EmailMessage()
    message['Subject'] = 'Password Reset'
    message['From'] = EMAIL_ADDRESS
    message['To'] = email
    message.set_content(f"""Hello {user['fullname']},

Your password has been reset. Here is your temporary password:

Temporary Password: {temp_password}

Please log in and change your password immediately.
""")

    send_async_email(message)
    return jsonify({'message': 'Password reset successful. Please check your email.'}), 200


@auth_bp.route('/update', methods=['PUT'])
def update_user_info():
    """
    Update the logged-in user's information.
    """
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token missing!'}), 401

    user_id = decode_token(token)
    if not user_id:
        return jsonify({'error': 'Invalid token!'}), 401

    data = request.get_json()
    update_fields = {key: value for key, value in data.items() if key in ['fullname', 'email', 'phone_number']}
    result = db.users.update_one({'_id': ObjectId(user_id)}, {'$set': update_fields})

    if result.modified_count == 0:
        return jsonify({'error': 'No changes were made.'}), 400

    updated_user = User.find_by_id(user_id)
    updated_user['_id'] = str(updated_user['_id'])
    updated_user.pop('password', None)
    return jsonify(updated_user), 200


@auth_bp.route('/delete-account', methods=['DELETE'])
def delete_account():
    """
    Delete the logged-in user's account.
    """
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token missing!'}), 401

    user_id = decode_token(token)
    if not user_id:
        return jsonify({'error': 'Invalid token!'}), 401

    result = db.users.delete_one({'_id': ObjectId(user_id)})
    if result.deleted_count == 0:
        return jsonify({'error': 'User not found or already deleted.'}), 404

    return jsonify({'message': 'User account deleted successfully.'}), 200


@auth_bp.route('/change-password', methods=['PUT'])
def change_password():
    """
    Allow a logged-in user to change their password.
    Expects: old_password, new_password, confirm_password in the request JSON.
    """
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token missing!'}), 401

    user_id = decode_token(token)
    if not user_id:
        return jsonify({'error': 'Invalid token!'}), 401

    data = request.get_json()
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')

    if not all([old_password, new_password, confirm_password]):
        return jsonify({'error': 'Old password, new password, and confirm password are required.'}), 400

    if new_password != confirm_password:
        return jsonify({'error': 'New password and confirm password do not match.'}), 400

    user = User.find_by_id(user_id)
    if not user:
        return jsonify({'error': 'User not found.'}), 404

    if not check_password_hash(user['password'], old_password):
        return jsonify({'error': 'Old password is incorrect.'}), 401

    hashed_password = generate_password_hash(new_password)
    result = db.users.update_one({'_id': ObjectId(user_id)}, {'$set': {'password': hashed_password}})
    if result.modified_count == 0:
        return jsonify({'error': 'Password not updated. Try again.'}), 400

    return jsonify({'message': 'Password updated successfully.'}), 200
