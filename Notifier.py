from valorlib.Packets.Packet import *

import re
import time
import random

class Notifier:

	lastQuestID = None
	lastActionTime = time.time()
	ignore = ["lucky djinn", "lucky ent god", "red demon", "cyclops ", "ghost king", "phoenix ", "ent ancient", "oasis "]
	needsDisplay = False
	questName = ""
	seenObjects = set()

	def main(self, client):
		if client.currentMap == "Nexus" and time.time() - self.lastActionTime > 30:
			p = PlayerText()
			p.text = "/realm"
			client.SendPacketToServer(CreatePacket(p))
			self.lastActionTime = time.time()

		elif client.currentMap == "Realm" and client.latestQuest != None:

			if client.oryx:
				print("going to oryx")
				p = PlayerText()
				p.text = "/nexus"
				client.SendPacketToServer(CreatePacket(p))
				self.lastActionTime = time.time()
				client.oryx = False

			if (self.lastQuestID == None or client.questSwitch) and client.latestQuest not in self.seenObjects:
				
				client.questSwitch = False

				if client.latestQuest in client.newObjects:

					self.seenObjects.add(client.latestQuest)
					self.needsDisplay = True
					self.questName = client.enemyName[client.newObjects[client.latestQuest].objectType]
					self.lastActionTime = time.time()
					print("got", self.questName)
				
				self.lastQuestID = client.latestQuest
				
		elif client.currentMap == "Vault":
			if time.time() - self.lastActionTime > 60:
				p = PlayerText()
				p.text = "/realm"
				client.SendPacketToServer(CreatePacket(p))
				self.lastActionTime = time.time()