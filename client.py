import re
import rsa
import base64
import socket
import select
import struct
import requests
import time
import json
import pickle
import traceback
import threading

from valorlib.Packets.Packet import *	
from valorlib.Packets.DataStructures import *	
from valorlib.RC4 import RC4
from queue import Queue
# secret modules
from WZYBFIPQLMOH import *
from Notifier import *
from AFK import *

class ObjectInfo:

	def __init__(self):
		self.pos = WorldPosData()
		self.objectType = 0

	def PrintString(self):
		self.pos.PrintString()
		print("objectType", self.objectType)

class Client:

	def __init__(self, names: dict):

		# static stuff
		self.publicKey = rsa.PublicKey.load_pkcs1_openssl_pem(b"-----BEGIN PUBLIC KEY-----\nMFswDQYJKoZIhvcNAQEBBQADSgAwRwJAeyjMOLhcK4o2AnFRhn8vPteUy5Fux/cXN/J+wT/zYIEUINo02frn+Kyxx0RIXJ3CvaHkwmueVL8ytfqo8Ol/OwIDAQAB\n-----END PUBLIC KEY-----")
		self.remoteHostAddr = "51.222.11.213"
		self.remoteHostPort = 2050
		# use this key to decrypt packets from the server
		self.clientReceiveKey = RC4(bytearray.fromhex("612a806cac78114ba5013cb531"))
		# use this key to send packets to the server
		self.serverRecieveKey = RC4(bytearray.fromhex("BA15DE"))
		self.headers = {
			'User-Agent': "Mozilla/5.0 (Windows; U; en-US) AppleWebKit/533.19.4 (KHTML, like Gecko) AdobeAIR/32.0",
			'Referer' : 'app:/Valor.swf',
			'x-flash-version' : '32,0,0,170'
		}
		self.email = None
		self.password = None
		self.buildVersion = "3.8.0"
		self.loginToken = b""
		self.serverSocket = None
		self.lastPacketTime = time.time()
		
		# modules + internal variables
		self.moduleName = "none"
		self.module = None
		self.enemyName = names
		self.reconnecting = False
		self.connected = False
		self.blockLoad = False
		self.helloTime = 0
		self.messageQueue = Queue()

		# state consistency
		self.gameIDs = {
			1 : "Realm",
			-1 : "Nexus",
			-2 : "Nexus",
			-5 : "Vault",
			-15 : "Marketplace",
			-16 : "Ascension Enclave",
			-17 : "Aspect Hall"
		}
		self.currentMap = None
		self.charID = None
		self.objectID = None
		self.newObjects = {}
		self.oryx = False
		self.nextGameID = -1
		self.nextKeyTime = 0
		self.nextKey = []
		self.latestQuest = None
		self.questSwitch = False

		# this is in milliseconds
		self.clientStartTime = int(time.time() * 1000)
		self.ignoreIn = []
		"""
		self.ignoreIn = [
			PacketTypes.ShowEffect, PacketTypes.Ping, PacketTypes.Goto, 
			PacketTypes.Update, PacketTypes.NewTick, PacketTypes.EnemyShoot
			]
		"""

	# returns how long the client has been active
	def time(self):
		return int(time.time() * 1000 - self.clientStartTime)

	"""
	connect remote host -> send hello packet
	"""
	def connect(self):
		self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.serverSocket.connect((self.remoteHostAddr, self.remoteHostPort))
		self.connected = True
		
	# send hello packet
	def fireHelloPacket(self, useReconnect):
		p = Hello()

		if not useReconnect:
			p.buildVersion = self.buildVersion
			p.gameID = -1
			p.guid = self.encryptString(self.email)
			p.loginToken = self.encryptString(self.loginToken)
			p.keyTime = -1
			p.key = []
			p.mapJSON = ""
			p.cliBytes = 0
			self.currentMap = 'Nexus'
		else:
			p.buildVersion = self.buildVersion
			p.gameID = self.nextGameID
			self.currentMap = self.gameIDs[p.gameID]
			p.guid = self.encryptString(self.email)
			p.loginToken = self.encryptString(self.loginToken)
			p.keyTime = self.nextKeyTime
			p.key = self.nextKey
			p.mapJSON = ""
			p.cliBytes = 0

		p.PrintString()

		# after sending hello, reset states (since keys have expired)
		self.nextGameID = -1
		self.nextKeyTime = 0
		self.nextKey = []

		self.helloTime = time.time()
		
		self.SendPacketToServer(CreatePacket(p))

	def fireLoadPacket(self):
		p = Load()
		# should only trigger on startup
		if self.charID is None:
			self.charID = self.getRandomCharID()
		p.charID = self.charID
		p.isFromArena = False
		self.SendPacketToServer(CreatePacket(p))

	# listen for incoming packets and deal with them
	def listenToServer(self):

		header = self.serverSocket.recv(5)

		if len(header) == 0:
			print("server sent 0")
			self.reset()
		
		# if the server sent nothing, keep trying until we recieve 5 bytes
		while len(header) != 5:
			header += self.serverSocket.recv(5 - len(header))

		packetID = header[4]
		expectedPacketLength = struct.unpack("!i", header[:4])[0]
		# read the packet, subtract 5 cuz you already read header
		leftToRead = expectedPacketLength - 5
		data = bytearray()
		
		while (leftToRead > 0):
			buf = bytearray(self.serverSocket.recv(leftToRead))
			data += buf
			leftToRead -= len(buf)

		# decipher it to update our internal state
		self.clientReceiveKey.decrypt(data)
		packet = Packet(header, data, packetID)
		send = True

		"""	
		# for debugging
		try:
			if packet.ID not in self.ignoreIn:
				print("Server sent:", PacketTypes.reverseDict[packet.ID])
		except:
			print("Got unknown packet from server, id", packet.ID)
		"""
		
		if packet.ID == PacketTypes.CreateSuccess:
			# capture our object ID, necessary to send many types of packets like invswap or buy
			self.onCreateSuccess(packet)

		elif packet.ID == PacketTypes.Goto:
			p = GotoAck()
			p.time = self.time()
			self.SendPacketToServer(CreatePacket(p))

		# keep-alive functions
		elif packet.ID == PacketTypes.Ping:
			p = Ping()
			p.read(packet.data)
			reply = Pong()
			reply.serial = p.serial
			reply.time = self.time()
			self.SendPacketToServer(CreatePacket(reply))

		elif packet.ID == PacketTypes.Update:

			p = UpdateAck()
			self.SendPacketToServer(CreatePacket(p))

			p = Update()
			p.read(packet.data)
			for i in p.newObjects:
				obj = ObjectInfo()
				obj.pos = i.objectStatusData.pos
				obj.objectType = i.objectType
				self.newObjects.update({i.objectStatusData.objectID : obj})

		elif packet.ID == PacketTypes.Text:
			p = Text()
			p.read(packet.data)
			if p.name == '#Sidon the Dark Elder' and 'CLOSED THIS' in p.text:
				self.oryx = True

		elif packet.ID == PacketTypes.NewTick:
			p = NewTick()
			p.read(packet.data)
			#p.PrintString()

		elif packet.ID == PacketTypes.QueuePing:
			p = QueuePing()
			p.read(packet.data)
			reply = QueuePong()
			reply.serial = p.serial
			reply.time = self.time()
			self.SendPacketToServer(CreatePacket(reply))

		# you need to ack the update packets
		elif packet.ID == PacketTypes.Update:
			p = UpdateAck()
			self.SendPacketToServer(CreatePacket(p))

		# server expects a Load from the client after AccountList
		elif packet.ID == PacketTypes.AccountList:
			# then, fire Load packet
			self.fireLoadPacket()

		elif packet.ID == PacketTypes.QuestObjId:
			p = QuestObjId()
			p.read(packet.data)
			self.questSwitch = True
			self.latestQuest = p.objectID

		elif packet.ID == PacketTypes.Reconnect:
			# update map name.
			p = Reconnect()
			p.read(packet.data)
			
			self.nextGameID = p.gameID
			self.nextKeyTime = p.keyTime
			self.nextKey = p.key
			p.PrintString()
			self.reconnecting = True

		elif packet.ID == PacketTypes.Failure:
			p = Failure()
			p.read(packet.data)
			p.PrintString()
			raise Exception("Got failure from server. Aborting")

	# create a wizzy
	def Create(self):
		p = Create()
		p.classType = 782
		p.skinType = 0
		self.SendPacketToServer(CreatePacket(p))


	def reset(self):
		self.resetStates()
		self.clientReceiveKey.reset()
		self.serverRecieveKey.reset()
		self.serverSocket = None
		self.gameSocket = None
		
		# first, connect to remote
		self.connect()
		
		# then, fire the hello packet, connect to new map
		self.fireHelloPacket(True)		
		self.clientStartTime = int(time.time() * 1000)

	def resetStates(self):
		self.connected = False
		self.helloTime = 0
		self.clientReceiveKey.reset()
		self.serverRecieveKey.reset()
		self.objectID = None
		self.newObjects = {}
		self.oryx = False
		self.latestQuest = None
		self.clientStartTime = int(time.time() * 1000)


	def onReconnect(self):
		self.Disconnect()
		self.resetStates()
		self.connect()
		self.fireHelloPacket(True)


		# load or create:
		if self.charID is None:
			self.charID = self.getRandomCharID()

		if self.charID == -1:
			self.blockLoad = True
			self.Create()

	def Disconnect(self):
		self.connected = False
		if self.serverSocket:
			self.serverSocket.shutdown(socket.SHUT_RD)
			self.serverSocket.close()
		self.gameSocket = None

	# main loop!
	def mainLoop(self):

		# post to acc/verify
		self.accountVerify()

		# first, connect to remote
		self.connect()
		# then, fire the hello packet, connect to nexus.
		self.fireHelloPacket(False)


		# load or create:
		if self.charID is None:
			self.charID = self.getRandomCharID()

		# if no character exists
		if self.charID == -1:
			self.blockLoad = True
			self.Create()

		print("Connected to server!")

		# listen to packets
		while True:

			try:
				if time.time() - self.lastPacketTime > 30:
					print("Connection was hanging")
					self.reset()
				
				# take care of reconnect first
				if self.reconnecting:

					# flush
					ready = select.select([self.serverSocket], [], [])[0]
					if self.serverSocket in ready:
						self.serverSocket.recv(20000)

					self.onReconnect()
					self.reconnecting = False

				# check if there is data ready from the server
				ready = select.select([self.serverSocket], [], [])[0]
				if self.serverSocket in ready:
					self.lastPacketTime = time.time()
					self.listenToServer()

				# finally, run a custom module
				self.module.main(self)

			except ConnectionAbortedError as e:
				print("Connection was aborted:", e)
				self.reset()

			except ConnectionResetError as e:
				print("Connection was reset")
				traceback.print_exc()
				self.reset()

			except Exception as e:
				print("Ran into exception:", e)
				self.reset()

			except KeyboardInterrupt:
				print("Quitting.")
				return

	# rsa encrypt + base 64
	def encryptString(self, s):
		return base64.b64encode(rsa.encrypt(s, self.publicKey))

	# send a packet to the server
	def SendPacketToServer(self, packet):
		self.serverRecieveKey.encrypt(packet.data)
		self.serverSocket.sendall(packet.format())

	# get loginToken
	def accountVerify(self):

		x = requests.post(
			"https://valor-prod.realmdex.com/account/verify?g={}".format(self.email),
			headers = self.headers,
			data = {
				"guid" : self.email,
				"password" : self.password,
				"pin": "",
				"ignore" : 0,
				"gameClientVersion" : self.buildVersion
			}
		).content.decode("utf-8")
		self.loginToken = bytes(re.findall("<LoginToken>(.+?)</LoginToken>", x, flags = re.I)[0], 'utf-8')
		print(self.loginToken)

	def getRandomCharID(self):
		print("getting random char ID")
		x = requests.post(
			"https://valor-prod.realmdex.com/char/list?g={}".format(self.email),
			headers = self.headers,
			data = {
				"guid" : self.email,
				"loginToken" : self.loginToken,
				"do_login" : "true",
				"ignore" : 0,
				"gameClientVersion" : self.buildVersion
			}
		).content.decode("utf-8")

		try:
			charID = int(re.findall("<char id=\"([0-9]+)\">", x, flags = re.I)[0])
			return charID
		except IndexError:
			return -1

	def onCreateSuccess(self, packet):
		p = CreateSuccess()
		p.read(packet.data)
		self.connected = True
		self.objectID = p.objectID
		self.charID = p.charID
		print("Connected to {}!".format(self.currentMap))

	#########
	# hooks #
	#########

	def initializeAccountDetails(self):
		try:
			x = json.load(open("account.json", "r"))
			self.email = x['email'].encode("utf-8")
			self.password = x['password'].encode("utf-8")
			self.moduleName = x['module']

			if self.email == b"" or self.password == b"":
				raise Exception("You left your credentials blank!")

		except Exception as e:
			print(e)
			print("Make sure you are entering your account details correctly; do not forget the comma after the email value.")
			return False

		return True

	def loadModules(self):
		if self.moduleName == "notifier":
			self.module = Notifier()
		elif self.moduleName == "none":
			self.module = AFK()
		elif self.moduleName == "WZYBFIPQLMOH":
			self.module = WZYBFIPQLMOH()

		if self.module == None:
			return False

		return True

if __name__ == "__main__":

	with open("NameDictionary.pkl", "rb") as f:
		nameDictionary = pickle.load(f)


	c = Client(nameDictionary)
	if not c.initializeAccountDetails():
		print("Encountered exception in initializing account details. Quitting.")
	if not c.loadModules():
		print("No module was loaded. Quitting.")
	else:
		c.mainLoop()