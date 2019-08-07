from savescum import config
import requests

def log(message):
    functions = config.log_functions()
    for function in functions:
        function(message)

def discord(message):
    # source: https://makerhacks.com/python-messages-discord/
    webhook_url = config.json()['logging']['discord-webhook']
    r = requests.post(webhook_url, data = {"content": message})

def downmail(message):
    from downmail.mailaccount import MailAccount
    creds = config.json()['logging']['downmail']
    account = MailAccount('imap.gmail.com', 993, 'smtp.gmail.com', 465,
                          creds['address'], creds['pw'])
    account.send_message_plain([creds['sendTo']], message, message)
