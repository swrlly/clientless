import re
import rsa
import base64
import socket
import select
import struct
import requests
import time
import json

from valorlib.Packets.Packet import *
from RC4 import RC4

class Client:

	def __init__(self):
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

		self.buildVersion = "3.2.2"
		self.serverSocket = None

		# state consistency
		self.charID = None
		self.objectID = None
		self.charID = None
		self.reconnecting = False
		self.connected = False

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
	def fireHelloPacket(self):
		p = Hello()
		p.buildVersion = self.buildVersion
		p.gameID = -1
		p.guid = self.encryptString(self.email)
		p.password = self.encryptString(self.password)
		p.secret = ""
		p.keyTime = -1
		p.key = []
		p.mapJSON = ""
		p.cliBytes = 0
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

		# this happens every 30 seconds lmfao
		# i remember this strange packet causing me a 2 month blocker period.
		# if len(header) == 0:
		#	return
		
		# if the server sent nothing, keep trying until we recieve 5 bytes
		while len(header) != 5:
			print(":(", len(header))
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

		# keep-alive functions
		elif packet.ID == PacketTypes.Ping:
			p = Ping()
			p.read(packet.data)
			reply = Pong()
			reply.serial = p.serial
			reply.time = self.time()
			self.SendPacketToServer(CreatePacket(reply))

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

		elif packet.ID == PacketTypes.Reconnect:
			# update map name.
			p = Reconnect()
			p.read(packet.data)
			self.currentMap = p.name
			self.reconnecting = True

		elif packet.ID == PacketTypes.Failure:
			p = Failure()
			p.read(packet.data)
			p.PrintString()
			raise Exception("Got failure from server. Aborting")

	# main loop!
	def mainLoop(self):
		# first, connect to remote
		self.connect()
		# then, fire the hello packet
		self.fireHelloPacket()

		print("Connected to server!")

		# listen to packets
		while True:
			try:
				ready = select.select([self.serverSocket], [], [])[0]
				if self.serverSocket in ready:
					self.listenToServer()
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

	def getRandomCharID(self):
		x = requests.post(
			"http://51.222.11.213:8080/char/list",
			headers = self.headers,
			data = {
				"guid" : self.email,
				"password" : self.password,
				"game_net_user_id" : "",
				"game_net" : "rotmg",
				"do_login" : "true",
				"play_platform" : "rotmg",
				"ignore" : 0,
				"gameClientVersion" : self.buildVersion
			}
		).content.decode("utf-8")
		try:
			return int(re.findall("<char id=\"([0-9]+)\">", x, flags = re.I)[0])
		except IndexError:
			return -1


	#########
	# hooks #
	#########

	def onCreateSuccess(self, packet):
		p = CreateSuccess()
		p.read(packet.data)
		self.objectID = p.objectID
		self.charID = p.charID

	def initializeAccountDetails(self):
		try:
			x = json.load(open("account.json", "r"))
			self.email = x['email'].encode("utf-8")
			self.password = x['password'].encode("utf-8")

			if self.email == b"" or self.password == b"":
				raise Exception("You left your credentials blank!")

		except Exception as e:
			print(e)
			print("Make sure you are entering your account details correctly; do not forget the comma after the email value.")
			return False

		return True


if __name__ == "__main__":
	c = Client()
	if not c.initializeAccountDetails():
		print("Encountered exception. Quitting.")
	else:
		c.mainLoop()