import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your_flask_secret_key')
    MONGO_URI = os.environ.get('mongodb://itsenock254:2467havoc@cluster0-shard-00-00.dadth.mongodb.net:27017,user_database?ssl=true&replicaSet=atlas-tvdsu5-shard-0&authSource=admin&retryWrites=true&w=majority')  # MongoDB URI
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your_jwt_secret_key')
