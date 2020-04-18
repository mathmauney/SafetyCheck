import os
import time
import logging
from flask import Flask
from slack import WebClient
from slackeventsapi import SlackEventAdapter
import ssl as ssl_lib
import certifi

# Initialize a Flask app to host the events adapter
app = Flask(__name__)
slack_events_adapter = SlackEventAdapter(os.environ['SLACK_SIGNING_SECRET'], "/slack/events", app)

# Initialize a Web API client
slack_web_client = WebClient(token=os.environ['SLACK_BOT_TOKEN'])

# Setup variables for checkins
state = 'out'
josue = 'U4VMN6N2J' # actual josue
#josue = 'U4UTZEGE7' # me as josue for testing
channel = 'C012313EJLC'
reminder = 15 # how long in min to remind
emergency = 45 # how long in min to @everyone

def start_checkin(channel: str):
    global state
    state = 'in'
    now = int(time.time())
    checkin_time = now + 60*reminder
    emergency_time = now + 60*emergency
    response = slack_web_client.chat_postMessage(
        channel=channel,
        text="Welcome Josue! I'll start checking in on you now, stay safe!"
    )
    response = slack_web_client.chat_scheduleMessage(
        channel=channel,
        text=f"Hey <@{josue}>, you still there?",
        post_at=str(checkin_time)
    )
    response = slack_web_client.chat_scheduleMessage(
        channel=channel,
        text="Hey <!everyone>, Josue didn't check-in, can someone call him?",
        post_at=str(emergency_time)
    )

def stop_checkin(channel: str):
    global state
    state = 'out'
    oldest = int(time.time()) + 60
    latest = oldest + 60*emergency
    response = slack_web_client.chat_scheduledMessages_list(
        channel=channel,
        latest=str(latest),
        oldest=str(oldest)
    )
    for message in response['scheduled_messages']:
        response = slack_web_client.chat_deleteScheduledMessage(
            channel=channel,
            scheduled_message_id=message['id']
        )
    response = slack_web_client.chat_postMessage(
        channel=channel,
        text="Bye Josue, let me know next time you are in lab!"
    )


def checkedin(channel: str):
    if state == 'out':
        return
    # Delete old messages
    oldest = int(time.time()) + 60
    latest = oldest + 60*emergency
    response = slack_web_client.chat_scheduledMessages_list(
        channel=channel,
        latest=str(latest),
        oldest=str(oldest)
    )
    for message in response['scheduled_messages']:
        response = slack_web_client.chat_deleteScheduledMessage(
            channel=channel,
            scheduled_message_id=message['id']
        )

    # Log sighting
    response = slack_web_client.chat_postMessage(
        channel=channel,
        text="Thanks for checking in Josue, see you in a bit."
    )


    # Make new ones
    now = int(time.time())
    checkin_time = now + 60*reminder
    emergency_time = now + 60*emergency
    response = slack_web_client.chat_scheduleMessage(
        channel=channel,
        text=f"Hey <@{josue}>, you still there?",
        post_at=str(checkin_time)
    )
    response = slack_web_client.chat_scheduleMessage(
        channel=channel,
        text="Hey <!here>, Josue didn't check-in, can someone call him?",
        post_at=str(emergency_time)
    )


# ============== Message Events ============= #
# When a user sends a DM, the event type will be 'message'.
# Here we'll link the message callback to the 'message' event.
@slack_events_adapter.on("message")
def message(payload):
    """Display the onboarding welcome message after receiving a message
    that contains "start".
    """
    event = payload.get("event", {})

    channel_id = event.get("channel")
    user_id = event.get("user")
    text = event.get("text")

    if user_id != josue:
        return

    if channel_id != channel:
        return

    if text and text.lower().startswith("here"):
        return start_checkin(channel_id)
    elif text and text.lower().startswith("leaving"):
        return stop_checkin(channel_id)
    else:
        return checkedin(channel_id)

# ============= Reaction Added Events ============= #
# When monitored user adds an emoji reaction to a message,
# the type of the event will be 'reaction_added'.
# Here we'll link the update_emoji callback to the 'reaction_added' event.
@slack_events_adapter.on("reaction_added")
def update_emoji(payload):
    event = payload.get("event", {})

    channel_id = event.get("item", {}).get("channel")
    user_id = event.get("user")

    if user_id != josue:
        return
    elif channel_id != channel:
        return
    else:
        return checkedin(channel_id)


if __name__ == "__main__":
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())
    ssl_context = ssl_lib.create_default_context(cafile=certifi.where())
    app.run(port=3000)

