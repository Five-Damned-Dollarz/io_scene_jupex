bl_info={
	"name": "Lithtech World Importer",
	"description": "Import Lithtech Jupiter Ex World00p files.",
	"author": "Amphos",
	"version": (0,0,0,0,0,00,0,0,0,00,0,0,0,00,0,0,0,00),
	"blender": (2, 90, 0),
	"location": "File > Import-Export",
	"warning": "Extremely early development.",
	"support": "COMMUNITY",
	"category": "Import-Export",
}

import os
import bpy
import bpy_extras
import bmesh
from bpy.props import StringProperty, BoolProperty, FloatProperty, EnumProperty
from mathutils import Vector

from enum import Enum

import struct

# Python's import system sucks so much!
from .utils import ReadRaw, ReadVector, ReadLTString, ReadCString

# Jupiter EX
from . import WorldModels
from . import WorldObjects
from . import RenderMeshes

# Loki
from . import WldBsp

#Lithtech general
from . import lithtech_ascii as lta

import importlib
importlib.reload(WorldModels)
importlib.reload(WorldObjects)
importlib.reload(RenderMeshes)
importlib.reload(WldBsp)

###

_GameDataFolder=r""

class GameCode(Enum):
	FEAR1=399
	District187=246
	FEAR2=None
	Condemned=None
	PetaCity=1120

class ImportOptions(object):
	def __init__(self):
		self.GameDataFolder=r""
		self.GameId=None

		self.ImportBsps=False
		self.ImportRenderSurfaces=True
		self.ImportMaterials=True
		self.ImportObjects=False
		#self.ImportNavMesh=False

def importWorld(options: ImportOptions):
	return

###

class WorldLoader(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
	bl_idname="io_scene_jupex.world_loader"
	bl_label="Import Jupiter EX World"

	filename_ext=".world00p"

	filter_glob: StringProperty(
		default="*.world00p;*.wld",
		options={'HIDDEN'},
		maxlen=255,
	)

	def updateGameDataFolder(self, context):
		global _GameDataFolder
		_GameDataFolder=os.fspath(self.game_data_folder)
		return None

	game_data_folder: StringProperty(
		name="Game Folder",
		description="Folder containing all the extracted assets, must be the root folder containing GameClient.dll and GameServer.dll",
		default=r"F:\FEAR Stuff\FEAR Public Tools v2\Dev\Runtime\Game",
		maxlen=260,
		subtype="DIR_PATH",
		update=updateGameDataFolder
	)

	game_identity: EnumProperty(
		items=[
			(GameCode.FEAR1.name, "FEAR", "FEAR, FEAR: Extraction Point, and FEAR: Perseus Mandate", 0),
			(GameCode.District187.name, "District 187", "District 187, also known as S2 Son Silah", 1),
			(GameCode.FEAR2.name, "FEAR 2", "FEAR 2: Project Origin", 2),
			(GameCode.Condemned.name, "Condemned", "Condemned", 3),
			(GameCode.PetaCity.name, "PetaCity", "PetaCity", 4),
		],
		name="Game",
		description="Select the game the imported world is from",
		default=0
	)

	import_bsps: BoolProperty(
		name="Import BSPs",
		description="Currently only supports FEAR 1",
		default=False
	)

	import_render_surfaces: BoolProperty(
		name="Import Render Surfaces",
		description="",
		default=True
	)

	import_materials: BoolProperty(
		name="Import Materials",
		description="Warning: loading materials (including textures) can take a long time",
		default=True
	)

	import_objects: BoolProperty(
		name="Import Objects",
		description="Currently only supports Light objects",
		default=False
	)

	import_nav_mesh: BoolProperty(
		name="Import Nav Mesh",
		description="",
		default=False
	)

	def draw(self, context):
		layout=self.layout

		box=layout.box()
		box.label(text="Data")
		box.row().prop(self, "game_identity")
		box.row().prop(self, "game_data_folder")

		box=layout.box()
		box.label(text="Import Options")
		box.row().prop(self, "import_bsps")
		box.row().prop(self, "import_render_surfaces")
		box.row().prop(self, "import_materials")
		box.row().prop(self, "import_objects")
		#box.row().prop(self, "import_nav_mesh")

	def execute(self, context):
		opts=ImportOptions()
		opts.GameDataFolder=os.fspath(self.game_data_folder)
		opts.GameId=self.game_identity
		opts.ImportBsps=self.import_bsps
		opts.ImportRenderSurfaces=self.import_render_surfaces
		opts.ImportMaterials=self.import_materials
		opts.ImportObjects=self.import_objects
		#opts.ImportNavMesh=self.import_nav_mesh

		with open(self.filepath, "rb") as f:

			# FIXME: need a better solution for this
			if opts.GameId in [GameCode.FEAR2.name, GameCode.Condemned.name]:
				WldBsp.ReadWldFile(f)

				SetCamera()

				return {"FINISHED"}

			header=Header()
			header.read(f)
			print(header)

			if self.import_bsps:
				f.seek(56) # not needed
				wm_section=WorldModels.WorldModelSection()
				wm_section.read(f, GameCode[opts.GameId].value)

			if self.import_render_surfaces:
				f.seek(header.render_section)
				render_section=ReadRaw(f, "10I")
				RenderMeshes.ReadRenderMesh(f, render_section, opts)

			if self.import_objects:
				f.seek(header.object_section)
				WorldObjects.ReadObjects(f)

		SetCamera()

		return {"FINISHED"}

	@staticmethod
	def menu_func_import(self, context):
		self.layout.operator(WorldLoader.bl_idname, text='Lithtech JupEx World (.world00p)')

class WorldExporter(bpy.types.Operator, bpy_extras.io_utils.ExportHelper):
	bl_idname="io_scene_jupex.world_exporter"
	bl_label="Export Jupiter EX World"

	filename_ext=".world00a"

	filter_glob: StringProperty(
		default="*.world00a",
		options={'HIDDEN'},
		maxlen=255,
	)

	def execute(self, context):
		with open(self.filepath, "w") as f:
			f.write(lta.write())

		print("world00a export called")
		return {"FINISHED"}

	@staticmethod
	def menu_func_export(self, context):
		self.layout.operator(WorldExporter.bl_idname, text='Lithtech JupEx World (.world00a)')

def register():
	bpy.utils.register_class(WorldLoader)
	bpy.types.TOPBAR_MT_file_import.append(WorldLoader.menu_func_import)

	bpy.utils.register_class(WorldExporter)
	bpy.types.TOPBAR_MT_file_export.append(WorldExporter.menu_func_export)

def unregister():
	bpy.utils.unregister_class(WorldLoader)
	bpy.types.TOPBAR_MT_file_import.remove(WorldLoader.menu_func_import)

	bpy.utils.unregister_class(WorldExporter)
	bpy.types.TOPBAR_MT_file_export.remove(WorldExporter.menu_func_export)

# detect file type
def DetectFileType(file, game_code):
	_=ReadRaw(file, "I")[0]
	file.seek(0)
	if _ & 0xFFFFFC00!=0:
		return GameCode.FEAR2.name
	else:
		return game_code

# camera util
def SetCamera():
	# massively increase camera clipping because 1000m is not enough for even a normal sized room
	for area in bpy.context.screen.areas:
		if area.type=="VIEW_3D":
			for space in area.spaces:
				if space.type=="VIEW_3D":
					space.overlay.normals_length=25.0 # FIXME: remove this later!
					space.shading.show_backface_culling=True

					if space.clip_end<10000.0:
						space.clip_end=100000.0

### Header Section

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

		self.render_section, self.sector_section, self.object_section, self.unk_section=ReadRaw(file, "4I")

		self.bounds_min=ReadVector(file)
		self.bounds_max=ReadVector(file)
		self.world_offset=ReadVector(file)