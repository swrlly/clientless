import os
import discord
import asyncio
import pickle
import threading

from client import Client
from dotenv import load_dotenv
from discord.ext.commands import Bot

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD = int(os.getenv("DISCORD_GUILD"))
CHANNEL = int(os.getenv("DISCORD_CHANNEL"))
ROLE = int(os.getenv("ROLE"))
ping = ['Queen of Hearts', 'Yazanahar', 'Larry Gigsman', 'Sorgigas', 'Mothership', 'Stone Gargoyle', 'Tod', "The Horrific"]

with open("NameDictionary.pkl", "rb") as f:
    nameDictionary = pickle.load(f)
client = Client(nameDictionary)
if not client.initializeAccountDetails():
    print("Encountered exception in initializing account details. Quitting.")
if not client.loadModules():
    print("No module was loaded. Quitting.")

intents = discord.Intents.all()
bot = Bot(command_prefix="-")

async def tracker():
    
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL)

    while not bot.is_closed():

        if client.module.needsDisplay:

            here = False

            for i in ping:
                if i in client.module.questName:
                    here = True

            if here:
                await channel.send("<@&{}> ".format(ROLE) +  client.module.questName + " spawned in realm.")
            else:
                pass
            client.module.needsDisplay = False
            await asyncio.sleep(0.5)

        while not client.messageQueue.empty():
            await channel.send(client.messageQueue.get())

@bot.event
async def on_ready():
    guild = discord.utils.find(lambda g: g.id == GUILD, bot.guilds)
    print(
        f'{bot.user} is connected to the following guild:\n'
        f'{guild.name}(id: {guild.id})'
    )

@bot.event
async def on_member_update(before, after):
    return

bot.loop.create_task(tracker())
botThread = threading.Thread(target = bot.run, args = (TOKEN,), daemon = True)
botThread.start()
print("Started discord bot thread.")
client.mainLoop()