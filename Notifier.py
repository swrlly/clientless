from valorlib.Packets.Packet import *

import re
import time
import random

class Notifier:

	# send messages in a discord channel notifying events

	lastQuestID = None
	lastActionTime = time.time()
	ignore = ["lucky djinn", "lucky ent god", "red demon", "cyclops ", "ghost king", "phoenix ", "ent ancient", "oasis "]
	needsDisplay = False
	questName = ""
	seenObjects = set()

	# main loop, called after packet has been read
	def main(self, client):
		# connect to realm
		if client.currentMap == "Nexus" and time.time() - self.lastActionTime > 2:
			p = PlayerText()
			p.text = "/realm"
			client.SendPacketToServer(CreatePacket(p))
			self.lastActionTime = time.time()

		# else if we are in realm and quest loaded, check for id
		elif client.currentMap == "Realm" and client.latestQuest != None:

			# check if we are going to oryx
			if client.oryx:
				print("going to oryx")
				p = PlayerText()
				p.text = "/vault"
				client.SendPacketToServer(CreatePacket(p))
				self.lastActionTime = time.time()
				client.oryx = False

			# if new quest arrived
			if (self.lastQuestID == None or client.questSwitch) and client.latestQuest not in self.seenObjects:
				
				# tell client no need to switch
				client.questSwitch = False

				# send message if it is a new object
				if client.latestQuest in client.newObjects:

					# tell ourselves we've seen it (to not have double ping)
					self.seenObjects.add(client.latestQuest)

					# tell bot that we need to display this message
					self.needsDisplay = True
					self.questName = client.enemyName[client.newObjects[client.latestQuest].objectType]
					self.lastActionTime = time.time()
					print("got", self.questName)
				
				self.lastQuestID = client.latestQuest
				

		elif client.currentMap == "Vault":
			# wait 1 minute before recon to realm
			if time.time() - self.lastActionTime > 60:
				p = PlayerText()
				p.text = "/realm"
				client.SendPacketToServer(CreatePacket(p))
				self.lastActionTime = time.time()