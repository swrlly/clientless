# clientless

A headless client for the Realm of the Mad God private server Valor. Has functionality to track events and ping people in a discord server.

## Client only

1. Create an `account.json` that looks like this:

```
{
    "email" : "",
    "password" : "",
    "module": "afk"
}
```

where you would need to fill in account details and `module` can be some unique code called after packets are received from the server. See `AFK.py` for an example.

2. Type `python client.py` to login. You will be AFK in nexus.

## Notifier

1. Create an `account.json` that looks like this (need account info as well):

```
{
    "email" : "",
    "password" : "",
    "module": "notifier"
}
```

Create an `.env` file that contains the bot token, discord channel and discord guild:

```
DISCORD_TOKEN=bot token here
DISCORD_GUILD='your guild here'
DISCORD_CHANNEL='your channel here'
```

2. Type `python bot.py` and watch the notifications roll in.