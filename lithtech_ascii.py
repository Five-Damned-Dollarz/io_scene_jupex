'''
Rough LTA format:

world
	header
		versioncode 2
	polyhedronlist
		polyhedron
			color
			pointlist points as (3x[0x########] 3x[0-255])
			polylist
				editpoly
					f (3x [vertex index])
					material "filename string"
					occlusion "unknown string"
					mappings (
						index to material input [usually 0-4] (
							textureinfo ([3x3 UV matrix?])
						)
					)
	nodehierarchy
		worldnode
			type null/brush
			brushindex idx [only for type brush]
			label [only for type null]
			nodeid [incremental unique?]
			flags [( worldroot [if has children?] expanded )]
			properties
				name "name string"
				propid idx
			childlist (worldnode)
	globalproplist
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

def OpqArea(vec_1, vec_2, vec_3):
	area_1=vec_2-vec_1
	area_2=vec_3-vec_1

	return area_1.x*area_2.y-area_2.x*area_1.y

def OpqCoords(vec_1, vec_2, vec_3, vec):
	tri_area=OpqArea(vec_1, vec_2, vec_3)

	if (abs(tri_area)<0.00000001):
		return Vector((1.0, 0.0, 0.0))

	u=OpqArea(vec_2, vec_3, vec)/tri_area
	v=OpqArea(vec_3, vec_1, vec)/tri_area
	w=1.0-u-v

	return Vector((u, v, w))

def CalculateOpq(vert_1, vert_2, vert_3, uv_1, uv_2, uv_3, tex_w, tex_h):
	uv_1=Vector((uv_1.x, -uv_1.y, 0.0))
	uv_2=Vector((uv_2.x, -uv_2.y, 0.0))
	uv_3=Vector((uv_3.x, -uv_3.y, 0.0))

	bary_o=OpqCoords(uv_1, uv_2, uv_3, Vector((0.0, 0.0, 0.0)))
	bary_p=OpqCoords(uv_1, uv_2, uv_3, Vector((1.0, 0.0, 0.0)))
	bary_q=OpqCoords(uv_1, uv_2, uv_3, Vector((0.0, 1.0, 0.0)))

	o=(bary_o.x*vert_1)+(bary_o.y*vert_2)+(bary_o.z*vert_3)
	p=(bary_p.x*vert_1)+(bary_p.y*vert_2)+(bary_p.z*vert_3)
	q=(bary_q.x*vert_1)+(bary_q.y*vert_2)+(bary_q.z*vert_3)

	p=p-o
	q=q-o

	p_len=p.length

	p_len=p_len*(1.0/tex_w)
	p_len=1.0/p_len

	q_len=q.length
	q_len=q_len*(1.0/tex_h)
	q_len=1.0/q_len

	p.normalize()
	q.normalize()

	r=q.cross(p)
	p_new=r.cross(q)
	q_new=p.cross(r)

	p_new.normalize()
	q_new.normalize()

	p_scale=1.0/p.dot(p_new)
	q_scale=1.0/q.dot(q_new)

	r=q_new.cross(p_new)

	p_new=p_new*p_len*p_scale
	q_new=q_new*q_len*q_scale

	r.normalize()
	p=p_new+r
	q=q_new-(p_new.dot(q_new)*r)

	return UvMatrix((o, p, q))

def write():
	main_node=Node("world")

	header_node=main_node.createChild("header", None, True)
	version_node=header_node.createChild("versioncode", 2)

	polyhedron_list_node=main_node.createChild("polyhedronlist", None, True)

	### for each object we're exporting create a geo list
	objects=[obj for obj in bpy.context.scene.objects if obj.type=='MESH']

	for obj in objects:

		### brush geo
		poly_node=polyhedron_list_node.createChild("polyhedron", None, True)
		poly_node.createChild("color", (255, 255, 255))

		pointlist_node=poly_node.createChild("pointlist")

		for (i, vert) in enumerate(obj.data.vertices):
			pointlist_node.createChild("", PointListEntry(vert.co))

		polylist_node=poly_node.createChild("polylist", None, True)

		for poly in obj.data.polygons:
			editpoly_node=polylist_node.createChild("editpoly")
			editpoly_node.createChild("f", [i for i in poly.vertices])
			#editpoly_node.createChild("material", r"Prefabs\Systemic\Vehicles\c2_exterior02.Mat00")
			#editpoly_node.createChild("occlusion", "")

			mappings_node=editpoly_node.createChild("mappings", None, True)

			_TextureScale=1
			try:
				_UvLayer=obj.data.uv_layers[0]
			except:
				_UvLayer=None

			verts=[]
			uvs=[]

			for loop_idx in poly.loop_indices:
				v1=obj.data.loops[loop_idx].vertex_index

				verts.append(obj.data.vertices[v1])

				if _UvLayer!=None:
					temp_uv=_UvLayer.data[loop_idx].uv;
				else:
					temp_uv=Vector((0, 0))

				uvs.append(temp_uv)

			try:
				opq=CalculateOpq(verts[0].co, verts[1].co, verts[2].co, uvs[0], uvs[1], uvs[2], _TextureScale, _TextureScale)
			except Exception as e:
				print("error", e, "creating opq values for", obj.name_full);
				opq=UvMatrix((Vector((0, 0, 0)), Vector((0, 0, 0)), Vector((0, 0, 0))))

			uv_node=mappings_node.createChild("0")
			texture_info_node=uv_node.createChild("textureinfo", opq)

			#uv_node=mappings_node.createChild("1")
			#texture_info_node=uv_node.createChild("textureinfo", UvMatrix(((66.0, 50.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))))

			#uv_node=mappings_node.createChild("2")
			#texture_info_node=uv_node.createChild("textureinfo", UvMatrix(((66.0, 50.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))))

			#uv_node=mappings_node.createChild("3")
			#texture_info_node=uv_node.createChild("textureinfo", UvMatrix(((66.0, 50.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))))

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

	# TODO: convert Blender's tree hierarchy as much as possible
	for i, obj in enumerate(objects):

		child_node=children_node.createChild("worldnode")
		child_node.createChild("type", WorldNodeType.brush)
		child_node.createChild("brushindex", i) # only for type brush
		child_node.createChild("nodeid", 70+i)
		flags_node=child_node.createChild("flags") # ( worldroot [if has children?] expanded )
		flags_node.createChild("", None)

		proplist_node=child_node.createChild("properties")
		proplist_node.createChild("name", "Brush")
		proplist_node.createChild("propid", i+1)
	###

	global_proplist_node=main_node.createChild("globalproplist", None, True)
	proplist_node=global_proplist_node.createChild("proplist", None, True)
	### node properties
	for i, obj in enumerate(objects):
		proplist_node=global_proplist_node.createChild("proplist", None, True)
		prop_name_node=proplist_node.createChild("string", "Name")
		prop_name_node.createChild("data", obj.name_full)
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