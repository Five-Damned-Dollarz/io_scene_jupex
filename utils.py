import os
import struct

def ReadRaw(file, format):
	buf=struct.unpack(format, file.read(struct.calcsize(format)))
	#print(buf)
	return buf

def ReadVector(file):
	return ReadRaw(file, "3f")

def ReadLTString(file):
	return file.read(struct.unpack("H", file.read(2))[0]).decode("ascii")
	
def ReadCString(buffer):
	return buffer.split(b'\x00')[0].decode("ascii")