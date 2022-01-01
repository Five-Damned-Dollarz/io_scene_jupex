import os
import struct

import bpy

from enum import IntEnum

from .utils import ReadRaw, ReadLTString, ReadCString

class ObjectPropertyType(IntEnum):
	String=0
	Vector=1
	Colour=2
	Float=3
	Int=4
	Flags=5
	Quaternion=6
	CommandString=7
	Text=8

class Object(object):
	def __init__(self):
		self.type_name=None
		self.properties={}

	def read(self, file):
		self.type_name=ReadLTString(file)

		prop_count, props_size=ReadRaw(file, "2I")

		props_buffer=file.read(props_size)
		for i in range(prop_count):
			name_index, prop_type=ReadRaw(file, "2I")
			prop_name=ReadCString(props_buffer[name_index:])

			data=file.read(4)
			if prop_type==ObjectPropertyType.String or prop_type==ObjectPropertyType.CommandString or prop_type==ObjectPropertyType.Text:
				data=struct.unpack("I", data)[0]
				data=ReadCString(props_buffer[data:]) #struct.unpack(props_buffer[data:], "s")
			elif prop_type==ObjectPropertyType.Vector or prop_type==ObjectPropertyType.Colour:
				data=struct.unpack("I", data)[0]
				data=struct.unpack("3f", props_buffer[data:data+12])
				data=(data[0], data[2], data[1]) # reorder vector for Blender
			elif prop_type==ObjectPropertyType.Float:
				data=struct.unpack("f", data)[0]
			elif prop_type==ObjectPropertyType.Int or prop_type==ObjectPropertyType.Flags:
				data=struct.unpack("i", data)[0]
			elif prop_type==ObjectPropertyType.Quaternion:
				data=struct.unpack("I", data)[0]
				data=struct.unpack("4f", props_buffer[data:data+16])
				data=(data[3], data[0], data[2], data[1]) # reorder the quat for Blender
			else:
				raise ValueError("Unknown object property type {}".format(prop_type))

			self.properties[prop_name]=data

def ReadObjects(file):
	collection=bpy.data.collections.new("Lights")
	bpy.context.scene.collection.children.link(collection)

	object_count=ReadRaw(file, "I")[0]

	objects=[]
	for i in range(object_count):
		new_obj=Object()
		new_obj.read(file)
		objects.append(new_obj)

		if new_obj.type_name in ["LightCube", "LightDirectional", "LightPoint", "LightPointFill", "LightSpot"]:
			print(new_obj.properties)

			light=bpy.data.lights.new(new_obj.properties["Name"], "POINT")
			light.energy=new_obj.properties["LightRadius"]
			light.color=new_obj.properties["LightColor"]
			light.distance=0.0

			light_obj=bpy.data.objects.new(new_obj.properties["Name"], light)
			light_obj.location=new_obj.properties["Pos"]
			light_obj.rotation_quaternion=new_obj.properties["Rotation"]

			collection.objects.link(light_obj)