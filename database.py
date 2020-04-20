"""Robowillow database operations in pymongo."""
import pymongo

host = "mongodb://localhost:27017/"
my_client = pymongo.MongoClient(host)
main_db = my_client['safety']
users = main_db['users']
settings = main_db['settings']    # No settings yet, keeping this in case I need it.



def add_user(user_id):
    """Add a new user to the database."""
    init_dict = {"slack_id": user_id}
    users.insert_one(init_dict)
