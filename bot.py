# join a discord channel, ping when yaza/larry/sor/mothership/garg/tod spawns

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
ping = ['Yazanahar', 'Larry Gigsman','Sorgigas', 'Mothership', 'Stone Gargoyle', 'Tod', 'Cyber Lord']

# load client
with open("NameDictionary.pkl", "rb") as f:
	nameDictionary = pickle.load(f)
client = Client(nameDictionary)
if not client.initializeAccountDetails():
	print("Encountered exception in initializing account details. Quitting.")
if not client.loadModules():
	print("No module was loaded. Quitting.")

# load bot
intents = discord.Intents.default()
bot = Bot(command_prefix="-")

async def tracker():
	
	await bot.wait_until_ready()
	channel = bot.get_channel(CHANNEL)

	while not bot.is_closed():

		# if we got a signal that we need to display a message
		if client.module.needsDisplay:

			here = False

			for i in ping:
				if i in client.module.questName:
					here = True

			if here:
				await channel.send("@here " + client.module.questName + " has spawned in realm.")
			else:
				pass
			client.module.needsDisplay = False
			await asyncio.sleep(0.5)

@bot.event
async def on_ready():
	guild = discord.utils.find(lambda g: g.id == GUILD, bot.guilds)
	print(
		f'{bot.user} is connected to the following guild:\n'
		f'{guild.name}(id: {guild.id})'
	)

bot.loop.create_task(tracker())
botThread = threading.Thread(target = bot.run, args = (TOKEN,))
botThread.start()
print("Started discord bot thread.")
clientThread = threading.Thread(target = client.mainLoop)
clientThread.start()
print("Started client thread.")