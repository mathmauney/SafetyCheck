# SafetyCheck -- ARCHIVED
<a href="https://slack.amauney.com:444/begin_auth"><img alt="Add to Slack" height="40" width="139" src="https://platform.slack-edge.com/img/add_to_slack.png" srcset="https://platform.slack-edge.com/img/add_to_slack.png 1x, https://platform.slack-edge.com/img/add_to_slack@2x.png 2x"></a>

## Installing SafetyCheck
1. Add SafetyCheck to your workspace using the button above.
2. The bot will make a channel, add youself and any co-workers who should be notified to this channel.

## Using SafetyCheck
1. Start a check-in session by saying ```start``` in the channel the bot is installed in.
2. The bot will generate a status message. Any interactions with the bot will now register as a check-in and this message will be updated.
3. After 30 minutes the bot will send a private message reminding you to check-in. Respond to this with either a message or emoji.
4. 30 minutes after a missed reminder an alert message will be sent notifying everyone in the channel that a check-in was missed and to try to contact that user in person.
5. To end a sessoin simply type ```stop```. This will change your status message to checked-out and remove reminder and alert messages.

### User Settings

  Settings can be managed using the ```set``` command followed by the setting name, then the desired value (e.g. ```set alert 60```). Currently available settings are:
- alert: This defines how long, in minutes from the last check in, until everyone in the channel is mentioned in an alert (default: 60)
- reminder: This defines how long, in minutes from the last check in, until the user is sent a reminder DM (default: 30)
