"""Robowillow database operations in pymongo."""
import pymongo

host = "mongodb://localhost:27017/"
client = pymongo.MongoClient(host)
main_db = client.test
# main_db = my_client['safety']
users = main_db['users']
settings = main_db['settings']    # No settings yet, keeping this in case I need it.
tokens = main_db['tokens']


def add_user(user_id):
    """Add a new user to the database."""
    init_dict = {"slack_id": user_id}
    users.insert_one(init_dict)


def add_token(teamID, token):
    check = {"teamID": teamID}
    entry = tokens.find_one(check)
    if entry is None:
        init_dict = {"teamID": teamID,
                     "token": token}
        tokens.insert_one(init_dict)
    elif entry['token'] != token:
        update_dict = {'$set': {'token': token}}
        tokens.update_one(entry, update_dict)


def get_token(teamID):
    find_dict = {'teamID': teamID}
    entry = tokens.find_one(find_dict)
    if entry is not None:
        return entry['token']
    else:
        return None
