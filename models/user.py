from pymongo import MongoClient
from bson import ObjectId  # Make sure ObjectId is imported correctly
import os

# Connect to MongoDB
client = MongoClient(os.getenv('MONGO_URI', 'mongodb+srv://itsenock254:<2467Havoc.>@cluster0.no4qaur.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0'))

db = client['user_database']


class User:
    """
    User model to encapsulate all user-related operations.
    """

    def __init__(self, fullname, email, phone_number, password):
        self.fullname = fullname
        self.email = email
        self.phone_number = phone_number
        self.password = password  # This should already be hashed

    def save(self):
        """
        Save the user to the database.
        """
        user_data = {
            'fullname': self.fullname,
            'email': self.email,
            'phone_number': self.phone_number,
            'password': self.password
        }
        try:
            result = db.users.insert_one(user_data)
            return result
        except Exception as e:
            print(f"Error saving user to database: {e}")
            return None

    def update_field(self, field, value):
        """
        Update a specific field for the user in the database.
        """
        try:
            result = db.users.update_one({'email': self.email}, {'$set': {field: value}})
            if result.modified_count > 0:
                setattr(self, field, value)  # Update the instance variable
            return result
        except Exception as e:
            print(f"Error updating user field '{field}': {e}")
            return None

    def update_fullname(self, new_fullname):
        """
        Updates the user's full name in the database.
        """
        return self.update_field('fullname', new_fullname)

    def update_phone_number(self, new_phone_number):
        """
        Updates the user's phone number in the database.
        """
        return self.update_field('phone_number', new_phone_number)

    def update_password(self, new_password):
        """
        Updates the user's password in the database.
        """
        return self.update_field('password', new_password)

    @staticmethod
    def find_by_email_or_fullname(identifier):
        """
        Find a user by email or fullname.
        """
        try:
            user = db.users.find_one({
                '$or': [
                    {'email': identifier},
                    {'fullname': identifier}
                ]
            })
            return user
        except Exception as e:
            print(f"Error finding user by email or fullname: {e}")
            return None

    @staticmethod
    def find_by_id(user_id):
        """
        Find a user by their ID.
        """
        try:
            user = db.users.find_one({'_id': ObjectId(user_id)})
            return user
        except Exception as e:
            print(f"Error finding user by ID: {e}")
            return None

    @staticmethod
    def delete_user(email):
        """
        Delete a user from the database by email.
        """
        try:
            result = db.users.delete_one({'email': email})
            return result.deleted_count > 0
        except Exception as e:
            print(f"Error deleting user with email {email}: {e}")
            return False
