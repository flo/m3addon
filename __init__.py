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
    for material in context.scene.m3_material_references:
        list.append((material.name, material.name, material.name))
    return list

def handleTypeOrBoneSuffixChange(self, context):
    scene = context.scene
    typeName = "Unknown"
    for typeId, name, description in particleTypeList:
        if typeId == self.emissionAreaType:
            typeName = name
    
    boneSuffix = self.boneSuffix
    self.name = "%s (%s)" % (boneSuffix, typeName)

    if self.boneSuffix != self.oldBoneSuffix:
        oldBoneName = shared.boneNameForPartileSystem(self.oldBoneSuffix)
        newBoneName = shared.boneNameForPartileSystem(self.boneSuffix)
        bone, armatureObject = findBoneWithArmatureObject(scene, oldBoneName)
        if bone != None:
            bone.name = newBoneName
    self.oldBoneSuffix = self.boneSuffix

def handleMaterialNameChange(self, context):
    scene = context.scene
    materialName = self.name
    materialReferenceIndex = self.materialReferenceIndex
    if materialReferenceIndex != -1:
        materialReference = scene.m3_material_references[self.materialReferenceIndex]
        materialIndex = materialReference.materialIndex
        materialType = materialReference.materialType
        label = shared.calculateMaterialLabel(materialName, materialType)
        materialReference.name = label
    
def handleAttachmentVolumeTypeChange(self, context):
    if self.volumeType in ["0", "1", "2"]:
       if self.volumeSize0 == 0.0:
            self.volumeSize0 = 1.0
    else:
        self.volumeSize0 = 0.0

    if self.volumeType in ["0", "2"]:
        if self.volumeSize1 == 0.0:
            self.volumeSize1 = 1.0
    else:
        self.volumeSize1 = 0.0

    if self.volumeType in ["0"]:
        if self.volumeSize2 == 0.0:
            self.volumeSize2 = 1.0
    else:
        self.volumeSize2 = 0.0

def handleAnimationSequenceIndexChange(self, context):
    scene = self
    newIndex = scene.m3_animation_index
    oldIndex = scene.m3_animation_old_index
    shared.setAnimationWithIndexToCurrentData(scene, oldIndex)
    if (newIndex >= 0) and (newIndex < len(scene.m3_animations)):
        animation = scene.m3_animations[newIndex]
        scene.frame_start = animation.startFrame
        scene.frame_end = animation.exlusiveEndFrame - 1
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
        for targetObject in scene.objects:
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

def handlePartileSystemIndexChanged(self, context):
    scene = context.scene
    partileSystem = scene.m3_particle_systems[scene.m3_particle_system_index]
    selectOrCreateBoneForPartileSystem(scene, partileSystem)

def iterateArmatureObjects(scene):
    for obj in scene.objects:
        if obj.type == "ARMATURE":
            if obj.data != None:
                yield obj

def findArmatureObjectForNewBone(scene):
    for obj in iterateArmatureObjects(scene):
        return obj
    return None

def findBoneWithArmatureObject(scene, boneName):
    for armatureObject in iterateArmatureObjects(scene):
        armature = armatureObject.data
        for bone in armature.bones:
            if bone.name == boneName:
                return (bone, armatureObject)
    return (None, None)

def selectOrCreateBoneForPartileSystem(scene, particle_system):
        boneName = shared.boneNameForPartileSystem(particle_system.boneSuffix)
        if bpy.ops.object.mode_set.poll():
           bpy.ops.object.mode_set(mode='OBJECT')
        if bpy.ops.object.select_all.poll():
           bpy.ops.object.select_all(action='DESELECT')
        bone, armatureObject = findBoneWithArmatureObject(scene, boneName)
        boneExists = bone != None
        if boneExists:
            armature = armatureObject.data
            armatureObject.select = True
            scene.objects.active = armatureObject
            if bpy.ops.object.mode_set.poll():
                bpy.ops.object.mode_set(mode='POSE')
        else:
            armatureObject = findArmatureObjectForNewBone(scene)
            if armatureObject == None:
                armature = bpy.data.armatures.new(name="Armature")
                armatureObject = bpy.data.objects.new("Armature", armature)
                scene.objects.link(armatureObject)
            else:
                armature = armatureObject.data
            armatureObject.select = True
            scene.objects.active = armatureObject
            bpy.ops.object.mode_set(mode='EDIT')
            editBone = armature.edit_bones.new(boneName)
            editBone.head = (0, 0, 0)
            editBone.tail = (1, 0, 0)
            bpy.ops.object.mode_set(mode='POSE')
            bone = armature.bones[boneName]
        scene.objects.active = armatureObject
        armatureObject.select = True
        for currentBone in armature.bones:
            currentBone.select = False
        bone.select = True
    
particleTypesWithRadius = ["2", "4"]
particleTypesWithWidth = ["1", "3"]
particleTypesWithLength = ["1", "3"]
particleTypesWithHeight = ["3", "4"]
particleTypeList =  [("0", "Point", "Particles spawn at a certain point"), 
                        ("1", 'Plane', "Particles spawn in a rectangle"), 
                        ("2", 'Sphere', 'Particles spawn in a sphere'),
                        ("3", 'Cuboid', 'Particles spawn in a cuboid'),
                        ("4", 'Cylinder', 'Particles spawn in a cylinder')
                        ]

uvSourceList = [("0", "Default", "First UV layer of mesh or generated whole image UVs for particles"),
                 ("1", "UV Layer 2", "Second UV layer which can be used for decals"),
                 ("2", "UV Layer 2", "Third UV layer"),
                 ("3", "UV Layer 4", "Fourth UV layer?"),
                 ("4", "Unknown (value 4)", "Unknown"),
                 ("5", "Unknown (value 5)", "Unknown"),
                 ("6", "Animated Particle UV", "The texture gets divided as specified by the particle system to create multiple small image frames which play then as an animation"),
                 ("7", "Unknown (value 7)", "Unknown"),
                 ("8", "Unknown (value 8)", "Unknown"),
                 ("9", "Unknown (value 9)", "Unknown"),
                 ("10", "Unknown (value 9)", "Unknown")
                 ] 

particleEmissionTypeList = [("0", "Directed", "Emitted particles fly towards a configureable direction with a configurable spread"), 
                        ("1", 'Radial', "Particles move into all kinds of directions"), 
                        ("2", 'Unknown', 'Particles spawn in a sphere')]
attachmentVolumeTypeList = [("-1", "None", "No Volume, it's a simple attachment point"), 
                            ("0", 'Cuboid', "Volume with the shape of a cuboid with the given width, length and height"),
                            ("1", 'Sphere', "Volume with the shape of a sphere with the given radius"), 
                            ("2", 'Cylinder', 'Volume with the shape of a cylinder with the given radius and height'),
                            ("3", 'Unknown 3', 'Unknown Volume with id 3'),
                            ("4", 'Unknown 4', 'Unknown Volume with id 4')
                           ] 
    
matDefaultSettingsList = [("MESH", "Mesh Standard Material", "A material for meshes"), 
                        ("PARTICLE", 'Particle Standard Material', "Material for particle systems")
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
class M3AnimIdData(bpy.types.PropertyGroup):
    # animId is actually an unsigned integer but blender can store only signed ones
    # thats why the number range needs to be moved into the negative for storage
    animIdMinus2147483648 = bpy.props.IntProperty(name="animId", options=set())
    animPath = bpy.props.StringProperty(name="animPath", options=set())
    objectId =  bpy.props.StringProperty(name="objectId", options=set())

class AssignedActionOfM3Animation(bpy.types.PropertyGroup):
    targetName = bpy.props.StringProperty(name="targetName", options=set())
    actionName = bpy.props.StringProperty(name="actionName", options=set())
    
class M3Animation(bpy.types.PropertyGroup):
    name = bpy.props.StringProperty(name="name", default="Stand", options=set())
    startFrame = bpy.props.IntProperty(subtype="UNSIGNED",options=set())
    exlusiveEndFrame = bpy.props.IntProperty(subtype="UNSIGNED",options=set())
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
    uvSource = bpy.props.EnumProperty(items=uvSourceList, options=set(), default="0")
    brightMult = bpy.props.FloatProperty(name="bright. mult.",options={"ANIMATABLE"}, default=1.0)
    brightMult2 = bpy.props.FloatProperty(name="bright. mult. 2",options={"ANIMATABLE"})
    brightness = bpy.props.FloatProperty(name="brightness", options={"ANIMATABLE"}, default=1.0)
    alphaAsTeamColor = bpy.props.BoolProperty(options=set())
    alphaOnly = bpy.props.BoolProperty(options=set())
    alphaBasedShading = bpy.props.BoolProperty(options=set())

class M3Material(bpy.types.PropertyGroup):
    name = bpy.props.StringProperty(name="name", default="Material", options=set())
    materialType = bpy.props.IntProperty(options=set())
    materialIndex = bpy.props.IntProperty(options=set())
    
class M3StandardMaterial(bpy.types.PropertyGroup):
    name = bpy.props.StringProperty(name="name", default="Material", update=handleMaterialNameChange, options=set())
    # the following field gets used to update the name of the material reference:
    materialReferenceIndex = bpy.props.IntProperty(options=set(), default=-1)
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
    oldBoneSuffix = bpy.props.StringProperty(options={"SKIP_SAVE"})
    materialReferenceIndex = bpy.props.IntProperty(default=0, subtype="UNSIGNED",options=set())
    maxParticles = bpy.props.IntProperty(default=20, subtype="UNSIGNED",options=set())
    emissionSpeed1 = bpy.props.FloatProperty(name="emis. speed 1",options={"ANIMATABLE"}, default=0.0, description="The initial speed of the particles at emission")
    emissionSpeed2 = bpy.props.FloatProperty(default=1.0, name="emiss. speed 2",options={"ANIMATABLE"}, description="If emission speed randomization is enabled this value specfies the other end of the range of random speeds")
    randomizeWithEmissionSpeed2 = bpy.props.BoolProperty(options=set(),default=False, description="Specifies if the second emission speed value should be used to generate random emission speeds")
    emissionAngleX = bpy.props.FloatProperty(default=0.0, name="emis. angle X", subtype="ANGLE", options={"ANIMATABLE"}, description="Specifies the X rotation of the emission vector")
    emissionAngleY = bpy.props.FloatProperty(default=0.0, name="emis. angle Y", subtype="ANGLE", options={"ANIMATABLE"}, description="Specifies the Y rotation of the emission vector")
    emissionSpreadX = bpy.props.FloatProperty(default=0.0, name="emissionSpreadX", options={"ANIMATABLE"}, description="Specifies in radian by how much the emission vector can be randomly rotated around the X axis")
    emissionSpreadY = bpy.props.FloatProperty(default=0.0, name="emissionSpreadY", options={"ANIMATABLE"}, description="Specifies in radian by how much the emission vector can be randomly rotated around the Y axis")
    lifespan1 = bpy.props.FloatProperty(default=0.5, name="lifespan1", options={"ANIMATABLE"},  description="Specfies how long it takes before the particles start to decay")
    lifespan2 = bpy.props.FloatProperty(default=5.0, name="lifespan2", options={"ANIMATABLE"}, description="If random lifespans are enabled this specifies the other end of the range for random lifespan values")
    randomizeWithLifespan2 = bpy.props.BoolProperty(default=True, name="randomizeWithLifespan2", options=set(), description="Specifies if particles should have random lifespans")
    zAcceleration = bpy.props.FloatProperty(default=0.0, name="z acceleration",options=set(), description="Negative gravity which does not get influenced by the emission vector")
    unknownFloat1a = bpy.props.FloatProperty(default=1.0, name="unknownFloat1a",options=set())
    unknownFloat1b = bpy.props.FloatProperty(default=1.0, name="unknownFloat1b",options=set())
    unknownFloat1c = bpy.props.FloatProperty(default=0.5, name="unknownFloat1c",options=set())
    unknownFloat1d = bpy.props.FloatProperty(default=1.0, name="unknownFloat1d",options=set())
    particleSizes1 = bpy.props.FloatVectorProperty(default=(1.0, 1.0, 1.0), name="particle sizes 1", size=3, subtype="XYZ", options={"ANIMATABLE"}, description="The first two values are the initial and final size of particles")
    rotationValues1 = bpy.props.FloatVectorProperty(default=(0.0, 0.0, 0.0), name="rotation values 1", size=3, subtype="XYZ", options={"ANIMATABLE"}, description="The first value is the inital rotation and the second value is the rotation speed")
    initialColor1 = bpy.props.FloatVectorProperty(default=(1.0, 1.0, 1.0, 0.5), name="initial color 1", size=4, subtype="COLOR", options={"ANIMATABLE"}, description="Color of the particle when it gets emitted")
    finalColor1 = bpy.props.FloatVectorProperty(default=(1.0, 1.0, 1.0, 0.5), name="final color 1", size=4, subtype="COLOR", options={"ANIMATABLE"}, description="The color the particle will have when it vanishes")
    unknownColor1 = bpy.props.FloatVectorProperty(default=(1.0, 1.0, 1.0, 0.0), name="unknown color 1", size=4, subtype="COLOR", options={"ANIMATABLE"})
    slowdown = bpy.props.FloatProperty(default=1.0, min=0.0, name="slowdown" ,options=set(), description="The amounth of speed reduction in the particles lifetime")
    unknownFloat2a = bpy.props.FloatProperty(default=0.0, name="unknownFloat2a",options=set())
    unknownFloat2b = bpy.props.FloatProperty(default=1.0, name="unknownFloat2b",options=set())
    unknownFloat2c = bpy.props.FloatProperty(default=2.0, name="unknownFloat2c",options=set())
    trailingEnabled = bpy.props.BoolProperty(default=True, options=set(), description="If trailing is enabled then particles don't follow the particle emitter")
    emissionRate = bpy.props.FloatProperty(default=10.0, name="emiss. rate", options={"ANIMATABLE"})
    emissionAreaType = bpy.props.EnumProperty(default="2", items=particleTypeList, update=handleTypeOrBoneSuffixChange, options=set())
    emissionAreaSize = bpy.props.FloatVectorProperty(default=(0.1, 0.1, 0.1), name="emis. area size", size=3, subtype="XYZ", options={"ANIMATABLE"})
    tailUnk1 = bpy.props.FloatVectorProperty(default=(0.05, 0.05, 0.05), name="tail unk.", size=3, subtype="XYZ", options={"ANIMATABLE"})
    emissionAreaRadius = bpy.props.FloatProperty(default=2.0, name="emis. area radius", options={"ANIMATABLE"})
    spreadUnk = bpy.props.FloatProperty(default=0.05, name="spread unk.", options={"ANIMATABLE"})
    emissionType = bpy.props.EnumProperty(default="0", items=particleEmissionTypeList, options=set())
    randomizeWithParticleSizes2 = bpy.props.BoolProperty(default=False, options=set(), description="Specifies if particles have random sizes")
    particleSizes2 = bpy.props.FloatVectorProperty(default=(1.0, 1.0, 1.0), name="particle sizes 2", size=3, subtype="XYZ", options={"ANIMATABLE"}, description="The first two values are used to determine a random initial and final size for a particle")
    randomizeWithRotationValues2 = bpy.props.BoolProperty(default=False, options=set())
    rotationValues2 = bpy.props.FloatVectorProperty(default=(0.0, 0.0, 0.0), name="rotation values 2", size=3, subtype="XYZ", options={"ANIMATABLE"})
    randomizeWithColor2 = bpy.props.BoolProperty(default=False, options=set())
    initialColor2 = bpy.props.FloatVectorProperty(default=(1.0, 1.0, 1.0, 0.0), name="initial color 2", size=4, subtype="COLOR", options={"ANIMATABLE"})
    finalColor2 = bpy.props.FloatVectorProperty(default=(1.0, 1.0, 1.0, 1.0), name="final color 2", size=4, subtype="COLOR", options={"ANIMATABLE"})
    unknownColor2 = bpy.props.FloatVectorProperty(default=(1.0, 1.0, 1.0, 1.0), name="unknown color 2", size=4, subtype="COLOR", options={"ANIMATABLE"})
    partEmit = bpy.props.IntProperty(default=0, subtype="UNSIGNED", options={"ANIMATABLE"})
    phase1StartImageIndex = bpy.props.IntProperty(default=0, min=0, max=255, subtype="UNSIGNED", options=set(), description="Specifies the cell index shown at start of phase 1 when the image got divided into rows and collumns")
    phase1EndImageIndex = bpy.props.IntProperty(default=0, min=0, max=255, subtype="UNSIGNED", options=set(), description="Specifies the cell index shown at end of phase 1 when the image got divided into rows and collumns")
    phase2StartImageIndex = bpy.props.IntProperty(default=0, min=0, max=255, subtype="UNSIGNED", options=set(), description="Specifies the cell index shown at start of phase 2 when the image got divided into rows and collumns")
    phase2EndImageIndex = bpy.props.IntProperty(default=0, min=0, max=255, subtype="UNSIGNED", options=set(), description="Specifies the cell index shown at end of phase 2 when the image got divided into rows and collumns")
    relativePhase1Length = bpy.props.FloatProperty(default=1.0, min=0.0, max=1.0, subtype="FACTOR" ,name="relative phase 1 length", options=set(), description="A value of 0.4 means that 40% of the lifetime of the particle the phase 1 image animation will play")
    numberOfColumns = bpy.props.IntProperty(default=0, min=0, subtype="UNSIGNED", name="columns", options=set(), description="Specifies in how many columns the image gets divided")
    numberOfRows = bpy.props.IntProperty(default=0, min=0, subtype="UNSIGNED", name="rows", options=set(), description="Specifies in how many rows the image gets divided")
    columnWidth = bpy.props.FloatProperty(default=float("inf"), min=0.0, max=1.0, name="columnWidth", options=set(), description="Specifies the width of one column, relative to an image with width 1")
    rowHeight = bpy.props.FloatProperty(default=float("inf"), min=0.0, max=1.0, name="rowHeight", options=set(), description="Specifies the height of one row, relative to an image with height 1")
    unknownFloat4 = bpy.props.FloatProperty(default=0.0, name="unknownFloat4",options=set())
    unknownFloat5 = bpy.props.FloatProperty(default=1.0, name="unknownFloat5",options=set())
    unknownFloat6 = bpy.props.FloatProperty(default=1.0, name="unknownFloat6",options=set())
    unknownFloat7 = bpy.props.FloatProperty(default=1.0, name="unknownFloat7",options=set())
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
    name = bpy.props.StringProperty(name="name", options=set())
    boneName = bpy.props.StringProperty(name="boneName", options=set())
    volumeType = bpy.props.EnumProperty(default="-1",update=handleAttachmentVolumeTypeChange, items=attachmentVolumeTypeList, options=set())
    volumeSize0 = bpy.props.FloatProperty(default=1.0, options=set())
    volumeSize1 = bpy.props.FloatProperty(default=0.0, options=set())
    volumeSize2 = bpy.props.FloatProperty(default=0.0, options=set())

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


class MaterialReferencesPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_M3_material_references"
    bl_label = "M3 Materials"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        row = layout.row()
        col = row.column()
        col.template_list(scene, "m3_material_references", scene, "m3_material_reference_index", rows=2)

        col = row.column(align=True)
        col.operator("m3.materials_add", icon='ZOOMIN', text="")
        col.operator("m3.materials_remove", icon='ZOOMOUT', text="")

class MaterialPropertiesPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_M3_material_properties"
    bl_label = "M3 Material Properties"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        materialReferenceIndex = scene.m3_material_reference_index
        if materialReferenceIndex >= 0 and materialReferenceIndex < len(scene.m3_material_references):
            materialReference = scene.m3_material_references[materialReferenceIndex]
            materialType = materialReference.materialType
            materialIndex = materialReference.materialIndex
            
            if materialType == shared.standardMaterialTypeIndex:
                material = scene.m3_standard_materials[materialIndex]
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
            else:
                layout.label(text=("Unsupported material type %d" % materialType))

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

        materialIndex = scene.m3_material_reference_index
        if materialIndex >= 0 and materialIndex < len(scene.m3_material_references):
            materialReference = scene.m3_material_references[materialIndex]
            materialType = materialReference.materialType
            materialIndex = materialReference.materialIndex
            
            if materialType == shared.standardMaterialTypeIndex:
                material = scene.m3_standard_materials[materialIndex]
                col.template_list(material, "layers", scene, "m3_material_layer_index", rows=2)
                layerIndex = scene.m3_material_layer_index
                if layerIndex >= 0 and layerIndex < len(material.layers):
                    layer = material.layers[layerIndex]
                    layout.prop(layer, 'imagePath', text="Image Path")
                    layout.prop(layer, 'uvSource', text="UV Source")
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
            col.label(text="No properties to display")


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
            layout.prop(particle_system, 'materialReferenceIndex',text="Material Index")
            
            split = layout.split()
            col = split.column()
            col.row().label("Emis. Area:")
            col = col.row().column(align=True)
            col.prop(particle_system, 'emissionAreaType',text="")
            sub = col.row()
            sub.active = particle_system.emissionAreaType in particleTypesWithLength
            sub.prop(particle_system, 'emissionAreaSize', index=0, text="Length")
            sub =  col.row()
            sub.active = particle_system.emissionAreaType in particleTypesWithWidth
            sub.prop(particle_system, 'emissionAreaSize', index=1, text="Width")
            sub = col.row()
            sub.active = particle_system.emissionAreaType in particleTypesWithHeight
            sub.prop(particle_system, 'emissionAreaSize', index=2, text="Height")
            sub = col.row()
            sub.active = particle_system.emissionAreaType in particleTypesWithRadius
            sub.prop(particle_system, 'emissionAreaRadius',text="Radius")
            
            split = layout.split()
            col = split.column()
            col.prop(particle_system, 'emissionRate', text="Particles Per Second")
            col.prop(particle_system, 'maxParticles', text="Particle Maximum")
            
            layout.prop(particle_system, 'trailingEnabled', text="Trailing")

            split = layout.split()
            col = split.column()
            col.label(text="Emis. Speed.:")
            sub = col.column(align=True)
            sub.prop(particle_system, "emissionSpeed1", text="")
            col = split.column()
            col.prop(particle_system, "randomizeWithEmissionSpeed2", text="Randomize With:")
            sub = col.column(align=True)
            sub.active = particle_system.randomizeWithEmissionSpeed2
            sub.prop(particle_system, "emissionSpeed2", text="")

            layout.prop(particle_system, 'emissionType', text="Emission Type")
            split = layout.split()
            split.active = particle_system.emissionType != "1"
            col = split.column()
            sub = col.column(align=True)
            sub.label(text="Angle:")
            sub.prop(particle_system, "emissionAngleX", text="X")
            sub.prop(particle_system, "emissionAngleY", text="Y")
            col = split.column()
            sub = col.column(align=True)
            sub.label(text="Spread:")
            sub.prop(particle_system, "emissionSpreadX", text="X")
            sub.prop(particle_system, "emissionSpreadY", text="Y")
            
            split = layout.split()
            col = split.column()
            col.label(text="Lifespan:")
            sub = col.column(align=True)
            sub.prop(particle_system, "lifespan1", text="")
            col = split.column()
            col.prop(particle_system, "randomizeWithLifespan2", text="Randomize With:")
            sub = col.column(align=True)
            sub.active = particle_system.randomizeWithLifespan2
            sub.prop(particle_system, "lifespan2", text="")
            
            
            layout.prop(particle_system, 'zAcceleration', text="Z-Acceleration")
            
            split = layout.split()
            col = split.column()
            col.label(text="Color:")
            sub = col.column(align=True)
            sub.prop(particle_system, "initialColor1", text="Initial")
            sub.prop(particle_system, "finalColor1", text="Final")
            sub.prop(particle_system, "unknownColor1", text="Unknown")
            col = split.column()
            col.prop(particle_system, "randomizeWithColor2", text="Randomize With:")
            sub = col.column(align=True)
            sub.active = particle_system.randomizeWithColor2
            sub.prop(particle_system, "initialColor2", text="Initial")
            sub.prop(particle_system, "finalColor2", text="Final")
            sub.prop(particle_system, "unknownColor2", text="Unknown")
            

            split = layout.split()
            col = split.column()
            sub = col.column(align=True)
            sub.label(text="Size (Particle):")
            sub.prop(particle_system, 'particleSizes1', index=0, text="Initial")
            sub.prop(particle_system, 'particleSizes1', index=1, text="Final")
            sub.prop(particle_system, 'particleSizes1', index=2, text="Unknown")
            col = split.column()
            col.prop(particle_system, "randomizeWithParticleSizes2", text="Randomize With:")
            sub = col.column(align=True)
            sub.active = particle_system.randomizeWithParticleSizes2
            sub.prop(particle_system, 'particleSizes2', index=0, text="Initial")
            sub.prop(particle_system, 'particleSizes2', index=1, text="Final")
            sub.prop(particle_system, 'particleSizes2', index=2, text="Unknown")


            split = layout.split()
            col = split.column()
            sub = col.column(align=True)
            sub.label(text="Rotation (Particle):")
            sub.prop(particle_system, 'rotationValues1', index=0, text="Initial")
            sub.prop(particle_system, 'rotationValues1', index=1, text="Speed")
            sub.prop(particle_system, 'rotationValues1', index=2, text="Unknown")
            col = split.column()
            col.prop(particle_system, "randomizeWithRotationValues2", text="Randomize With:")
            sub = col.column(align=True)
            sub.active = particle_system.randomizeWithRotationValues2
            sub.prop(particle_system, 'rotationValues2', index=0, text="Initial")
            sub.prop(particle_system, 'rotationValues2', index=1, text="Speed")
            sub.prop(particle_system, 'rotationValues2', index=2, text="Unknown")

            split = layout.split()
            row = split.row()
            sub = row.column(align=True)
            sub.label(text="Column:")
            sub.prop(particle_system, 'numberOfColumns', text="Count")
            sub.prop(particle_system, 'columnWidth', text="Width")
            row = split.row()
            sub = row.column(align=True)
            sub.label(text="Row:")
            sub.prop(particle_system, 'numberOfRows', text="Count")
            sub.prop(particle_system, 'rowHeight', text="Height")
            split = layout.split()
            col = split.column()
            sub = col.column(align=True)
            sub.label(text="Phase 1 Image Index:")
            sub.prop(particle_system, 'phase1StartImageIndex', text="Inital")
            sub.prop(particle_system, 'phase1EndImageIndex', text="Final")
            split = layout.split()
            col = split.column()
            sub = col.column(align=True)
            sub.label(text="Phase 2 Image Index:")
            sub.prop(particle_system, 'phase2StartImageIndex', text="Inital")
            sub.prop(particle_system, 'phase2EndImageIndex', text="Final")
            layout.prop(particle_system, 'relativePhase1Length', text="Relative Phase 1 Length")


            split = layout.split()
            col = split.column()
            sub = col.column(align=True)
            sub.label(text="Unknown Floats 1:")
            sub.prop(particle_system, 'unknownFloat1a', text="")
            sub.prop(particle_system, "unknownFloat1b", text="")
            sub.prop(particle_system, "unknownFloat1c", text="")
            sub.prop(particle_system, "unknownFloat1d", text="")
            
            layout.prop(particle_system, 'slowdown', text="Slowdown")
            
            split = layout.split()
            col = split.column()
            sub = col.column(align=True)
            sub.label(text="Unknown Floats 2:")
            sub.prop(particle_system, "unknownFloat2a", text="X")
            sub.prop(particle_system, "unknownFloat2b", text="Y")
            sub.prop(particle_system, "unknownFloat2c", text="Z")
                        
            layout.prop(particle_system, 'tailUnk1', text="Tail Unk1")
            layout.prop(particle_system, 'spreadUnk', text="Spread Unk")
            layout.prop(particle_system, 'partEmit', text="Part. Emit.")

            layout.prop(particle_system, "unknownFloat4", text="Unknown Float 4")
            layout.prop(particle_system, "unknownFloat5", text="Unknown Float 5")
            layout.prop(particle_system, "unknownFloat6", text="Unknown Float 6")
            layout.prop(particle_system, "unknownFloat7", text="Unknown Float 7")

            
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
            layout.prop(attachment_point, 'name', text="Name")
            layout.prop(attachment_point, 'boneName', text="Bone")
            layout.prop(attachment_point, 'volumeType', text="Volume: ")
            if attachment_point.volumeType in ["1", "2"]: 
                layout.prop(attachment_point, 'volumeSize0', text="Volume Radius")
            elif attachment_point.volumeType in  ["0"]:
                layout.prop(attachment_point, 'volumeSize0', text="Volume Width")
            if attachment_point.volumeType in ["0"]:
                layout.prop(attachment_point, 'volumeSize1', text="Volume Length")
            elif attachment_point.volumeType in ["2"]:
                layout.prop(attachment_point, 'volumeSize1', text="Volume Height")
            if attachment_point.volumeType in ["0"]:
                layout.prop(attachment_point, 'volumeSize2', text="Volume Height")

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
        defaultSettingMesh = "MESH"
        defaultSettingParticle = "PARTICLE"
        if self.defaultSetting in [defaultSettingMesh, defaultSettingParticle]:
            materialIndex = len(scene.m3_standard_materials)
            materialType = shared.standardMaterialTypeIndex
            materialReferenceIndex = len(scene.m3_material_references)
            materialReference = scene.m3_material_references.add()
            materialReference.materialIndex = materialIndex
            materialReference.materialType = materialType
            material = scene.m3_standard_materials.add()
            material.materialReferenceIndex = materialReferenceIndex
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
        
        scene.m3_material_reference_index = len(scene.m3_material_references)-1
        return {'FINISHED'}
    def findUnusedName(self, scene):
        usedNames = set()
        for material in scene.m3_standard_materials:
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
        referenceIndex = scene.m3_material_reference_index
        if referenceIndex>= 0:
            # Check if material is in use, and abort:
            for particle_system in scene.m3_particle_systems:
                if particle_system.materialReferenceIndex == referenceIndex:
                    self.report({"ERROR"}, "Can't delete: The particle system '%s' is using this material" % particle_system.name)
                    return {"CANCELLED"}
                    
            for higherReferenceIndex in range(referenceIndex+1,len(scene.m3_material_references)):
                higherReference = scene.m3_material_references[higherReferenceIndex]
                material = shared.getMaterial(scene, higherReference.materialType, higherReference.materialIndex)
                if material != None:
                    material.materialReferenceIndex -= 1
                    
            materialReference = scene.m3_material_references[referenceIndex]
            materialIndex = materialReference.materialIndex
            materialType = materialReference.materialType
            
            for particle_system in scene.m3_particle_systems:
                if particle_system.materialReferenceIndex > referenceIndex:
                    particle_system.materialReferenceIndex -= 1
            
            for otherReference in scene.m3_material_references:
                if otherReference.materialType == materialType and otherReference.materialIndex > materialIndex:
                    otherReference.materialIndex -= 1

            if materialType == shared.standardMaterialTypeIndex:
                scene.m3_standard_materials.remove(materialIndex)
            
            scene.m3_material_references.remove(scene.m3_material_reference_index)
            scene.m3_material_reference_index -= 1
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
        animation.exlusiveEndFrame = 60
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
        if len(scene.m3_material_references) >= 1:
            particle_system.materialName = scene.m3_material_references[0].name

        handleTypeOrBoneSuffixChange(particle_system, context)
        scene.m3_particle_system_index = len(scene.m3_particle_systems)-1
        
        selectOrCreateBoneForPartileSystem(scene, particle_system)
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
        attachment_point.boneName = name

        scene.m3_attachment_point_index = len(scene.m3_attachment_points)-1
        return{'FINISHED'}
        
    def findUnusedName(self, scene):
        usedNames = set()
        for attachment_point in scene.m3_attachment_points:
            usedNames.add(attachment_point.name)
        suggestedNames = ["Ref_Center", "Ref_Origin", "Ref_Overhead", "Ref_Target"]

        for boneName in boneNameSet():
            if boneName.startswith("Ref_"):
                suggestedNames.add(boneName)
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
    filter_glob = StringProperty(default="*.m3;*.m3a", options={'HIDDEN'})

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
    bpy.types.Scene.m3_material_references = bpy.props.CollectionProperty(type=M3Material)
    bpy.types.Scene.m3_standard_materials = bpy.props.CollectionProperty(type=M3StandardMaterial)
    bpy.types.Scene.m3_material_reference_index = bpy.props.IntProperty()
    bpy.types.Scene.m3_particle_systems = bpy.props.CollectionProperty(type=M3ParticleSystem)
    bpy.types.Scene.m3_particle_system_index = bpy.props.IntProperty(update=handlePartileSystemIndexChanged)
    bpy.types.Scene.m3_attachment_points = bpy.props.CollectionProperty(type=M3AttachmentPoint)
    bpy.types.Scene.m3_attachment_point_index = bpy.props.IntProperty()
    bpy.types.Scene.m3_export_options = bpy.props.PointerProperty(type=M3ExportOptions)
    bpy.types.Scene.m3_animation_ids = bpy.props.CollectionProperty(type=M3AnimIdData)

    bpy.types.INFO_MT_file_import.append(menu_func_import)
    bpy.types.INFO_MT_file_export.append(menu_func_export)
 
def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.INFO_MT_file_import.remove(menu_func_import)
    bpy.types.INFO_MT_file_export.remove(menu_func_export)
 
if __name__ == "__main__":
    register()