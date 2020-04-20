"""Robowillow database operations in pymongo."""
import pymongo
from config import dbpassword

client = pymongo.MongoClient(f"mongodb+srv://dbUser:{dbpassword}@cluster0-yfftj.gcp.mongodb.net/test?retryWrites=true&w=majority")
main_db = client.test
# main_db = my_client['safety']
users = main_db['users']
settings = main_db['settings']    # No settings yet, keeping this in case I need it.


def add_user(user_id):
    """Add a new user to the database."""
    init_dict = {"slack_id": user_id}
    users.insert_one(init_dict)
