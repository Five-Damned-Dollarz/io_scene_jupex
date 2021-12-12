bl_info={
	"name": "Lithtech World Importer",
	"description": "Import Lithtech Jupiter Ex World00p files.",
	"author": "Amphos",
	"version": (0,0,0,0,0,00,0,0,0,00,0,0,0,00,0,0,0,00),
	"blender": (2, 90, 0),
	"location": "File > Import-Export",
	"support": "COMMUNITY",
	"category": "Import-Export",
}

import bpy
import bpy_extras
import bmesh
from bpy.props import StringProperty, BoolProperty, FloatProperty
from mathutils import Vector

from enum import IntEnum

import struct

class WorldLoader(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
	bl_idname="io_scene_jupex.world_loader"
	bl_label="Import Jupiter EX World"

	filename_ext=".world00p"

	filter_glob: StringProperty(
		default="*.world00p",
		options={'HIDDEN'},
		maxlen=255,
	)

	'''
	game_data_folder: StringProperty(
		name="Game Folder",
		description="Choose a directory:",
		default="",
		maxlen=260,
		subtype="DIR_PATH"
	)

	import_bsps: BoolProperty(
		name="Import BSPs",
		description="",
		default=False
	)

	import_nav_mesh: BoolProperty(
		name="Import Nav Mesh",
		description=""
		default=False
	)

	def draw(self, context):
		layout=self.layout

		box=layout.box()
		box.label(text="Data")
		box.row().prop(self, "game_data_folder")
	'''

	def execute(self, context):
		with open(self.filepath, "rb") as f:
			header=Header()
			header.read(f)
			print(header)

			f.seek(header.render_section) # skip to render section
			render_section=ReadRaw(f, "10I")
			ReadRenderMesh(f, render_section)

		# massively increase camera clipping because 1000m is not enough for even a normal sized room
		for area in bpy.context.screen.areas:
			if area.type=="VIEW_3D":
				for space in area.spaces:
					if space.type=="VIEW_3D":
						if space.clip_end<10000.0:
							space.clip_end=100000.0

		return {"FINISHED"}

	@staticmethod
	def menu_func_import(self, context):
		self.layout.operator(WorldLoader.bl_idname, text='Lithtech JupEx World (.world00p)')

def register():
	bpy.utils.register_class(WorldLoader)
	bpy.types.TOPBAR_MT_file_import.append(WorldLoader.menu_func_import)

def unregister():
	bpy.utils.unregister_class(WorldLoader)
	bpy.types.TOPBAR_MT_file_import.remove(WorldLoader.menu_func_import)

''' Python is incapable of allowing me simple import functionality, so fuck you '''

def ReadRaw(file, format):
	buf=struct.unpack(format, file.read(struct.calcsize(format)))
	#print(buf)
	return buf

def ReadVector(file):
	return ReadRaw(file, "3f")

def ReadLTString(file):
	return file.read(struct.unpack("H", file.read(2))[0]).decode("ascii")

###

_VersionConstant=113

class Header(object):
	def __init__(self):
		self.version=0

		# offsets
		self.render_section=0
		self.sector_section=0
		self.object_section=0
		self.unk_section=0

		self.bounds_min=Vector()
		self.bounds_max=Vector()
		self.world_offset=Vector()

	def __repr__(self):
		return "Header: {} [{:#08x} {:#08x} {:#08x} {:#08x}] [{} {}] {}".format(self.version, self.render_section, self.sector_section, self.object_section,
			self.unk_section, self.bounds_min, self.bounds_max, self.world_offset)

	def __str__(self):
		return repr(self)

	def read(self, file):
		self.version=ReadRaw(file, "I")[0]

		if self.version!=_VersionConstant:
			raise ValueError("Incorrect world version {}, expected {}".format(self.version, _VersionConstant))

		(self.render_section, self.sector_section, self.object_section, self.unk_section)=ReadRaw(file, "4I")

		self.bounds_min=ReadVector(file)
		self.bounds_max=ReadVector(file)
		self.world_offset=ReadVector(file)

class Vertex(object):
	def __init__(self):
		self.position=Vector()
		self.normal=Vector()

		self.tex_coords=Vector([0, 0])

		self.tangent=Vector()
		self.binormal=Vector()
		self.colour=Vector([0, 0, 0, 0])

class VertexPropertyFormat(IntEnum):
	Float_x2=1 # Vector2f
	Float_x3=2 # Vector3f
	Float_x4=3 # Vector4f
	Byte_x4=4 # Int_x1?
	SkeletalIndex=5 # Float or Int, depending on shader defs
	Exit=17

class VertexPropertyLocation(IntEnum):
	Position=0
	BlendWeight=1
	BlendIndices=2
	Normal=3
	TexCoords=5
	Tangent=6
	Binormal=7
	Colour=10

class VertexProperty(object):
	def __init__(self):
		self.format=-1
		self.location=-1
		self.id=0

class VertexDefinition(object):
	def __init__(self):
		self.properties=[]

	def readVertex(self, vertex_data) -> Vertex:
		temp_vert=Vertex()

		idx=0
		for prop in self.properties:

			pack_str=""
			if prop.format==VertexPropertyFormat.Float_x2:
				pack_str="2f"
			elif prop.format==VertexPropertyFormat.Float_x3:
				pack_str="3f"
			elif prop.format==VertexPropertyFormat.Float_x4:
				pack_str="4f"
			elif prop.format==VertexPropertyFormat.Byte_x4:
				pack_str="4B"
			elif prop.format==VertexPropertyFormat.SkeletalIndex:
				pack_str="4b" # 4 bytes
			elif prop.format==VertexPropertyFormat.Exit:
				continue # this /should/ never activate since we chop the final entry off when reading the descriptors
			else:
				raise ValueError("Invalid vertex property format")

			pack_size=struct.calcsize(pack_str)
			unpacked=struct.unpack(pack_str, vertex_data[idx:idx+pack_size])

			idx+=pack_size

			if prop.id>0: # handle this properly!
				print("Unhandled vertex property, id > 0")
				continue

			if prop.location==VertexPropertyLocation.Position:
				temp_vert.position=Vector([unpacked[0], unpacked[2], unpacked[1]])
			elif prop.location==VertexPropertyLocation.BlendWeight:
				print("Unhandled vertex blend weight parameter")
			elif prop.location==VertexPropertyLocation.BlendIndices:
				print("Unhandled vertex blend indices parameter")
			elif prop.location==VertexPropertyLocation.Normal:
				temp_vert.normal=Vector([unpacked[0], unpacked[2], unpacked[1]])
			elif prop.location==VertexPropertyLocation.TexCoords:
				temp_vert.tex_coords=Vector([unpacked[0], 1.0-unpacked[1]])
			elif prop.location==VertexPropertyLocation.Tangent:
				temp_vert.tangent=Vector([unpacked[0], unpacked[2], unpacked[1]])
			elif prop.location==VertexPropertyLocation.Binormal:
				temp_vert.binormal=Vector([unpacked[0], unpacked[2], unpacked[1]])
			elif prop.location==VertexPropertyLocation.Colour:
				temp_vert.colour=Vector([unpacked[0]/255, unpacked[1]/255, unpacked[2]/255, unpacked[3]/255])
			else:
				raise ValueError("Unknown vertex property location")

		return temp_vert

class RenderSurface(object):
	def __init__(self):
		self.vertices_start=0
		self.vertices_count=0
		self.vertex_size=0

		self.indices_start=0
		self.indices_offset=0
		self.indices_count=0

		self.material_id=0
		#self.unk=0
		self.vertex_definition=None

		self.vertices=[]
		self.indices=[]

	def read(self, file, vertex_defs, vertex_data, triangulation_data):
		raw=ReadRaw(file, "9I")

		self.vertices_start=raw[0]
		self.vertices_count=raw[1]
		self.vertex_size=raw[2]
		self.indices_start=raw[3]
		self.indices_offset=self.vertices_start-raw[4]
		self.indices_count=raw[5]
		self.material_id=raw[6]
		#self.unk=raw[7]

		self.vertex_definition=vertex_defs[raw[8]]

		buffer_offset=self.vertices_start*self.vertex_size
		buffer_end=buffer_offset+(self.vertices_count*self.vertex_size)
		self.readVertices(vertex_data[buffer_offset:buffer_end])

		buffer_offset=self.indices_start*2
		buffer_end=buffer_offset+(self.indices_count*6)
		self.readTriangulations(triangulation_data[buffer_offset:buffer_end])

	def readVertices(self, vertex_data):
		for i in range(self.vertices_count):
			idx=i*self.vertex_size
			buf=vertex_data[idx:idx+self.vertex_size]

			try:
				new_vert=self.vertex_definition.readVertex(buf)
			except ValueError as e:
				print(repr(e))

			self.vertices.append(new_vert)

		#print("SURFACE VERT COUNT", len(self.vertices))

	def readTriangulations(self, triangle_data):
		for i in range(self.indices_count):
			verts=struct.unpack("3H", triangle_data[i*6:(i*6)+6])
			verts=[(i-self.indices_offset) for i in verts]

			self.indices.append(verts) # -self.indices_offset?
			#face=[vert_id-(self.vertices_start-self.indices_offset) for vert_id in verts]

		#print("SURFACE TRI COUNT", len(self.indices))

def ReadRenderMesh(file, section_counts):
	mesh_counts=ReadRaw(file, "3I")
	block_sizes=ReadRaw(file, "2I")

	vertex_data=file.read(block_sizes[0])
	triangulation_data=file.read(block_sizes[1])

	struct_type_count=ReadRaw(file, "I")
	vertex_defs=[]
	for i in range(struct_type_count[0]):
		vertex_defs.append(ReadStructDef(file))

	render_surface_count=ReadRaw(file, "I")
	render_surfaces=[]

	for i in range(render_surface_count[0]):
		surface=RenderSurface()
		surface.read(file, vertex_defs, vertex_data, triangulation_data)
		render_surfaces.append(surface)

	collection=bpy.data.collections.new("Surfaces")
	bpy.context.scene.collection.children.link(collection)

	for i in render_surfaces:
		TestRenderSurface(i, collection)

	for i in range(mesh_counts[2]):
		print(ReadLTString(file))

	for i in range(section_counts[0]):
		ReadRenderTree(file)

def ReadStructDef(file):
	size=ReadRaw(file, "I")

	def_=VertexDefinition()

	for i in range(int(size[0]/8)):
		shorts=ReadRaw(file, "2H")
		bytes=ReadRaw(file, "4b")

		if shorts[0]==255:
			break

		prop=VertexProperty()
		prop.format=VertexPropertyFormat(bytes[0])
		prop.location=VertexPropertyLocation(bytes[2])
		prop.id=bytes[3]

		def_.properties.append(prop)

	return def_

def ReadRenderTree(file):
	count=ReadRaw(file, "I")

	for i in range(count[0]):
		ReadRenderNode(file)

def ReadRenderNode(file):
	counts=ReadRaw(file, "2I")

	for i in range(counts[0]):
		node_min=ReadVector(file)
		node_max=ReadVector(file)

		unknowns=ReadRaw(file, "3I")

		# just to visualize render node bounding boxes
		#center=((node_max[0]+node_min[0])/2, (node_max[1]+node_min[1])/2, (node_max[2]+node_min[2])/2)
		#dims=(node_max[0]-node_min[0], node_max[1]-node_min[1], node_max[2]-node_min[2])
		#bpy.ops.mesh.primitive_cube_add(size=1.0, calc_uvs=True, enter_editmode=False, align='WORLD', location=(center[0], center[2], center[1]), rotation=(0.0, 0.0, 0.0), scale=(dims[0]*2, dims[2]*2, dims[1]*2))

	for i in range(counts[1]):
		count=ReadRaw(file, "B")

		for j in range(count[0]):
			ReadVector(file)

def TestRenderSurface(surface, collection):
	mesh=bpy.data.meshes.new("Surface Test")
	mesh_obj=bpy.data.objects.new("Surface Obj", mesh)

	bm=bmesh.new()
	bm.from_mesh(mesh)

	for vert in surface.vertices:
		bm.verts.new(vert.position)

	bm.verts.ensure_lookup_table()

	for tri in surface.indices:
		bmface=[bm.verts[vert_id] for vert_id in tri]

		try:
			bm.faces.new(bmface)
		except ValueError as e:
			print(repr(e), tri)
			continue

	bm.faces.ensure_lookup_table()

	bm.to_mesh(mesh)
	bm.free()

	### Texture mapping

	uv_layer=mesh.uv_layers.new()

	uv_layer.active=True
	uv_layer.active_render=True

	for i, loop in enumerate(mesh.loops):
		uv=surface.vertices[loop.vertex_index].tex_coords
		uv_layer.data[i].uv=uv

	mesh.validate(clean_customdata=False)
	mesh.update(calc_edges=False)

	collection.objects.link(mesh_obj)