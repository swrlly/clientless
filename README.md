# clientless

A headless client for the Realm of the Mad God private server Valor.

## Usage

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