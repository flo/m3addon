#!/usr/bin/python3
# -*- coding: utf-8 -*-

# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

bl_info = {
    "name": "Importer and exporter for Blizzard's Starcraft 2 model files (*.m3)",
    'author': 'Florian Köberle',
    "location": "Properties Editor -> Scene -> M3 Panels",
    "description": "Allows to export (and import) simple Starcraft 2 models (.m3) with particle systems. Use on own risk!",
    "category": "Import-Export"
}

if "bpy" in locals():
    import imp
    if "m3import" in locals():
            imp.reload(m3import)
            
    if "m3export" in locals():
            imp.reload(m3export)
            
    if "shared" in locals():
        imp.reload(shared)

from . import shared
import bpy

from bpy.props import StringProperty
from bpy_extras.io_utils import ExportHelper, ImportHelper


def boneNameSet():
    boneNames = set()
    for armature in bpy.data.armatures:
        for bone in armature.bones:
            boneNames.add(bone.name)
        for bone in armature.edit_bones:
            boneNames.add(bone.name)
    return boneNames

def availableBones(self, context):
    sortedBoneNames = []
    sortedBoneNames.extend(boneNameSet())
    sortedBoneNames.sort()
    list = [("", "None", "Not assigned to a bone")]
    
    for boneName in sortedBoneNames:
        list.append((boneName,boneName,boneName))
    return list

def availableMaterials(self, context):
    list = [("", "None", "No Material")]
    for material in context.scene.m3_materials:
        list.append((material.name, material.name, material.name))
    return list

def handleTypeOrBoneSuffixChange(self, context):
    typeName = "Unknown"
    for typeId, name, description in particleTypeList:
        if typeId == self.type:
            typeName = name
    
    boneSuffix = self.boneSuffix
    self.name = "%s (%s)" % (boneSuffix, typeName)


def handleAnimationSequenceIndexChange(self, context):
    scene = self
    newIndex = scene.m3_animation_index
    oldIndex = scene.m3_animation_old_index
    shared.setAnimationWithIndexToCurrentData(scene, oldIndex)
    if (newIndex >= 0) and (newIndex < len(scene.m3_animations)):
        animation = scene.m3_animations[newIndex]
        scene.frame_start = animation.startFrame
        scene.frame_end = animation.endFrame
        newObjectNameToActionMap = {}
        newSceneAction = None
        for assignedAction in animation.assignedActions:
            action = bpy.data.actions.get(assignedAction.actionName)
            if action == None:
                print("Warning: The action %s was referenced by name but does no longer exist" % assignedAction.actionName)
            else:
                if action.id_root == 'OBJECT':
                    newObjectNameToActionMap[assignedAction.targetName] = action                
                elif action.id_root == 'SCENE':
                    newSceneAction = action
        for targetObject in bpy.data.objects:
            targetObject.animation_data_clear()
            newAction = newObjectNameToActionMap.get(targetObject.name)
            if newAction != None:
                targetObject.animation_data_create()
                targetObject.animation_data.action = newAction
        scene.animation_data_clear()
        if newSceneAction != None:
            scene.animation_data_create()
            scene.animation_data.action = newSceneAction
                
    scene.m3_animation_old_index = newIndex

particleTypeList =  [("0", "Point", "Particles spawn at a certain point"), 
                        ("1", 'Plane', "Particles move on a plane which is always rotated to camera"), 
                        ("2", 'Sphere', 'Particles spawn on a sphere and move outwards or to it\'s center'),
                        ("3", 'Unknown', 'It\'s unknown what kind of particle system this is'),
                        ("4", 'Cylinder', 'Particles spawn in a cylinder like area')
                        ]
matDefaultSettingsList = [("MESH", "Mesh Material", "A material for meshes"), 
                        ("PARTICLE", 'Particle Material', "Material for particle systems")
                        ]
                        
matBlendModeList = [("0", "Opaque", "no description yet"), 
                        ("1", 'Alpha Blend', "no description yet"), 
                        ("2", 'Add', 'no description yet'),
                        ("3", 'Alpha Add', 'no description yet'),
                        ("4", 'Mod', 'no description yet'),
                        ("5", 'Mod 2x', 'no description yet')
                        ]

matLayerAndEmisBlendModeList = [("0", "Mod", "no description yet"), 
                        ("1", 'Mod 2x', "no description yet"), 
                        ("2", 'Add', 'no description yet'),
                        ("3", 'Blend', 'no description yet'),
                        ("4", 'Team Color Emissive Add', 'no description yet'),
                        ("5", 'Team Color Diffuse Add', 'no description yet')
                        ]

matSpecularTypeList = [("0", "RGB", "no description yet"), 
                        ("1", 'Alpha Only', "no description yet")
                        ]


class AssignedActionOfM3Animation(bpy.types.PropertyGroup):
    targetName = bpy.props.StringProperty(name="targetName", options=set())
    actionName = bpy.props.StringProperty(name="actionName", options=set())
    
class M3Animation(bpy.types.PropertyGroup):
    name = bpy.props.StringProperty(name="name", default="Stand", options=set())
    startFrame = bpy.props.IntProperty(subtype="UNSIGNED",options=set())
    endFrame = bpy.props.IntProperty(subtype="UNSIGNED",options=set())
    assignedActions = bpy.props.CollectionProperty(type=AssignedActionOfM3Animation, options=set())
    movementSpeed = bpy.props.FloatProperty(name="mov. speed", options=set())
    frequency = bpy.props.IntProperty(subtype="UNSIGNED",options=set())
    notLooping = bpy.props.BoolProperty(options=set())
    alwaysGlobal = bpy.props.BoolProperty(options=set())
    globalInPreviewer = bpy.props.BoolProperty(options=set())

class M3MaterialLayer(bpy.types.PropertyGroup):
    name = bpy.props.StringProperty(options={"SKIP_SAVE"}, default="Material Layer")
    imagePath = bpy.props.StringProperty(name="image path", default="", options=set())
    color = bpy.props.FloatVectorProperty(name="color", size=4, subtype="COLOR", options={"ANIMATABLE"})
    textureWrapX = bpy.props.BoolProperty(options=set(), default=True)
    textureWrapY = bpy.props.BoolProperty(options=set(), default=True)
    colorEnabled = bpy.props.BoolProperty(options=set(), default=False)
    uvChannel = bpy.props.IntProperty(subtype="UNSIGNED",options=set())
    brightMult = bpy.props.FloatProperty(name="bright. mult.",options={"ANIMATABLE"}, default=1.0)
    brightMult2 = bpy.props.FloatProperty(name="bright. mult. 2",options={"ANIMATABLE"})
    brightness = bpy.props.FloatProperty(name="brightness", options={"ANIMATABLE"}, default=1.0)
    alphaAsTeamColor = bpy.props.BoolProperty(options=set())
    alphaOnly = bpy.props.BoolProperty(options=set())
    alphaBasedShading = bpy.props.BoolProperty(options=set())

class M3Material(bpy.types.PropertyGroup):
    name = bpy.props.StringProperty(name="name", default="Material", options=set())
    layers = bpy.props.CollectionProperty(type=M3MaterialLayer, options=set())
    blendMode = bpy.props.EnumProperty(items=matBlendModeList, options=set(), default="0")
    priority = bpy.props.IntProperty(options=set())
    specularity = bpy.props.FloatProperty(name="specularity", options=set())
    specMult = bpy.props.FloatProperty(name="spec. mult.", options=set(), default=1.0)
    emisMult = bpy.props.FloatProperty(name="emis. mult.", options=set(), default=1.0)
    layerBlendType = bpy.props.EnumProperty(items=matLayerAndEmisBlendModeList, options=set(), default="2")
    emisBlendType = bpy.props.EnumProperty(items=matLayerAndEmisBlendModeList, options=set(), default="3")
    specType = bpy.props.EnumProperty(items=matSpecularTypeList, options=set(), default="0")
    unfogged = bpy.props.BoolProperty(options=set(), default=True)
    twoSided = bpy.props.BoolProperty(options=set(), default=False)
    unshaded = bpy.props.BoolProperty(options=set(), default=False)
    noShadowsCast = bpy.props.BoolProperty(options=set(), default=False)
    noHitTest = bpy.props.BoolProperty(options=set(), default=False)
    noShadowsReceived = bpy.props.BoolProperty(options=set(), default=False)
    depthPrepass = bpy.props.BoolProperty(options=set(), default=False)
    useTerrainHDR = bpy.props.BoolProperty(options=set(), default=False)
    splatUVfix = bpy.props.BoolProperty(options=set(), default=False)
    softBlending = bpy.props.BoolProperty(options=set(), default=False)
    forParticles = bpy.props.BoolProperty(options=set(), default=False)
    unknownFlag0x1 = bpy.props.BoolProperty(options=set(), description="Should be true for particle system materials", default=False)
    unknownFlag0x4 = bpy.props.BoolProperty(options=set(), description="Makes mesh materials turn black but should be set for particle systems", default=False)
    unknownFlag0x8 = bpy.props.BoolProperty(options=set(), description="Should be true for particle system materials", default=False)
    unknownFlag0x200 = bpy.props.BoolProperty(options=set())

class M3ParticleSystem(bpy.types.PropertyGroup):

    # name attribute seems to be needed for template_list but is not actually in the m3 file
    # The name gets calculated like this: name = boneSuffix (type)
    name = bpy.props.StringProperty(options={"SKIP_SAVE"})
    boneSuffix = bpy.props.StringProperty(options=set(), update=handleTypeOrBoneSuffixChange, default="Particle System")
    type = bpy.props.EnumProperty(default="2", items=particleTypeList, update=handleTypeOrBoneSuffixChange, options=set())
    materialName = bpy.props.EnumProperty(items=availableMaterials, options=set())
    maxParticles = bpy.props.IntProperty(default=20, subtype="UNSIGNED",options=set())
    initEmissSpeed = bpy.props.FloatProperty(name="init. emiss. speed",options={"ANIMATABLE"}, default=0.0, description="The initial speed of the particles at emission.")
    speedVar = bpy.props.FloatProperty(default=1.0, name="speed var",options={"ANIMATABLE"})
    speedVarEnabled = bpy.props.BoolProperty(options=set(),default=False)
    angleY = bpy.props.FloatProperty(default=0.0, name="angleY", options={"ANIMATABLE"})
    angleX = bpy.props.FloatProperty(default=0.0, name="angleX", options={"ANIMATABLE"})
    speedX = bpy.props.FloatProperty(default=0.0, name="speedX", options={"ANIMATABLE"})
    speedY = bpy.props.FloatProperty(default=0.0, name="speedY", options={"ANIMATABLE"})
    lifespan = bpy.props.FloatProperty(default=0.5, name="lifespan", options={"ANIMATABLE"})
    decay = bpy.props.FloatProperty(default=5.0, name="decay", options={"ANIMATABLE"})
    decayEnabled = bpy.props.BoolProperty(default=True, name="decayEnabled", options=set())
    emissSpeed2 = bpy.props.FloatProperty(default=0.0, name="emiss. speed 2",options=set())
    scaleRatio = bpy.props.FloatProperty(default=1.0, name="scale ratio",options=set())
    unknownFloat1a = bpy.props.FloatProperty(default=1.0, name="unknownFloat1a",options=set())
    unknownFloat1b = bpy.props.FloatProperty(default=0.5, name="unknownFloat1b",options=set())
    unknownFloat1c = bpy.props.FloatProperty(default=1.0, name="unknownFloat1c",options=set())
    pemitScale = bpy.props.FloatVectorProperty(default=(1.0, 1.0, 1.0), name="pemit scale", size=3, subtype="XYZ", options={"ANIMATABLE"})
    speedUnk1 = bpy.props.FloatVectorProperty(default=(0.0, 0.0, 0.0), name="speedUnk1", size=3, subtype="XYZ", options={"ANIMATABLE"})
    color1a = bpy.props.FloatVectorProperty(default=(1.0, 1.0, 1.0, 0.5), name="color1a", size=4, subtype="COLOR", options={"ANIMATABLE"})
    color1b = bpy.props.FloatVectorProperty(default=(1.0, 1.0, 1.0, 0.5), name="color1b", size=4, subtype="COLOR", options={"ANIMATABLE"})
    color1c = bpy.props.FloatVectorProperty(default=(1.0, 1.0, 1.0, 0.0), name="color1c", size=4, subtype="COLOR", options={"ANIMATABLE"})
    emissSpeed3 = bpy.props.FloatProperty(default=1.0, name="emiss. speed 3",options=set())
    unknownFloat2a = bpy.props.FloatProperty(default=0.0, name="unknownFloat2a",options=set())
    unknownFloat2b = bpy.props.FloatProperty(default=1.0, name="unknownFloat2b",options=set())
    unknownFloat2c = bpy.props.FloatProperty(default=2.0, name="unknownFloat2c",options=set())
    trailingEnabled = bpy.props.BoolProperty(default=True, options=set())
    emissRate = bpy.props.FloatProperty(default=10.0, name="emiss. rate", options={"ANIMATABLE"})
    emissArea = bpy.props.FloatVectorProperty(default=(0.1, 0.1, 0.1), name="emiss. area", size=3, subtype="XYZ", options={"ANIMATABLE"})
    tailUnk1 = bpy.props.FloatVectorProperty(default=(0.05, 0.05, 0.05), name="tail unk.", size=3, subtype="XYZ", options={"ANIMATABLE"})
    pivotSpread = bpy.props.FloatProperty(default=2.0, name="pivot spread", options={"ANIMATABLE"})
    spreadUnk = bpy.props.FloatProperty(default=0.05, name="spread unk.", options={"ANIMATABLE"})
    radialEmissionEnabled = bpy.props.BoolProperty(default=False, options=set())
    pemitScale2Enabled = bpy.props.BoolProperty(default=False, options=set())
    pemitScale2 = bpy.props.FloatVectorProperty(default=(1.0, 1.0, 1.0), name="pemit scale 2", size=3, subtype="XYZ", options={"ANIMATABLE"})
    pemitRotateEnabled = bpy.props.BoolProperty(default=False, options=set())
    pemitRotate = bpy.props.FloatVectorProperty(default=(0.0, 0.0, 0.0), name="pemit rotate", size=3, subtype="XYZ", options={"ANIMATABLE"})
    color2Enabled = bpy.props.BoolProperty(default=False, options=set())
    color2a = bpy.props.FloatVectorProperty(default=(1.0, 1.0, 1.0, 0.0), name="color2a", size=4, subtype="COLOR", options={"ANIMATABLE"})
    color2b = bpy.props.FloatVectorProperty(default=(1.0, 1.0, 1.0, 1.0), name="color2b", size=4, subtype="COLOR", options={"ANIMATABLE"})
    color2c = bpy.props.FloatVectorProperty(default=(1.0, 1.0, 1.0, 1.0), name="color2c", size=4, subtype="COLOR", options={"ANIMATABLE"})
    partEmit = bpy.props.IntProperty(default=0, subtype="UNSIGNED", options={"ANIMATABLE"})
    lifespanRatio = bpy.props.FloatProperty(default=1.0, name="lifespan ratio",options=set())
    columns = bpy.props.IntProperty(default=0, subtype="UNSIGNED", name="columns", options=set())
    rows = bpy.props.IntProperty(default=0, subtype="UNSIGNED", name="rows", options=set())
    sort = bpy.props.BoolProperty(options=set())
    collideTerrain = bpy.props.BoolProperty(options=set())
    collideObjects = bpy.props.BoolProperty(options=set())
    spawnOnBounce = bpy.props.BoolProperty(options=set())
    useInnerShape = bpy.props.BoolProperty(options=set())
    inheritEmissionParams = bpy.props.BoolProperty(options=set())
    inheritParentVel = bpy.props.BoolProperty(options=set())
    sortByZHeight = bpy.props.BoolProperty(options=set())
    reverseIteration = bpy.props.BoolProperty(options=set())
    smoothRotation = bpy.props.BoolProperty(options=set())
    bezSmoothRotation = bpy.props.BoolProperty(options=set())
    smoothSize = bpy.props.BoolProperty(options=set())
    bezSmoothSize = bpy.props.BoolProperty(options=set())
    smoothColor = bpy.props.BoolProperty(options=set())
    bezSmoothColor = bpy.props.BoolProperty(options=set())
    litParts = bpy.props.BoolProperty(options=set())
    randFlipBookStart = bpy.props.BoolProperty(options=set())
    multiplyByGravity = bpy.props.BoolProperty(options=set())
    clampTailParts = bpy.props.BoolProperty(options=set())
    spawnTrailingParts = bpy.props.BoolProperty(options=set())
    fixLengthTailParts = bpy.props.BoolProperty(options=set())
    useVertexAlpha = bpy.props.BoolProperty(options=set())
    modelParts = bpy.props.BoolProperty(options=set())
    swapYZonModelParts = bpy.props.BoolProperty(options=set())
    scaleTimeByParent = bpy.props.BoolProperty(options=set())
    useLocalTime = bpy.props.BoolProperty(options=set())
    simulateOnInit = bpy.props.BoolProperty(options=set())
    copy = bpy.props.BoolProperty(options=set())
    
    
class M3AttachmentPoint(bpy.types.PropertyGroup):
    name = bpy.props.StringProperty(name="name", default="Attachment", options=set())
    boneName = bpy.props.EnumProperty(items=availableBones, options=set())
    
class M3ExportOptions(bpy.types.PropertyGroup):
    path = bpy.props.StringProperty(name="path", default="ExportedModel.m3", options=set())

class ExportPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_M3_quickExport"
    bl_label = "M3 Quick Export"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.prop(scene.m3_export_options,"path", text="")
        layout.operator("m3.quick_export", text="Export As M3")

class AnimationSequencesPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_M3_animations"
    bl_label = "M3 Animation Sequences"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        row = layout.row()
        col = row.column()
        col.template_list(scene, "m3_animations", scene, "m3_animation_index", rows=2)

        col = row.column(align=True)
        col.operator("m3.animations_add", icon='ZOOMIN', text="")
        col.operator("m3.animations_remove", icon='ZOOMOUT', text="")
        animationIndex = scene.m3_animation_index
        if animationIndex >= 0 and animationIndex < len(scene.m3_animations):
            animation = scene.m3_animations[animationIndex]
            layout.separator()
            layout.prop(animation, 'name', text="Name")
            layout.prop(animation, 'movementSpeed', text="Mov. Speed")
            layout.prop(animation, 'frequency', text="Frequency")
            layout.prop(animation, 'notLooping', text="Doesn't Loop")
            layout.prop(animation, 'alwaysGlobal', text="Always Global")
            layout.prop(animation, 'globalInPreviewer', text="Global In Previewer")


class MaterialsPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_M3_materials"
    bl_label = "M3 Materials"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        row = layout.row()
        col = row.column()
        col.template_list(scene, "m3_materials", scene, "m3_material_index", rows=2)

        col = row.column(align=True)
        col.operator("m3.materials_add", icon='ZOOMIN', text="")
        col.operator("m3.materials_remove", icon='ZOOMOUT', text="")

        materialIndex = scene.m3_material_index
        if materialIndex >= 0 and materialIndex < len(scene.m3_materials):
            material = scene.m3_materials[materialIndex]
            layout.separator()
            layout.prop(material, 'name', text="Name")
            layout.prop(material, 'blendMode', text="Blend Mode")
            layout.prop(material, 'priority', text="Priority")
            layout.prop(material, 'specularity', text="Specularity")
            layout.prop(material, 'specMult', text="Spec. Mult.")
            layout.prop(material, 'emisMult', text="Emis. Mult.")
            layout.prop(material, 'layerBlendType', text="Layer Blend Type")
            layout.prop(material, 'emisBlendType', text="Emis. Blend Type")
            layout.prop(material, 'specType', text="Spec. Type")
            layout.prop(material, 'unknownFlag0x1', text="unknownFlag0x1")
            layout.prop(material, 'unknownFlag0x4', text="unknownFlag0x4")
            layout.prop(material, 'unknownFlag0x8', text="unknownFlag0x8")
            layout.prop(material, 'unknownFlag0x200', text="unknownFlag0x200")
            layout.prop(material, 'unfogged', text="Unfogged")
            layout.prop(material, 'twoSided', text="Two Sided")
            layout.prop(material, 'unshaded', text="Unshaded")
            layout.prop(material, 'noShadowsCast', text="No Shadows Cast")
            layout.prop(material, 'noHitTest', text="No Hit Test")
            layout.prop(material, 'noShadowsReceived', text="No Shadows Received")
            layout.prop(material, 'depthPrepass', text="Depth Prepass")
            layout.prop(material, 'useTerrainHDR', text="Use Terrain HDR")
            layout.prop(material, 'splatUVfix', text="Splat UV Fix")
            layout.prop(material, 'softBlending', text="Soft Blending")
            layout.prop(material, 'forParticles', text="For Particles (?)")

class MatrialLayersPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_M3_material_layers"
    bl_label = "M3 Material Layers"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        row = layout.row()
        col = row.column()

        materialIndex = scene.m3_material_index
        if materialIndex >= 0 and materialIndex < len(scene.m3_materials):
            material = scene.m3_materials[materialIndex]
            col.template_list(material, "layers", scene, "m3_material_layer_index", rows=2)
            layerIndex = scene.m3_material_layer_index
            if layerIndex >= 0 and layerIndex < len(material.layers):
                layer = material.layers[layerIndex]
                layout.prop(layer, 'imagePath', text="Image Path")
                layout.prop(layer, 'textureWrapX', text="Tex. Wrap X")
                layout.prop(layer, 'textureWrapY', text="Tex. Wrap Y")
                layout.prop(layer, 'alphaAsTeamColor', text="Alpha As Team Color")
                layout.prop(layer, 'alphaOnly', text="Alpha Only")
                layout.prop(layer, 'alphaBasedShading', text="Alpha Based Shading")
                split = layout.split()
                row = split.row()
                row.prop(layer, 'colorEnabled', text="Color:")
                sub = row.column(align=True)
                sub.active = layer.colorEnabled
                sub.prop(layer, 'color', text="")
                
                split = layout.split()
                col = split.column()
                sub = col.column(align=True)
                sub.label(text="Brightness:")
                sub.prop(layer, "brightness", text="")
                sub.prop(layer, "brightMult", text="Multiplier")
                sub.prop(layer, "brightMult2", text="Multiplier 2")
                
        else:
            col.label(text="no m3 material selected")


class ParticleSystemsPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_M3_particles"
    bl_label = "M3 Particle Systems"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        row = layout.row()
        col = row.column()
        col.template_list(scene, "m3_particle_systems", scene, "m3_particle_system_index", rows=2)

        col = row.column(align=True)
        col.operator("m3.particle_systems_add", icon='ZOOMIN', text="")
        col.operator("m3.particle_systems_remove", icon='ZOOMOUT', text="")
        currentIndex = scene.m3_particle_system_index
        if currentIndex >= 0 and currentIndex < len(scene.m3_particle_systems):
            particle_system = scene.m3_particle_systems[currentIndex]
            layout.separator()
            layout.prop(particle_system, 'boneSuffix',text="Name")
            layout.prop(particle_system, 'type',text="Type")
            layout.prop(particle_system, 'materialName',text="Material")
            layout.prop(particle_system, 'maxParticles', text="Particle Maximum")
            layout.prop(particle_system, 'initEmissSpeed', text="Init. Emiss. Speed")

            split = layout.split()
            row = split.row()
            row.prop(particle_system, 'speedVarEnabled')
            sub = row.column(align=True)
            sub.active = particle_system.speedVarEnabled
            sub.prop(particle_system, 'speedVar', text="Speed Var")
            
            split = layout.split()
            col = split.column()
            sub = col.column(align=True)
            sub.label(text="Angle:")
            sub.prop(particle_system, "angleX", text="X")
            sub.prop(particle_system, "angleY", text="Y")
            col = split.column()
            sub = col.column(align=True)
            sub.label(text="Speed:")
            sub.prop(particle_system, "speedX", text="X")
            sub.prop(particle_system, "speedY", text="Y")
            
            layout.prop(particle_system, 'lifespan', text="Lifespan")
            
            split = layout.split()
            row = split.row()
            row.prop(particle_system, 'decayEnabled', text="")
            sub = row.column(align=True)
            sub.active = particle_system.decayEnabled
            sub.prop(particle_system, 'decay', text="Decay")
            
            layout.prop(particle_system, 'emissSpeed2', text="Emiss. Speed 2")
            layout.prop(particle_system, 'scaleRatio', text="Scale Ratio")
            
            split = layout.split()
            col = split.column()
            sub = col.column(align=True)
            sub.label(text="Unknown Floats 1:")
            sub.prop(particle_system, "unknownFloat1a", text="X")
            sub.prop(particle_system, "unknownFloat1b", text="Y")
            sub.prop(particle_system, "unknownFloat1c", text="Z")
            col = split.column()
            col.prop(particle_system, 'pemitScale', text="Pemit. Scale")
            split = layout.split()
            col = split.column()
            col.prop(particle_system, 'speedUnk1', text="Unknown Speed 1")
            
            split = layout.split()
            col = split.column()
            sub = col.column(align=True)
            sub.label(text="Colors:")
            sub.prop(particle_system, "color1a", text="")
            sub.prop(particle_system, "color1b", text="")
            sub.prop(particle_system, "color1c", text="")
            
            layout.prop(particle_system, 'emissSpeed3', text="Emiss. Speed 3")
            
            split = layout.split()
            col = split.column()
            sub = col.column(align=True)
            sub.label(text="Unknown Floats 2:")
            sub.prop(particle_system, "unknownFloat2a", text="X")
            sub.prop(particle_system, "unknownFloat2b", text="Y")
            sub.prop(particle_system, "unknownFloat2c", text="Z")
            
            layout.prop(particle_system, 'trailingEnabled', text="Trailing")
            
            layout.prop(particle_system, 'emissRate', text="Emiss. Rate")
            
            split = layout.split()
            col = split.column()
            col.prop(particle_system, 'emissArea', text="Emiss. Area")
            
            split = layout.split()
            col = split.column()
            col.prop(particle_system, 'tailUnk1', text="Tail Unk1")
            
            layout.prop(particle_system, 'pivotSpread', text="Pivot Spread")
            layout.prop(particle_system, 'spreadUnk', text="Spread Unk")
            layout.prop(particle_system, 'radialEmissionEnabled', text="Radial Emission")
            
            split = layout.split()
            row = split.row()
            sub = row.column(align=True)
            sub.prop(particle_system, 'pemitScale2Enabled', text="Pemit Scale 2:")
            subsub = sub.column()
            subsub.active = particle_system.pemitScale2Enabled
            subsub.prop(particle_system, 'pemitScale2', text="")
            
            split = layout.split()
            row = split.row()
            sub = row.column(align=True)
            sub.prop(particle_system, 'pemitRotateEnabled', text="Pemit Rotate:")
            subsub = sub.column()
            subsub.active = particle_system.pemitRotateEnabled
            subsub.prop(particle_system, 'pemitRotate', text="")
            
            split = layout.split()
            col = split.column()
            sub = col.column(align=True)
            sub.prop(particle_system, 'color2Enabled', text="Colors 2:")
            subsub = sub.column()
            subsub.active = particle_system.color2Enabled
            subsub.prop(particle_system, "color2a", text="")
            subsub.prop(particle_system, "color2b", text="")
            subsub.prop(particle_system, "color2c", text="")
            
            layout.prop(particle_system, 'partEmit', text="Part. Emit.")
            layout.prop(particle_system, 'lifespanRatio', text="Lifespan Ratio.")

            split = layout.split()
            row = split.row()
            row.prop(particle_system, 'columns', text="Columns")
            row.prop(particle_system, 'rows', text="Rows")
            
            layout.prop(particle_system, 'sort', text="Sort")
            layout.prop(particle_system, 'collideTerrain', text="Collide Terrain")
            layout.prop(particle_system, 'collideObjects', text="Collide Objects")
            layout.prop(particle_system, 'spawnOnBounce', text="Spawn On Bounce")
            layout.prop(particle_system, 'useInnerShape', text="Use Inner Shape")
            layout.prop(particle_system, 'inheritEmissionParams', text="Inherit Emission Params")
            layout.prop(particle_system, 'inheritParentVel', text="Inherit Parent Vel")
            layout.prop(particle_system, 'sortByZHeight', text="Sort By Z Height")
            layout.prop(particle_system, 'reverseIteration', text="Reverse Iteration")
            layout.prop(particle_system, 'smoothRotation', text="Smooth Rotation")
            layout.prop(particle_system, 'bezSmoothRotation', text="Bez Smooth Rotation")
            layout.prop(particle_system, 'smoothSize', text="Smooth Size")
            layout.prop(particle_system, 'bezSmoothSize', text="Bez Smooth Size")
            layout.prop(particle_system, 'smoothColor', text="Smooth Color")
            layout.prop(particle_system, 'litParts', text="Lit Parts")
            layout.prop(particle_system, 'randFlipBookStart', text="Rand Flip Book Start")
            layout.prop(particle_system, 'multiplyByGravity', text="Multiply By Gravity")
            layout.prop(particle_system, 'clampTailParts', text="Clamp Tail Parts")
            layout.prop(particle_system, 'spawnTrailingParts', text="Spawn Trailing Parts")
            layout.prop(particle_system, 'fixLengthTailParts', text="Fix Length Tail Parts")
            layout.prop(particle_system, 'useVertexAlpha', text="Use Vertex Alpha")
            layout.prop(particle_system, 'modelParts', text="Model Parts")
            layout.prop(particle_system, 'swapYZonModelParts', text="Swap Y Z On Model Parts")
            layout.prop(particle_system, 'scaleTimeByParent', text="Scale Time By Parent")
            layout.prop(particle_system, 'useLocalTime', text="Use Local Time")
            layout.prop(particle_system, 'simulateOnInit', text="Simulate On Init")
            layout.prop(particle_system, 'copy', text="Copy")

class AttachmentPointsPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_M3_attachments"
    bl_label = "M3 Attachment Points"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        row = layout.row()
        col = row.column()
        col.template_list(scene, "m3_attachment_points", scene, "m3_attachment_point_index", rows=2)

        col = row.column(align=True)
        col.operator("m3.attachment_points_add", icon='ZOOMIN', text="")
        col.operator("m3.attachment_points_remove", icon='ZOOMOUT', text="")

        currentIndex = scene.m3_attachment_point_index
        if currentIndex >= 0 and currentIndex < len(scene.m3_attachment_points):
            attachment_point = scene.m3_attachment_points[currentIndex]
            layout.separator()
            layout.prop(attachment_point, 'boneName', text="Bone")
            layout.prop(attachment_point, 'name', text="Name")

class M3_MATERIALS_OT_add(bpy.types.Operator):
    bl_idname      = 'm3.materials_add'
    bl_label       = "Add M3 Material"
    bl_description = "Adds an material for the export to Starcraft 2"
    
    defaultSetting = bpy.props.EnumProperty(items=matDefaultSettingsList, options=set(), default="MESH")
    name = bpy.props.StringProperty(name="name", default="Stand", options=set())
    
    def invoke(self, context, event):
        scene = context.scene
        self.name = self.findUnusedName(scene)
        context.window_manager.invoke_props_dialog(self, width=250)
        return {'RUNNING_MODAL'}  
        
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "defaultSetting", text="Default Settings") 
        layout.prop(self, "name", text="Name") 
  
    def execute(self, context):
        scene = context.scene
        defaultSettingParticle = "PARTICLE"
        material = scene.m3_materials.add()
        material.name = self.name
        for (layerName, layerFieldName) in zip(shared.materialLayerNames, shared.materialLayerFieldNames):
            layer = material.layers.add()
            layer.name = layerName
            if layerFieldName == "diffuseLayer":
                if self.defaultSetting != defaultSettingParticle:
                    layer.alphaAsTeamColor = True
            if layerFieldName == "evioMaskLayer":
                layer.alphaOnly = True
            elif layerFieldName in ["alphaMaskLayer", "layer12", "layer13"]:
                layer.textureWrapX = False
                layer.textureWrapY = False
                layer.alphaAsTeamColor = True
            elif layerFieldName == "heightLayer":
                layer.textureWrapX = False
                layer.textureWrapY = False
                layer.alphaOnly = True
        
        if self.defaultSetting == defaultSettingParticle:
            material.unfogged = True
            material.blendMode = "2"
            material.layerBlendType = "2"
            material.emisBlendType = "2"
            material.noShadowsCast = True
            material.noHitTest = True
            material.noShadowsReceived = True
            material.forParticles = True
            material.unknownFlag0x1 = True
            material.unknownFlag0x2 = True
            material.unknownFlag0x8 = True
         
        scene.m3_material_index = len(scene.m3_materials)-1
        return {'FINISHED'}
    def findUnusedName(self, scene):
        usedNames = set()
        for material in scene.m3_materials:
            usedNames.add(material.name)
        unusedName = None
        counter = 1
        while unusedName == None:
            suggestedName = "%02d" % counter
            if not suggestedName in usedNames:
                unusedName = suggestedName
            counter += 1
        return unusedName

class M3_MATERIALSS_OT_remove(bpy.types.Operator):
    bl_idname      = 'm3.materials_remove'
    bl_label       = "Remove M3 Material"
    bl_description = "Removes the active M3 Material"
    
    def invoke(self, context, event):
        scene = context.scene
        if scene.m3_material_index >= 0:
            scene.m3_materials.remove(scene.m3_material_index)
            scene.m3_material_index -= 1
        return{'FINISHED'}

class M3_ANIMATIONS_OT_add(bpy.types.Operator):
    bl_idname      = 'm3.animations_add'
    bl_label       = "Add Animation Sequence"
    bl_description = "Adds an animation sequence for the export to Starcraft 2"

    def invoke(self, context, event):
        scene = context.scene
        animation = scene.m3_animations.add()
        name = self.findUnusedName(scene)
        animation.name = name
        animation.startFrame = 0
        animation.endFrame = 100
        animation.frequency = 1
        animation.movementSpeed = 0.0
        scene.m3_animation_index = len(scene.m3_animations)-1
        return{'FINISHED'}
        
    def findUnusedName(self, scene):
        usedNames = set()
        for animation in scene.m3_animations:
            usedNames.add(animation.name)
        suggestedNames = ["Birth", "Stand", "Death", "Walk", "Attack"]
        unusedName = None
        for suggestedName in suggestedNames:
            if not suggestedName in usedNames:
                unusedName = suggestedName
                break
        counter = 1
        while unusedName == None:
            suggestedName = "Stand %02d" % counter
            if not suggestedName in usedNames:
                unusedName = suggestedName
            counter += 1
        return unusedName
        
class M3_ANIMATIONS_OT_remove(bpy.types.Operator):
    bl_idname      = 'm3.animations_remove'
    bl_label       = "Remove Animation Sequence"
    bl_description = "Removes the active M3 animation sequence"
    
    def invoke(self, context, event):
        scene = context.scene
        if scene.m3_animation_index >= 0:
                scene.m3_animations.remove(scene.m3_animation_index)
                scene.m3_animation_old_index = -1
                scene.m3_animation_index -= 1
        return{'FINISHED'}

class M3_PARTICLE_SYSTEMS_OT_add(bpy.types.Operator):
    bl_idname      = 'm3.particle_systems_add'
    bl_label       = "Add Particle System"
    bl_description = "Adds a particle system for the export to the m3 model format"

    def invoke(self, context, event):
        scene = context.scene
        particle_system = scene.m3_particle_systems.add()
        particle_system.boneSuffix = self.findUnusedName(scene)
        if len(scene.m3_materials) >= 1:
            particle_system.materialName = scene.m3_materials[0].name

        handleTypeOrBoneSuffixChange(particle_system, context)
        scene.m3_particle_system_index = len(scene.m3_particle_systems)-1
        return{'FINISHED'}
        
    def findUnusedName(self, scene):
        usedNames = set()
        for particle_system in scene.m3_particle_systems:
            usedNames.add(particle_system.name)
        unusedName = None
        counter = 1
        while unusedName == None:
            suggestedName = "%02d" % counter
            if not suggestedName in usedNames:
                unusedName = suggestedName
            counter += 1
        return unusedName

class M3_PARTICLE_SYSTEMS_OT_remove(bpy.types.Operator):
    bl_idname      = 'm3.particle_systems_remove'
    bl_label       = "Remove Particle System"
    bl_description = "Removes the active M3 particle system"
    
    def invoke(self, context, event):
        scene = context.scene
        if scene.m3_particle_system_index >= 0:
                scene.m3_particle_systems.remove(scene.m3_particle_system_index)
                scene.m3_particle_system_index-= 1
        return{'FINISHED'}
        

        
        
class M3_ATTACHMENT_POINTS_OT_add(bpy.types.Operator):
    bl_idname      = 'm3.attachment_points_add'
    bl_label       = "Add Attachment Point"
    bl_description = "Adds an attachment point for the export to Starcraft 2"

    def invoke(self, context, event):
        scene = context.scene
        attachment_point = scene.m3_attachment_points.add()
        name = self.findUnusedName(scene)
        attachment_point.name = name
        boneNames = boneNameSet()
        if name in boneNames:
            attachment_point.boneName = name

        scene.m3_attachment_point_index = len(scene.m3_attachment_points)-1
        return{'FINISHED'}
        
    def findUnusedName(self, scene):
        usedNames = set()
        for attachment_point in scene.m3_attachment_points:
            usedNames.add(attachment_point.name)
        suggestedNames = ["Ref_Center", "Ref_Origin", "Ref_Overhead", "Ref_Target"]
        unusedName = None
        for suggestedName in suggestedNames:
            if not suggestedName in usedNames:
                unusedName = suggestedName
                break
        counter = 1
        while unusedName == None:
            suggestedName = "Attachment " + str(counter)
            if not suggestedName in usedNames:
                unusedName = suggestedName
            counter += 1
        return unusedName
        

class M3_ATTACHMENT_POINTS_OT_remove(bpy.types.Operator):
    bl_idname      = 'm3.attachment_points_remove'
    bl_label       = "Remove Attachment Point"
    bl_description = "Removes the active M3 attachment point"
    
    def invoke(self, context, event):
        scene = context.scene
        if scene.m3_attachment_point_index >= 0:
                scene.m3_attachment_points.remove(scene.m3_attachment_point_index)
                scene.m3_attachment_point_index-= 1
        return{'FINISHED'}
        
class M3_OT_quickExport(bpy.types.Operator):
    bl_idname      = 'm3.quick_export'
    bl_label       = "Quick Export"
    bl_description = "Exports the model to the specified m3 path without asking further questions"
    
    def invoke(self, context, event):
        scene = context.scene
        fileName = scene.m3_export_options.path
        if not "m3export" in locals():
            from . import m3export
        m3export.exportParticleSystems(scene, fileName)
        return{'FINISHED'}

class M3_OT_export(bpy.types.Operator, ExportHelper):
    '''Export a M3 file'''
    bl_idname = "m3.export"
    bl_label = "Export M3 Particle Systems"
    bl_options = {'UNDO'}

    filename_ext = ".m3"
    filter_glob = StringProperty(default="*.m3", options={'HIDDEN'})

    filepath = bpy.props.StringProperty(
        name="File Path", 
        description="Path of the file that should be created", 
        maxlen= 1024, default= "")

    def execute(self, context):
        print("Export", self.properties.filepath)
        scene = context.scene
        if not "m3export" in locals():
            from . import m3export

        m3export.exportParticleSystems(scene, self.properties.filepath)
        return {'FINISHED'}
            
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class M3_OT_import(bpy.types.Operator, ImportHelper):
    '''Load a M3 file'''
    bl_idname = "m3.import"
    bl_label = "Import M3"
    bl_options = {'UNDO'}

    filename_ext = ".m3"
    filter_glob = StringProperty(default="*.m3", options={'HIDDEN'})

    filepath = bpy.props.StringProperty(
        name="File Path", 
        description="File path used for importing the simple M3 file", 
        maxlen= 1024, default= "")

    def execute(self, context):
        print("Load", self.properties.filepath)
        if not "m3import" in locals():
            from . import m3import
        m3import.importFile(self.properties.filepath)
        return {'FINISHED'}
            
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

        

def menu_func_import(self, context):
    self.layout.operator(M3_OT_import.bl_idname, text="Starcraft 2 Model (.m3)...")
    
def menu_func_export(self, context):
    self.layout.operator(M3_OT_export.bl_idname, text="Starcraft 2 Model (.m3)...")
 
def register():
    bpy.utils.register_module(__name__)

    bpy.types.Scene.m3_animation_index = bpy.props.IntProperty(update=handleAnimationSequenceIndexChange)
    bpy.types.Scene.m3_animation_old_index = bpy.props.IntProperty()
    bpy.types.Scene.m3_animations = bpy.props.CollectionProperty(type=M3Animation)
    bpy.types.Scene.m3_material_layer_index = bpy.props.IntProperty()
    bpy.types.Scene.m3_materials = bpy.props.CollectionProperty(type=M3Material)
    bpy.types.Scene.m3_material_index = bpy.props.IntProperty()
    bpy.types.Scene.m3_particle_systems = bpy.props.CollectionProperty(type=M3ParticleSystem)
    bpy.types.Scene.m3_particle_system_index = bpy.props.IntProperty()
    bpy.types.Scene.m3_attachment_points = bpy.props.CollectionProperty(type=M3AttachmentPoint)
    bpy.types.Scene.m3_attachment_point_index = bpy.props.IntProperty()
    bpy.types.Scene.m3_export_options = bpy.props.PointerProperty(type=M3ExportOptions)

    bpy.types.INFO_MT_file_import.append(menu_func_import)
    bpy.types.INFO_MT_file_export.append(menu_func_export)
 
def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.INFO_MT_file_import.remove(menu_func_import)
    bpy.types.INFO_MT_file_export.remove(menu_func_export)
 
if __name__ == "__main__":
    register()