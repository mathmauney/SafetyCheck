"""Slack app to perform safety checks and monitoring for people working alone."""
import os
import time
import logging
from flask import Flask, request
from slack import WebClient
from slack import errors
from slackeventsapi import SlackEventAdapter
import ssl as ssl_lib
import certifi
import database as db
import datetime
import pytz
import threading
from uuid import uuid4

client_id = os.environ["SLACK_CLIENT_ID"]
client_secret = os.environ["SLACK_CLIENT_SECRET"]
signing_secret = os.environ["SLACK_SIGNING_SECRET"]

state = str(uuid4())
oauth_scope = ", ".join(['channels:read', 'channels:history', 'chat:write', 'groups:write', 'im:history', 'im:write', 'mpim:write', "reactions:read", 'users:read', 'im:read'])

# Some default variables
default_alert_time = 60
default_reminder_time = 30

# Initialize a Flask app to host the events adapter
app = Flask(__name__)

# Initialize a Web API client
slack_web_client = WebClient(token=os.environ['SLACK_BOT_TOKEN'])


# Create a dictionary to represent a database to store our token
global_token = ""


# Route to kick off Oauth flow
@app.route("/begin_auth", methods=["GET"])
def pre_install():
    return f'<a href="https://slack.com/oauth/v2/authorize?scope={ oauth_scope }&client_id={ client_id }&state={state}"><img alt=""Add to Slack"" height="40" width="139" src="https://platform.slack-edge.com/img/add_to_slack.png" srcset="https://platform.slack-edge.com/img/add_to_slack.png 1x, https://platform.slack-edge.com/img/add_to_slack@2x.png 2x" /></a>'


# Route for Oauth flow to redirect to after user accepts scopes
@app.route("/finish_auth", methods=["GET", "POST"])
def post_install():
    # Retrieve the auth code and state from the request params
    auth_code = request.args["code"]
    received_state = request.args["state"]

    # Token is not required to call the oauth.v2.access method
    client = WebClient()

    # verify state received in params matches state we originally sent in auth request
    if received_state == state:
        # Exchange the authorization code for an access token with Slack
        response = client.oauth_v2_access(
          client_id=client_id,
          client_secret=client_secret,
          code=auth_code)
    else:
        return "Invalid State"

    # Save the bot token and teamID to a database
    # In our example, we are saving it to dictionary to represent a DB
    teamID = response["team"]["id"]
    db.add_token(teamID, response["access_token"])
    # Also save the bot token in a global variable so we don't have to
    # do a database lookup on each WebClient call
    global global_token
    global_token = response["access_token"]

    # See if "the-welcome-channel" exists. Create it if it doesn't.
    channel_exists()

    # Don't forget to let the user know that auth has succeeded!
    return "Auth complete!"


# verifies if "the-welcome-channel" already exists
def channel_exists():
    # grab a list of all the channels in a workspace
    clist = slack_web_client.conversations_list()
    exists = False
    for k in clist["channels"]:
        # look for the channel in the list of existing channels
        if k["name"] == "safetycheck-channel":
            exists = True
            break
    if exists is False:
        # create the channel since it doesn't exist
        create_channel()


def create_channel():
    slack_web_client.conversations_create(name="safetycheck-channel")


slack_events_adapter = SlackEventAdapter(os.environ['SLACK_SIGNING_SECRET'], "/slack/events", app)


# ============== Slack Events ============= #
# Message event
@slack_events_adapter.on("message")
def message(payload):
    """Process a message event."""
    print("Got a message event")
    event = payload.get("event", {})

    channel_id = event.get("channel")
    user_id = event.get("user")
    text = event.get("text")
    ts = event.get("ts")

    user = User(user_id)

    if float(ts) < user.last_update:
        return
    else:
        user.last_update = float(ts)

    if text and text.lower().startswith("start"):
        x = threading.Thread(target=user.start_checkins, args=(channel_id,), daemon=True)
        x.start()
        # user.start_checkins(channel_id)
    elif text and text.lower().startswith("stop"):
        x = threading.Thread(target=user.stop_checkins, daemon=True)
        x.start()
        # user.stop_checkins()
    elif text and text.lower().startswith("clear"):
        oldest = int(time.time()) + 60
        latest = oldest + 60*60*12
        response = slack_web_client.chat_scheduledMessages_list(
            channel=channel_id,
            latest=str(latest),
            oldest=str(oldest)
            )
        for message in response['scheduled_messages']:
            response = slack_web_client.chat_deleteScheduledMessage(
                channel=channel_id,
                scheduled_message_id=message['id']
            )
    elif text and text.lower().startswith("set alert "):
        num = text.split(" ")[2]
        user.alert_time = int(num)
    elif text and text.lower().startswith("set reminder "):
        num = text.split(" ")[2]
        user.reminder_time = int(num)
    else:
        user.checkin()

# Reaction Added Event#
@slack_events_adapter.on("reaction_added")
def update_emoji(payload):
    """Process an emoji update event."""
    print("Got an emoji added event")
    event = payload.get("event", {})
    user_id = event.get("user")
    ts = event.get("event_ts")

    user = User(user_id)

    if float(ts) < user.last_update:
        return
    else:
        user.last_update = float(ts)

    user.checkin()


# ============= Classes ============= #
class User:
    """Defines a user class that will interface with the database backend."""

    def __init__(self, user_id):
        """Initialize the user and make sure there is an entry in the database."""
        self.id = user_id
        self.find_dict = {'slack_id': user_id}
        user = db.users.find_one(self.find_dict)
        if user is None:
            db.add_user(self.id)

    # ===== Define database interaction functions =====
    def _get(self, property_name):
        """Get a value from the database for this user."""
        return_dict = {'_id': 0, property_name: 1}
        db_result = db.users.find_one(self.find_dict, return_dict)
        return db_result.get(property_name, None)

    def _set(self, property_name, value):
        """Set a value in the database for this user."""
        update_dict = {'$set': {property_name: value}}
        db.users.update_one(self.find_dict, update_dict)

    # ===== Define class properties to pull from database =====
    @property
    def tz(self):
        """Get the users time zone."""
        tz = self._get('tz')
        if tz is not None:
            return pytz.timezone(tz)
        else:
            response = slack_web_client.users_info(user=self.id)
            if response['ok']:
                new_tz = response['user']['tz']
                self._set('tz', new_tz)
                return pytz.timezone(new_tz)
            else:
                raise ValueError('Unable to get user time zone.')

    @tz.setter
    def tz(self, new_tz):
        self._set('tz', new_tz)

    @property
    def channel(self):
        """Get the channel the user is using for checkins."""
        return self._get('channel')

    @channel.setter
    def channel(self, new_channel):
        self._set('channel', new_channel)

    @property
    def alert_time(self):
        """Get the time after which an alert should be posted."""
        alert_time = self._get('alert_time')
        if alert_time is not None:
            return alert_time
        else:
            return default_alert_time

    @alert_time.setter
    def alert_time(self, new_alert_time):
        self._set('alert_time', new_alert_time)

    @property
    def reminder_time(self):
        """Get the time after which the user should be reminded to check in."""
        reminder_time = self._get('reminder_time')
        if reminder_time is not None:
            return reminder_time
        else:
            return default_reminder_time

    @reminder_time.setter
    def reminder_time(self, new_reminder_time):
        self._set('reminder_time', new_reminder_time)

    @property
    def pms(self):
        """Get the channel id for private messaging the user."""
        pms = self._get('pms')
        if pms is not None:
            return pms
        else:
            response = slack_web_client.conversations_open(users=[self.id])
            if response['ok']:
                pms = response['channel']['id']
                self._set('pms', pms)
                return pms

    @property
    def alert_message(self):
        """Get the message id of a scheduled alert message."""
        return self._get('alert_message')

    @alert_message.setter
    def alert_message(self, message_id):
        self._set('alert_message', message_id)

    @property
    def reminder_message(self):
        """Get the message id of a scheduled reminder message."""
        return self._get('reminder_message')

    @reminder_message.setter
    def reminder_message(self, message_id):
        self._set('reminder_message', message_id)

    @property
    def status_message(self):
        """Get the message id of the users status message."""
        return self._get('status_message')

    @status_message.setter
    def status_message(self, message_id):
        self._set('status_message', message_id)

    @property
    def name(self):
        """Query slack for the users name."""
        response = slack_web_client.users_info(user=self.id)
        if response['ok']:
            return response['user']['name']
        else:
            raise ValueError('Unable to get user name.')

    @property
    def last_update(self):
        """Last message/emoji from user to prevent duplications."""
        out = self._get('last_update')
        if out is None:
            return 0
        else:
            return out

    @last_update.setter
    def last_update(self, new_time):
        self._set('last_update', new_time)

    # ===== Define checkin functions =====
    def start_checkins(self, channel_id):
        """Start checkins for the user in a given channel."""
        self.channel = channel_id
        response = slack_web_client.chat_postMessage(
            channel=channel_id,
            text=f"Welcome {self.name}! I'll start checking in on you now, stay safe!"
        )
        self.status_message = response['ts']
        self.checkin()

    def checkin(self):
        """Update that a user has been seen."""
        if self.channel is None:
            return
        self.delete_scheduled()
        now = int(time.time())
        reminder_time = now + 60*self.reminder_time
        alert_time = now + 60*self.alert_time
        response = slack_web_client.chat_scheduleMessage(
            channel=str(self.pms),
            text=f"Hey, you still there?",
            post_at=str(reminder_time)
        )
        self.reminder_message = response['scheduled_message_id']
        response = slack_web_client.chat_scheduleMessage(
            channel=str(self.channel),
            text=f"Hey <!channel>, {self.name} didn't check-in, can someone call him?",
            post_at=str(alert_time)
        )
        self.alert_message = response['scheduled_message_id']
        checkin_time = datetime.datetime.now(self.tz).strftime('%I:%M %p')
        slack_web_client.chat_update(
            channel=str(self.channel),
            ts=str(self.status_message),
            text=f"Welcome {self.name}! I'll start checking in on you now, stay safe! Last checked in at: {checkin_time}"
        )

    def delete_scheduled(self):
        """Delete all the scheduled checkin messages for this user."""
        if self.reminder_message is not None:
            try:
                slack_web_client.chat_deleteScheduledMessage(
                    channel=str(self.pms),
                    scheduled_message_id=str(self.reminder_message)
                )
            except errors.SlackApiError:
                print("Could not delete reminder.")
            self.reminder_messgae = None
        if self.alert_message is not None:
            try:
                slack_web_client.chat_deleteScheduledMessage(
                    channel=str(self.channel),
                    scheduled_message_id=str(self.alert_message)
                )
            except errors.SlackApiError:
                print("Could not delete alert.")
            self.alert_message = None

    def stop_checkins(self):
        """End the session for a user."""
        self.delete_scheduled()
        checkin_time = datetime.datetime.now(self.tz).strftime('%I:%M %p')
        slack_web_client.chat_update(
            channel=str(self.channel),
            ts=str(self.status_message),
            text=f"{self.name.title()} checked out at: {checkin_time}"
        )
        self.channel = None
        self.tz = None
        self.status_message = None


if __name__ == "__main__":
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())
    ssl_context = ssl_lib.create_default_context(cafile=certifi.where())
    app.run(port=3000)
