from math import ceil
import bpy
import bpy_extras
import bmesh
from mathutils import Vector

import struct

from .utils import ReadRaw, ReadVector, ReadLTString, ReadCString

### BSP Section

class BspPolygon(object):
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

class WorldModel(object):
	def __init__(self):
		self.names=[]

		self.polygons=[]
		self.vertices=[]

	def read(self, file):
		_=ReadRaw(file, "I")
		point_count, polygon_count, unk_count, node_count=ReadRaw(file, "4I")

		half_extent=ReadVector(file)
		center=ReadVector(file)

		_=ReadRaw(file, "I")

		vertex_counts=file.read(polygon_count)

		for i in range(polygon_count):
			poly=BspPolygon()
			poly.read(file, vertex_counts[i])
			self.polygons.append(poly)

		nodes=[]
		for _ in range(node_count):
			nodes.append(ReadRaw(file, "I2i"))

		for _ in range(point_count):
			temp_vert=ReadVector(file)
			temp_vert=Vector([temp_vert[0], temp_vert[2], temp_vert[1]])
			self.vertices.append(temp_vert)

		# do polygon vertex fixup here?

# returns array of strings correctly ordered for: bsp.name=str_table[bsp.id]
def readStringTable(count, raws, indices):
	strings_out=[]

	for _ in range(count):
		strings_out.append([])

	for ind in indices: # (str idx, bsp id)
		strings_out[ind[1]].append(ReadCString(raws[ind[0]:]))

	return strings_out

class WorldModelSection(object):
	def __init__(self):
		self.bounds_min=Vector()
		self.bounds_max=Vector()

	def read(self, file, magic_number): # pull in the magic number
		self.bounds_min=ReadVector(file)
		self.bounds_max=ReadVector(file)

		count, _=ReadRaw(file, "2I")

		_=ReadRaw(file, "{}B".format(ceil(count/8)))

		counts=[count ^ magic_number for count in ReadRaw(file, "8I")]
		bsp_name_count, bsp_names_length, plane_count, bsp_count, node_count, polygon_count, vertex_ref_count, vertex_count=counts

		bsp_names=file.read(bsp_names_length)

		bsp_name_indices=[]
		for _ in range(bsp_name_count):
			bsp_name_indices.append(ReadRaw(file, "2I"))

		world_model_names=readStringTable(bsp_count, bsp_names, bsp_name_indices)

		planes=[]
		for _ in range(plane_count):
			planes.append(ReadVector(file))

		world_models=[]
		for i in range(bsp_count):
			world_model=WorldModel()
			world_model.read(file)
			world_model.names=world_model_names[i]

			world_models.append(world_model)

		collection=bpy.data.collections.new("World Models")
		bpy.context.scene.collection.children.link(collection)
		for i in world_models:
			TestWorldModel(i, collection)

def TestWorldModel(model, collection):
	mesh=bpy.data.meshes.new("BSP")
	mesh_obj=bpy.data.objects.new(model.names[0], mesh)

	bm=bmesh.new()
	bm.from_mesh(mesh)

	for vert in model.vertices:
		bm.verts.new(vert)

	bm.verts.ensure_lookup_table()

	for poly in model.polygons:
		bmface=[bm.verts[vert_id] for vert_id in reversed(poly.vertex_ids)]

		try:
			bm.faces.new(bmface)
		except ValueError as e:
			print(repr(e), repr(poly))
			continue

	bm.faces.ensure_lookup_table()

	bm.to_mesh(mesh)
	bm.free()

	mesh.validate(clean_customdata=False)
	mesh.update(calc_edges=False)

	collection.objects.link(mesh_obj)