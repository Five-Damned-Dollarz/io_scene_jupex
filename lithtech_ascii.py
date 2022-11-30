import bpy
import struct
from mathutils import Vector
from enum import Enum

class WorldNodeType(Enum):
	null="null"
	brush="brush"

	def __str__(self):
		return f"{self.name}"

class Node(object):
	def __init__(self, name="<unknown>", attribute=None, is_list=False):
		self.name=name
		self.attribute=attribute
		self.is_list=is_list

		self.children=[]

		self._depth=0

	def createChild(self, name, attribute=None, is_list=False):
		node=Node(name, attribute, is_list)
		node._depth=self._depth+1

		self.children.append(node)

		return node

	def serialize(self):
		str_out=""

		str_out+=self._writeDepth()
		str_out+=f"( {self.name} "

		if self.attribute is not None:
			str_out+=self._writeAttribute()

		if self.is_list:
			str_out+="("
		str_out+="\n"

		for child in self.children:
			str_out+=child.serialize()

		str_out+=self._writeDepth()
		if self.is_list:
			str_out+=") "
		str_out+=")\n"

		return str_out

	def _writeAttribute(self):
		if type(self.attribute) is int:
			return "%d" % self.attribute
		elif type(self.attribute) is str:
			return f'"{self.attribute}"'
		elif type(self.attribute) is float:
			return "%.6f" % self.attribute
		elif type(self.attribute) is Vector:
			return "%.6f %.6f %.6f" % (self.attribute.x, self.attribute.y, self.attribute.z)
		elif type(self.attribute) is list:
			return self._writeList(self.attribute)
		elif type(self.attribute) is tuple:
			return self._writeList(self.attribute)
		elif type(self.attribute) is UvMatrix:
			return self._writeMatrix(self.attribute)

		return str(self.attribute)

	def _writeVector(self, val):
		return f"{val.x} {val.y} {val.z}"

	def _writeList(self, val):
		return " ".join([str(i) for i in val])

	def _writeMatrix(self, val):
		str_out="\n"

		self._depth+=1

		for row in val.matrix:
			str_out+=self._writeDepth()
			str_out+="( {} )\n".format(" ".join(floattohex(x) for x in row))

		self._depth-=1

		return str_out

	def _writeDepth(self):
		return "\t"*self._depth

def floattohex(f):
	return hex(struct.unpack('<I', struct.pack('<f', f))[0])

class PointListEntry(object):
	def __init__(self, pos):
		self.position=pos
		self.colour=(255, 255, 255, 255)

	def __repr__(self): # FIXME: garbage
		return "{} {}".format(" ".join(floattohex(x) for x in self.position), " ".join(str(x) for x in self.colour))

	def __str__(self):
		return repr(self)

class UvMatrix(object):
	def __init__(self, mat):
		self.matrix=mat

	def __repr__(self):
		str_out=""

		for row in self.matrix:
			str_out+="( {} )\n".format(" ".join(floattohex(x) for x in row))

		return str_out

	def __str__(self):
		return repr(self)

def write():
	main_node=Node("world")

	header_node=main_node.createChild("header", None, True)
	version_node=header_node.createChild("versioncode", 2)

	polylist_node=main_node.createChild("polyhedronlist", None, True)

	### brush geo
	poly_node=polylist_node.createChild("polyhedron", None, True)
	poly_node.createChild("color", (255, 255, 255))

	pointlist_node=poly_node.createChild("pointlist")

	objects=[obj for obj in bpy.context.scene.objects if obj.type=='MESH']

	for (i, vert) in enumerate(objects[0].data.vertices):
		pointlist_node.createChild("", PointListEntry(vert.co))

	polylist_node=poly_node.createChild("polylist", None, True)

	for poly in objects[0].data.polygons:
		editpoly_node=polylist_node.createChild("editpoly")
		editpoly_node.createChild("f", [i for i in poly.vertices])

	###

	nodelist_node=main_node.createChild("nodehierarchy")
	### world nodes
	world_node=nodelist_node.createChild("worldnode")
	world_node.createChild("type", WorldNodeType.null)
	world_node.createChild("label", "Base_Node") # only for type null
	world_node.createChild("nodeid", 69)
	flags_node=world_node.createChild("flags") # ( worldroot [if has children?] expanded )
	flags_node.createChild("", ["worldroot", "expanded"])

	proplist_node=world_node.createChild("properties")
	proplist_node.createChild("propid", 0)

	children_node=world_node.createChild("childlist", None, True)
	child_node=children_node.createChild("worldnode")
	child_node.createChild("type", WorldNodeType.brush)
	child_node.createChild("brushindex", 0) # only for type brush
	child_node.createChild("nodeid", 70)
	flags_node=child_node.createChild("flags") # ( worldroot [if has children?] expanded )
	flags_node.createChild("", None)

	proplist_node=child_node.createChild("properties")
	proplist_node.createChild("name", "Brush")
	proplist_node.createChild("propid", 1)
	###

	global_proplist_node=main_node.createChild("globalproplist", None, True)
	### node properties
	proplist_node=global_proplist_node.createChild("proplist", None, True)
	proplist_node=global_proplist_node.createChild("proplist", None, True)
	#proplist_node.createChild("string", "Name") # FIXME
	'''
	proplist (
		( string "Name" (  ) ( data "name string") )
		( string "Type" ( staticlist ) ( data ["Normal", "RenderOnly"] ) )
		( bool "NotAStep" (  ) ( data 0 ))
		( bool "ClipLight" (  ) ( data 0 ))
		( real "CreaseAngle" (  ) ( data 45.000000 ))
		( string "TangentMethod" ( staticlist ) ( data "Kaldera") )
		( string "ShadowLOD" ( staticlist ) ( data "Low") )
		( vector "Pos" ( hidden distance ) ( data ( vector (0.000000 0.000000 0.000000) ) ) )
		( rotation "Rotation" ( hidden ) ( data (eulerangles (0.028577 0.000000 0.000000) ) ) )
	)
	'''
	###

	return main_node.serialize()