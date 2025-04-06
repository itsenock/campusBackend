# app.py

from flask import Flask, send_from_directory
from flask_cors import CORS
from pymongo import MongoClient
from routes.auth_routes import auth_bp
from routes.item_routes import item_bp
from routes.cart_routes import cart_bp
from routes.payment_routes import payment_bp
from routes.admin_routes import admin_bp  
from dotenv import load_dotenv
import os
from flask.json.provider import DefaultJSONProvider
from bson import ObjectId

# Custom JSON provider to handle ObjectId serialization
class CustomJSONProvider(DefaultJSONProvider):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return super().default(obj)
    
app = Flask(__name__)
app.json = CustomJSONProvider(app)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config.from_object('config.Config')
load_dotenv()

CORS(app)

client = MongoClient(app.config['MONGO_URI'])
db = client['user_database']

app.config['DB_CLIENT'] = client

app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(item_bp, url_prefix='/api')
app.register_blueprint(cart_bp, url_prefix='/api')
app.register_blueprint(payment_bp, url_prefix='/api') 
app.register_blueprint(admin_bp, url_prefix='/api/admin')

# Serve static files from the uploads directory
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
