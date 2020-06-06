# SafetyCheck
<a href="https://slack.amauney.com:444/begin_auth"><img alt="Add to Slack" height="40" width="139" src="https://platform.slack-edge.com/img/add_to_slack.png" srcset="https://platform.slack-edge.com/img/add_to_slack.png 1x, https://platform.slack-edge.com/img/add_to_slack@2x.png 2x"></a>

## Installing SafetyCheck
1. Add SafetyCheck to your workspace using the button above.


## Using SafetyCheck
1. Start a check-in session by saying ```start``` in the channel the bot is installed in.
2. The bot will generate a status message. Any interactions with the bot will now register as a check-in and this message will be updated.
3. After 30 minutes the bot will send a private message reminding you to check-in. Respond to this with either a message or emoji.
4. 30 minutes after a missed reminder an alert message will be sent notifying everyone in the channel that a check-in was missed and to try to contact that user in person.
5. To end a sessoin simply type ```stop```. This will change your status message to checked-out and remove reminder and alert messages.
