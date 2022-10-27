from math import ceil
import bpy
import bpy_extras
import bmesh
from mathutils import Vector

import struct

from .utils import ReadRaw, ReadVector, ReadLTString, ReadCString

from .WorldModels import TestWorldModel, readStringTable

### Wld BSP section

_MagicConstant=b"WLDP"
_VersionConstants=[113, 126]

_LastVersion=0

class WldHeader(object):
	def __init__(self):
		self.magic=None
		self.version=0

	def read(self, file):
		self.magic, self.version=ReadRaw(file, "4sI")

		if self.magic!=_MagicConstant:
			raise ValueError("Incorrect file identifier {}, expected {}".format(self.magic, _MagicConstant))

		if self.version not in _VersionConstants:
			raise ValueError("Incorrect world version {}, expected {}".format(self.version, _VersionConstant))

		global _LastVersion
		_LastVersion=self.version

		_=ReadVector(file)
		_=ReadVector(file)
		_=ReadVector(file)
		_=ReadVector(file)
		_=ReadVector(file)

class WldModelsSection(object):
	def __init__(self):
		self.node_count=0
		self.subdivision_flags=[]

		self.string_count=0
		self.string_length=0
		self.strings=[]
		self.string_entries=[]

		self.normal_count=0
		self.normals=[]

		self.bsp_count=0

		self.float_count=0
		self.floats=[]

	def read(self, file):
		self.node_count=ReadRaw(file, "I")[0]
		self.subdivision_flags=ReadRaw(file, "{}B".format(ceil(self.node_count/8)))

		if _LastVersion==_VersionConstants[0]:
			_=ReadRaw(file, "I")

		self.string_count, self.string_length=ReadRaw(file, "II")
		self.normal_count, self.bsp_count=ReadRaw(file, "II")
		_=ReadRaw(file, "4I")

		if _LastVersion==_VersionConstants[1]:
			self.float_count=ReadRaw(file, "I")[0]
			self.floats=ReadRaw(file, "{}f".format(self.float_count))

		#self.strings=ReadRaw(file, "{}c".format(self.string_length))
		self.strings=file.read(self.string_length)

		self.string_entries=[]
		for i in range(self.string_count):
			temp_entry=ReadRaw(file, "II")
			self.string_entries.append(temp_entry)

		self.strings=readStringTable(self.bsp_count, self.strings, self.string_entries)

		self.normals=[]
		for i in range(self.normal_count):
			temp_normal=ReadVector(file)
			self.normals.append(temp_normal)

class WldBspPolygon(object):
	def __init__(self):
		self.surface_flags=0

		self.plane_id=-1
		self.plane_distance=float('nan')

		self.vertex_ids=[]

	def __repr__(self):
		return "BSP Poly: {} {} {} {}".format(self.surface_flags, self.plane_id, self.plane_distance, self.vertex_ids)

	def __str__(self):
		return repr(self)

	def read(self, file, vert_count):
		_=ReadRaw(file, "2b")

		self.surface_flags=ReadRaw(file, "H")[0]
		self.plane_id, self.plane_distance=ReadRaw(file, "If")
		self.vertex_ids=ReadRaw(file, "{}I".format(vert_count))

class WldUnknownTable(object):
	def __init(self):
		_=None

	def read(self, file):
		if _LastVersion==_VersionConstants[0]:
			_=ReadRaw(file, "Iii")
		elif _LastVersion==_VersionConstants[1]:
			_=ReadRaw(file, "Ihh")
		else:
			raise Exception(f"Trying to read WldUnknownTable with invalid version: {_LastVersion}")

class WldWorldModel(object):
	def __init__(self):
		self.vertex_count=0
		self.polygon_count=0
		self.unknown_table_count=0

		self.vertex_counts=[]

		self.polygons=[]
		self.unknown_table=[]
		self.vertices=[]

	def __repr__(self):
		return "World Model: {} {} {} {}".format(self.vertex_count, self.polygon_count, self.unknown_table_count)

	def __str__(self):
		return repr(self)

	def read(self, file):
		_, self.vertex_count, self.polygon_count, _, self.unknown_table_count=ReadRaw(file, "5I")
		_=ReadVector(file)
		_=ReadVector(file)

		if _LastVersion==_VersionConstants[0]:
			_=ReadRaw(file, "I")

		self.vertex_counts=ReadRaw(file, "{}B".format(self.polygon_count))

		self.polygons=[]
		for i in range(self.polygon_count):
			new_poly=WldBspPolygon()
			new_poly.read(file, self.vertex_counts[i])
			self.polygons.append(new_poly)

		self.unknown_table=[]
		for i in range(self.unknown_table_count):
			tmp=WldUnknownTable()
			tmp.read(file)
			self.unknown_table.append(tmp)

		self.vertices=[]
		for i in range(self.vertex_count):
			temp_vert=ReadVector(file)
			temp_vert=Vector((temp_vert[0], temp_vert[2], temp_vert[1]))
			self.vertices.append(temp_vert)

def ReadWldFile(file):
	header=WldHeader()
	header.read(file)

	model_section=WldModelsSection()
	model_section.read(file)

	bsps=[]
	for i in range(model_section.bsp_count):
		temp_wm=WldWorldModel()
		temp_wm.read(file)
		temp_wm.names=model_section.strings[i]
		bsps.append(temp_wm)

	collection=bpy.data.collections.new("FEAR 2 BSPs")
	bpy.context.scene.collection.children.link(collection)
	for i in bsps:
		TestWorldModel(i, collection);