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
    "category": "Import-Export",
    "tracker_url": "https://github.com/flo/m3addon/issues?state=open"
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
import mathutils
import math

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

def updateBoenShapesOfParticleSystemCopies(scene, particleSystem):
    for copy in particleSystem.copies:
        boneName = copy.boneName
        bone, armatureObject = shared.findBoneWithArmatureObject(scene, boneName)
        if bone != None:
            poseBone = armatureObject.pose.bones[boneName]
            shared.updateBoneShapeOfParticleSystem(particleSystem, bone, poseBone)

def handleAttachmentPointTypeOrBoneSuffixChange(self, context):
    attachmentPoint = self
    scene = context.scene
    typeName = "Unknown"
    if attachmentPoint.volumeType == "-1":
        typeName = "Point"
    else:
        typeName = "Volume"
        
    boneSuffix = attachmentPoint.boneSuffix
    attachmentPoint.name = "%s (%s)" % (boneSuffix, typeName)
    
    currentBoneName = attachmentPoint.boneName
    calculatedBoneName = shared.boneNameForAttachmentPoint(attachmentPoint)
    
    if currentBoneName != calculatedBoneName:
        bone, armatureObject = shared.findBoneWithArmatureObject(scene, currentBoneName)
        if bone != None:
            bone.name = calculatedBoneName
            attachmentPoint.boneName = bone.name
        else:
            attachmentPoint.boneName = calculatedBoneName
    if attachmentPoint.updateBlenderBone:
        selectOrCreateBoneForAttachmentPoint(scene, attachmentPoint)
    
def handleParticleSystemTypeOrBoneSuffixChange(self, context):
    particleSystem = self
    scene = context.scene
    typeName = "Unknown"
    for typeId, name, description in emissionAreaTypeList:
        if typeId == particleSystem.emissionAreaType:
            typeName = name
    
    boneSuffix = particleSystem.boneSuffix
    particleSystem.name = "%s (%s)" % (boneSuffix, typeName)

    if particleSystem.updateBlenderBoneShapes:
        currentBoneName = particleSystem.boneName
        calculatedBoneName = shared.boneNameForPartileSystem(particleSystem)

        if currentBoneName != calculatedBoneName:
            bone, armatureObject = shared.findBoneWithArmatureObject(scene, currentBoneName)
            if bone != None:
                bone.name = calculatedBoneName
                particleSystem.boneName = bone.name
            else:
                particleSystem.boneName = calculatedBoneName

            selectOrCreateBoneForPartileSystem(scene, particleSystem)
            updateBoenShapesOfParticleSystemCopies(scene, particleSystem)
        
def handleParticleSystemCopyRename(self, context):
    scene = context.scene
    particleSystemCopy = self
    
    currentBoneName = particleSystemCopy.boneName
    calculatedBoneName = shared.boneNameForPartileSystemCopy(particleSystemCopy)

    if currentBoneName != calculatedBoneName:
        bone, armatureObject = shared.findBoneWithArmatureObject(scene, currentBoneName)
        if bone != None:
            bone.name = calculatedBoneName
            particleSystemCopy.boneName = bone.name
        else:
            particleSystemCopy.boneName = calculatedBoneName
        
def handleParticleSystemAreaSizeChange(self, context):
    particleSystem = self
    scene = context.scene
    if particleSystem.updateBlenderBoneShapes:
        selectOrCreateBoneForPartileSystem(scene, particleSystem)
        updateBoenShapesOfParticleSystemCopies(scene, particleSystem)


def handleForceTypeOrBoneSuffixChange(self, context):
    scene = context.scene
    force = self
    typeName = "Unknown"
    for typeId, name, description in forceTypeList:
        if typeId == force.forceType:
            typeName = name
    
    boneSuffix = force.boneSuffix
    self.name = "%s (%s)" % (boneSuffix, typeName)

    if force.updateBlenderBoneShape:
        currentBoneName = force.boneName
        calculatedBoneName = shared.boneNameForForce(force)

        if currentBoneName != calculatedBoneName:
            bone, armatureObject = shared.findBoneWithArmatureObject(scene, currentBoneName)
            if bone != None:
                bone.name = calculatedBoneName
                force.boneName = bone.name
            else:
                force.boneName = calculatedBoneName

            selectOrCreateBoneForForce(scene, force)


def handleLightTypeOrBoneSuffixChange(self, context):
    scene = context.scene
    light = self
    typeName = "Unknown"
    for typeId, name, description in lightTypeList:
        if typeId == light.lightType:
            typeName = name
    
    light.name = "%s (%s)" % (light.boneSuffix, typeName)
    
    currentBoneName = light.boneName
    calculatedBoneName = shared.boneNameForLight(light)

    if light.updateBlenderBone:
        if currentBoneName != calculatedBoneName:
            bone, armatureObject = shared.findBoneWithArmatureObject(scene, currentBoneName)
            if bone != None:
                bone.name = calculatedBoneName
                light.boneName = bone.name
            else:
                light.boneName = calculatedBoneName
        selectOrCreateBoneForLight(scene, light)

def handleLightSizeChange(self, context):
    scene = context.scene
    light = self
    if light.updateBlenderBone:
        selectOrCreateBoneForLight(scene, light)

def handleCameraNameChange(self, context):
    scene = context.scene
    if self.name != self.oldName:
        bone, armatureObject = shared.findBoneWithArmatureObject(scene, self.oldName)
        if bone != None:
            bone.name = self.name
    self.oldName = self.name

def handleMaterialNameChange(self, context):
    scene = context.scene
    materialName = self.name
    materialReferenceIndex = self.materialReferenceIndex
    if materialReferenceIndex != -1:
        materialReference = scene.m3_material_references[self.materialReferenceIndex]
        materialIndex = materialReference.materialIndex
        materialType = materialReference.materialType
        oldMaterialName = materialReference.name 
        materialReference.name = materialName
        
        for particle_system in scene.m3_particle_systems:
            if particle_system.materialName == oldMaterialName:
                particle_system.materialName = materialName
                
        for meshObject in shared.findMeshObjects(scene):
            mesh = meshObject.data
            if mesh.m3_material_name == oldMaterialName:     
                mesh.m3_material_name = materialName
    
def handleAttachmentVolumeTypeChange(self, context):
    handleAttachmentPointTypeOrBoneSuffixChange(self, context)
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
        
        
def handleAttachmentVolumeSizeChange(self, context):
    scene = context.scene
    attachmentPoint = self
    if attachmentPoint.updateBlenderBone:
        selectOrCreateBoneForAttachmentPoint(scene, attachmentPoint)

def handleGeometicShapeUpdate(self, context):
    shapeObject = self
    if shapeObject.updateBlenderBoneShapes:
        selectOrCreateBoneForShapeObject(context.scene, shapeObject)

def handleParticleSystemsVisiblityUpdate(self, context):
    scene = context.scene
    for particleSystem in scene.m3_particle_systems:
        boneName = shared.boneNameForPartileSystem(particleSystem.boneSuffix)
        shared.setBoneVisibility(scene, boneName, self.showParticleSystems)
        
        for copy in particleSystem.copies:
            boneName = copy.boneName
            shared.setBoneVisibility(scene, boneName, self.showParticleSystems)

def handleFuzzyHitTestVisiblityUpdate(self, context):
    scene = context.scene
    for fuzzyHitTest in scene.m3_fuzzy_hit_tests:
        boneName = fuzzyHitTest.name
        shared.setBoneVisibility(scene, boneName, self.showFuzzyHitTests)
    
def handleTightHitTestVisiblityUpdate(self, context):
    scene = context.scene
    tightHitTest = scene.m3_tight_hit_test
    boneName = tightHitTest.name
    shared.setBoneVisibility(scene, boneName, self.showTightHitTest)

def handleAttachmentPointVisibilityUpdate(self, context):
    scene = context.scene
    for attachmentPoint in scene.m3_attachment_points:
        boneName = attachmentPoint.boneName
        shared.setBoneVisibility(scene, boneName, self.showAttachmentPoints)

def handleLightsVisiblityUpdate(self, context):
    scene = context.scene
    for light in scene.m3_lights:
        boneName = light.boneName
        shared.setBoneVisibility(scene, boneName, self.showLights)

def handleCamerasVisiblityUpdate(self, context):
    scene = context.scene
    for camera in scene.m3_cameras:
        boneName = camera.name
        shared.setBoneVisibility(scene, boneName, self.showCameras)

def handlePhysicsShapeVisibilityUpdate(self, context):
    scene = context.scene
    for rigidBody in scene.m3_rigid_bodies:
        boneName = rigidBody.boneName
        shared.setBoneVisibility(scene, boneName, self.showPhysicsShapes)

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
            newAction = newObjectNameToActionMap.get(targetObject.name)
            prepareDefaultValuesForNewAction(scene, targetObject, 'OBJECT', newAction)
            targetObject.animation_data_clear()
            if newAction != None:
                targetObject.animation_data_create()
                targetObject.animation_data.action = newAction

        prepareDefaultValuesForNewAction(scene, scene, 'SCENE', newSceneAction)
        scene.animation_data_clear()
        if newSceneAction != None:
            scene.animation_data_create()
            scene.animation_data.action = newSceneAction
                
    scene.m3_animation_old_index = newIndex

def prepareDefaultValuesForNewAction(scene, targetObject, actionOwnerType, newAction):
    oldAnimatedProperties = set()
    if targetObject.animation_data != None:
        oldAction = targetObject.animation_data.action
        if oldAction != None:
            for curve in oldAction.fcurves:
                oldAnimatedProperties.add((curve.data_path, curve.array_index))
    newAnimatedProperties = set()
    if newAction != None:
        for curve in newAction.fcurves:
            newAnimatedProperties.add((curve.data_path, curve.array_index))
    actionOwnerName = targetObject.name
    
    defaultAction = shared.determineDefaultActionFor(scene, actionOwnerName, actionOwnerType)
    if defaultAction == None:
        defaultAction = shared.createDefaulValuesAction(scene, actionOwnerName, actionOwnerType)
    propertiesBecomingAnimated = newAnimatedProperties.difference(oldAnimatedProperties)
    for prop in propertiesBecomingAnimated:
        value = getAttribute(targetObject, prop[0],prop[1])
        curve = None
        for c in defaultAction.fcurves:
            if c.data_path == prop[0] and c.array_index == prop[1]:
                curve = c
                break
        if curve == None:
            curve = defaultAction.fcurves.new(prop[0], prop[1])
        keyFrame = curve.keyframe_points.insert(0, value)
        keyFrame.interpolation = "CONSTANT"
    propertiesBecomingUnanimated = oldAnimatedProperties.difference(newAnimatedProperties)
    if defaultAction != None:
        for curve in defaultAction.fcurves:
            prop = (curve.data_path, curve.array_index)
            if prop in propertiesBecomingUnanimated:
                defaultValue = curve.evaluate(0)
                setAttribute(targetObject, curve.data_path, curve.array_index, defaultValue)


def setAttribute(obj, curvePath, curveIndex, value):
    """Gets the value of an attribute via animation path and index"""
    resolvedObject = obj.path_resolve(curvePath)
    if type(resolvedObject) in [float, int]:
        dotIndex = curvePath.rfind(".")
        attributeName = curvePath[dotIndex+1:]
        resolvedObject = obj.path_resolve(curvePath[:dotIndex])
        setattr(resolvedObject, attributeName, value)
    else:
        resolvedObject[curveIndex] = value

def getAttribute(obj, curvePath, curveIndex):
    """Gets the value of an attribute via animation path and index"""
    obj = obj.path_resolve(curvePath)
    if type(obj) in [float, int]:
        return obj
    else:
        return obj[curveIndex]

def findUnusedParticleSystemName(scene):
    usedNames = set()
    for particle_system in scene.m3_particle_systems:
        usedNames.add(particle_system.boneSuffix)
        for copy in particle_system.copies:
            usedNames.add(copy.name)
    unusedName = None
    counter = 1
    while unusedName == None:
        suggestedName = "%02d" % counter
        if not suggestedName in usedNames:
            unusedName = suggestedName
        counter += 1
    return unusedName  

def handlePartileSystemIndexChanged(self, context):
    scene = context.scene
    if scene.m3_particle_system_index == -1:
        return
    particleSystem = scene.m3_particle_systems[scene.m3_particle_system_index]
    particleSystem.copyIndex = -1
    selectOrCreateBoneForPartileSystem(scene, particleSystem)

def handleForceIndexChanged(self, context):
    scene = context.scene
    if scene.m3_force_index == -1:
        return
    force = scene.m3_forces[scene.m3_force_index]
    selectOrCreateBoneForForce(scene, force)

def handlePhysicsShapeUpdate(self, context):
    scene = context.scene
    
    if self.updateBlenderBoneShapes:
        if scene.m3_rigid_body_index != -1:
            rigidBody = scene.m3_rigid_bodies[scene.m3_rigid_body_index]
            shared.updateBoneShapeOfRigidBody(scene, rigidBody)
        
        selectCurrentRigidBodyBone(scene)

def handleRigidBodyIndexChange(self, context):
    selectCurrentRigidBodyBone(context.scene)

def handleRigidBodyBoneChange(self, context):
    # TODO: remove custom bone shape for old bone, create custom bone shape for new bone.
    # need to save old bone name somehow?
    selectCurrentRigidBodyBone(context.scene)

def selectCurrentRigidBodyBone(scene):
    if scene.m3_rigid_body_index != -1:
        rigidBody = scene.m3_rigid_bodies[scene.m3_rigid_body_index]
        selectBone(scene, rigidBody.boneName)

def handleLightIndexChanged(self, context):
    scene = context.scene
    if scene.m3_light_index == -1:
        return
    light = scene.m3_lights[scene.m3_light_index]
    selectOrCreateBoneForLight(scene, light)
    
def handleAttachmentPointIndexChanged(self, context):
    scene = context.scene
    if scene.m3_attachment_point_index == -1:
        return
    attachmentPoint = scene.m3_attachment_points[scene.m3_attachment_point_index]
    selectOrCreateBoneForAttachmentPoint(scene, attachmentPoint)

def handlePartileSystemCopyIndexChanged(self, context):
    scene = context.scene
    particleSystem = self
    if particleSystem.copyIndex >= 0 and particleSystem.copyIndex < len(particleSystem.copies):
        copy = particleSystem.copies[particleSystem.copyIndex]
        selectOrCreateBoneForPartileSystemCopy(scene, particleSystem, copy)

def handleCameraIndexChanged(self, context):
    scene = context.scene
    if scene.m3_camera_index == -1:
        return
    camera = scene.m3_cameras[scene.m3_camera_index]
    selectOrCreateBoneForCamera(scene, camera)

def handleFuzzyHitTestIndexChanged(self, context):
    scene = context.scene
    if scene.m3_fuzzy_hit_test_index == -1:
        return
    fuzzyHitTest = scene.m3_fuzzy_hit_tests[scene.m3_fuzzy_hit_test_index]
    selectOrCreateBoneForShapeObject(scene, fuzzyHitTest)

def selectOrCreateBoneForAttachmentPoint(scene, attachmentPoint):
    boneName = attachmentPoint.boneName
    bone, poseBone = selectOrCreateBone(scene, boneName)
    shared.updateBoneShapeOfAttachmentPoint(attachmentPoint, bone, poseBone)
    
def selectOrCreateBoneForPartileSystemCopy(scene, particleSystem, copy):
    boneName = copy.boneName
    bone, poseBone = selectOrCreateBone(scene, boneName)
    shared.updateBoneShapeOfParticleSystem(particleSystem, bone, poseBone)
    
def selectOrCreateBoneForForce(scene, force):
    boneName = force.boneName
    return selectOrCreateBone(scene, boneName)
    
def selectOrCreateBoneForLight(scene, light):
    boneName = light.boneName
    bone, poseBone = selectOrCreateBone(scene, boneName)
    shared.updateBoneShapeOfLight(light, bone, poseBone)

def selectOrCreateBoneForCamera(scene, camera):
    selectOrCreateBone(scene, camera.name)

def selectOrCreateBoneForPartileSystem(scene, particle_system):
    boneName = particle_system.boneName
    bone, poseBone = selectOrCreateBone(scene, boneName)
    shared.updateBoneShapeOfParticleSystem(particle_system, bone, poseBone)

def selectOrCreateBoneForShapeObject(scene, shapeObject):
    bone, poseBone = selectOrCreateBone(scene, shapeObject.name)
    shared.updateBoneShapeOfShapeObject(shapeObject, bone, poseBone)

def selectBone(scene, boneName):
    bone, armature = shared.findBoneWithArmatureObject(scene, boneName)
    if bone == None or armature == None:
        return
    
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='OBJECT')
    if bpy.ops.object.select_all.poll():
        bpy.ops.object.select_all(action='DESELECT')
    
    armature.select = True
    scene.objects.active = armature
    
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='POSE')
    
    for b in armature.data.bones:
        b.select = False
    
    bone.select = True
    
def removeBone(scene, boneName):
    "removes the given bone if it exists"
    bone, armatureObject = shared.findBoneWithArmatureObject(scene, boneName)
    if bone == None or armatureObject == None:
        return
    
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='OBJECT')
    if bpy.ops.object.select_all.poll():
        bpy.ops.object.select_all(action='DESELECT')
    
    armatureObject.select = True
    scene.objects.active = armatureObject
    
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='EDIT')
    
    armature = armatureObject.data
    edit_bone = armature.edit_bones[boneName]
    armature.edit_bones.remove(edit_bone)
    
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='POSE')
    

def selectOrCreateBone(scene, boneName):
    "Returns the bone and it's pose variant"
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='OBJECT')
    if bpy.ops.object.select_all.poll():
        bpy.ops.object.select_all(action='DESELECT')
    bone, armatureObject = shared.findBoneWithArmatureObject(scene, boneName)
    boneExists = bone != None
    if boneExists:
        armature = armatureObject.data
        armatureObject.select = True
        scene.objects.active = armatureObject
    else:
        armatureObject = shared.findArmatureObjectForNewBone(scene)
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

    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='POSE')
    scene.objects.active = armatureObject
    armatureObject.select = True
    for currentBone in armature.bones:
        currentBone.select = currentBone.name == boneName
    poseBone = armatureObject.pose.bones[boneName]
    bone = armatureObject.data.bones[boneName]
    return (bone, poseBone)


emissionAreaTypesWithRadius = [shared.emssionAreaTypeSphere, shared.emssionAreaTypeCylinder]
emissionAreaTypesWithWidth = [shared.emssionAreaTypePlane, shared.emssionAreaTypeCuboid]
emissionAreaTypesWithLength = [shared.emssionAreaTypePlane, shared.emssionAreaTypeCuboid]
emissionAreaTypesWithHeight = [shared.emssionAreaTypeCuboid, shared.emssionAreaTypeCylinder]
emissionAreaTypeList =  [(shared.emssionAreaTypePoint, "Point", "Particles spawn at a certain point"), 
                        (shared.emssionAreaTypePlane, 'Plane', "Particles spawn in a rectangle"), 
                        (shared.emssionAreaTypeSphere, 'Sphere', 'Particles spawn in a sphere'),
                        (shared.emssionAreaTypeCuboid, 'Cuboid', 'Particles spawn in a cuboid'),
                        (shared.emssionAreaTypeCylinder, 'Cylinder', 'Particles spawn in a cylinder')
                        ]

particleTypeList = [("0", "Square Billbords", "Quads always rotated towards camera (id 0)"), 
                    ("1", "Speed Scaled and Rotated Billbords", "Particles are rectangles scaled which get scaled by speed by a configurable amounth"),
                    ("2", "Square Billbords 2?", "Unknown 2"),
                    ("3", "Square Billbords 3?", "Unknown 3"),
                    ("4", "Square Billbords 4?", "Unknown 4"),
                    ("5", "Square Billbords 5?", "Unknown 5"),
                    ("6", "Rectangular Billbords", "Rectangles which can have a length != witdh which are rotated towards the camera"),
                    ("7", "Quads with speed as normal", "Particles are quads which have their normals aligned to the speed vector of the particle")
                    ]

forceTypeList = [("0", "Directional", "The particles get accelerated into one direction"), 
                    ("1", "Radial", "Particles get accelerated ayway from the force source"),
                    ("2", "Unknown", "Unknown"),
                    ("3", "Rotary", "The particles rotate in a circle around a center")
                   ]

physicsShapeTypeList = [("0", "Box", "Box shape with the given width, length and height"),
                        ("1", "Sphere", "Sphere shape with the given radius"),
                        ("2", "Capsule", "Capsule shape with the given radius and length"),
                        ("3", "Cylinder", "Cylinder with the given radius and length"),
                        ("4", "Convex Hull", "Convex hull created from the attached mesh"),
                        ("5", "Mesh", "Mesh shape created from the attached mesh"),
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


attachmentVolumeTypeList = [(shared.attachmentVolumeNone, "None", "No Volume, it's a simple attachment point"), 
                            (shared.attachmentVolumeCuboid, 'Cuboid', "Volume with the shape of a cuboid with the given width, length and height"),
                            (shared.attachmentVolumeSphere, 'Sphere', "Volume with the shape of a sphere with the given radius"), 
                            (shared.attachmentVolumeCylinder, 'Cylinder', 'Volume with the shape of a cylinder with the given radius and height'),
                            ("3", 'Unknown 3', 'Unknown Volume with id 3'),
                            ("4", 'Unknown 4', 'Unknown Volume with id 4')
                           ]
                           
fuzzyHitTestShapeList = [("0", 'Cuboid', "A cuboid with the given width, length and height"),
                         ("1", 'Sphere', "A sphere with the given radius"),
                         ("2", 'Capsule', 'A capsue which is based on a cylinder with the given radius and height'),
                        ]
matDefaultSettingsList = [("MESH", "Mesh Standard Material", "A material for meshes"), 
                        ("PARTICLE", 'Particle Standard Material', "Material for particle systems"),
                        ("DISPLACEMENT", "Displacement Material", "Moves the colors of the background to other locations"),
                        ("COMPOSITE", "Composite Material", "A combination of multiple materials"),
                        ("TERRAIN", "Terrain Material", "Makes the object look like the ground below it"),
                        ("VOLUME", "Volume Material", "A fog like material")
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

lightTypeList = [# directional light isn't supported yet: ("0", "Directional", ""),
                 (shared.lightTypePoint, "Point", "Light are generated around a point"),
                 (shared.lightTypeSpot, "Spot", "")
                 ]
class M3AnimIdData(bpy.types.PropertyGroup):
    # animId is actually an unsigned integer but blender can store only signed ones
    # thats why the number range needs to be moved into the negative for storage
    animIdMinus2147483648 = bpy.props.IntProperty(name="animId", options=set())
    longAnimId = bpy.props.StringProperty(name="longAnimId", options=set())

class M3AnimatedPropertyReference(bpy.types.PropertyGroup):
    longAnimId = bpy.props.StringProperty(name="longAnimId", options=set())
    
class AssignedActionOfM3Animation(bpy.types.PropertyGroup):
    targetName = bpy.props.StringProperty(name="targetName", options=set())
    actionName = bpy.props.StringProperty(name="actionName", options=set())

class M3TransformationCollection(bpy.types.PropertyGroup):
    name = bpy.props.StringProperty(name="name", default="all", options=set())
    animatedProperties = bpy.props.CollectionProperty(type=M3AnimatedPropertyReference, options=set())
    runsConcurrent = bpy.props.BoolProperty(default=True, options=set())

    
class M3Animation(bpy.types.PropertyGroup):
    name = bpy.props.StringProperty(name="name", default="Stand", options=set())
    startFrame = bpy.props.IntProperty(subtype="UNSIGNED", options=set())
    useSimulateFrame = bpy.props.BoolProperty(default=False, options=set())
    simulateFrame = bpy.props.IntProperty(subtype="UNSIGNED", default=0, options=set())
    exlusiveEndFrame = bpy.props.IntProperty(subtype="UNSIGNED", options=set())
    assignedActions = bpy.props.CollectionProperty(type=AssignedActionOfM3Animation, options=set())
    transformationCollections = bpy.props.CollectionProperty(type=M3TransformationCollection, options=set())
    transformationCollectionIndex = bpy.props.IntProperty(default=0, options=set())
    movementSpeed = bpy.props.FloatProperty(name="mov. speed", options=set())
    frequency = bpy.props.IntProperty(subtype="UNSIGNED",options=set())
    notLooping = bpy.props.BoolProperty(options=set())
    alwaysGlobal = bpy.props.BoolProperty(options=set())
    globalInPreviewer = bpy.props.BoolProperty(options=set())

class M3MaterialLayer(bpy.types.PropertyGroup):
    name = bpy.props.StringProperty(options={"SKIP_SAVE"}, default="Material Layer")
    imagePath = bpy.props.StringProperty(name="image path", default="", options=set())
    unknown11 = bpy.props.IntProperty(name="unknown11", default=-1, options=set())
    color = bpy.props.FloatVectorProperty(name="color", default=(1.0, 1.0, 1.0, 1.0), size=4, subtype="COLOR", options={"ANIMATABLE"})
    textureWrapX = bpy.props.BoolProperty(options=set(), default=True)
    textureWrapY = bpy.props.BoolProperty(options=set(), default=True)
    colorEnabled = bpy.props.BoolProperty(options=set(), default=False)
    uvSource = bpy.props.EnumProperty(items=uvSourceList, options=set(), default="0")
    brightMult = bpy.props.FloatProperty(name="bright. mult.",options={"ANIMATABLE"}, default=1.0)
    uvOffset = bpy.props.FloatVectorProperty(name="uv offset", default=(0.0, 0.0), size=2, subtype="XYZ", options={"ANIMATABLE"})
    uvAngle = bpy.props.FloatVectorProperty(name="uv offset", default=(0.0, 0.0, 0.0), size=3, subtype="XYZ", options={"ANIMATABLE"})
    uvTiling = bpy.props.FloatVectorProperty(name="uv tiling", default=(1.0, 1.0), size=2, subtype="XYZ", options={"ANIMATABLE"})
    midtoneOffset = bpy.props.FloatProperty(name="midtone offset", options={"ANIMATABLE"}, description="Can be used to make dark areas even darker so that only the bright regions remain")
    brightness = bpy.props.FloatProperty(name="brightness", options={"ANIMATABLE"}, default=1.0)
    alphaAsTeamColor = bpy.props.BoolProperty(options=set())
    alphaOnly = bpy.props.BoolProperty(options=set())
    alphaBasedShading = bpy.props.BoolProperty(options=set())
    useTint = bpy.props.BoolProperty(options=set())
    tintAlpha = bpy.props.BoolProperty(options=set())
    tintStrength = bpy.props.FloatProperty(options=set())
    tintStart = bpy.props.FloatProperty(options=set())
    tintCutout = bpy.props.FloatProperty(options=set())

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
    darkNormalMapping = bpy.props.BoolProperty(options=set(), default=False)
    unknownFlag0x1 = bpy.props.BoolProperty(options=set(), description="Should be true for particle system materials", default=False)
    unknownFlag0x4 = bpy.props.BoolProperty(options=set(), description="Makes mesh materials turn black but should be set for particle systems", default=False)
    unknownFlag0x8 = bpy.props.BoolProperty(options=set(), description="Should be true for particle system materials", default=False)
    unknownFlag0x200 = bpy.props.BoolProperty(options=set())

class M3DisplacementMaterial(bpy.types.PropertyGroup):
    name = bpy.props.StringProperty(name="name", default="Material", update=handleMaterialNameChange, options=set())
    # the following field gets used to update the name of the material reference:
    materialReferenceIndex = bpy.props.IntProperty(options=set(), default=-1)
    strengthFactor = bpy.props.FloatProperty(name="strength factor",options={"ANIMATABLE"}, default=1.0, description="Factor that gets multiplicated with the strength values")
    layers = bpy.props.CollectionProperty(type=M3MaterialLayer, options=set())
    priority = bpy.props.IntProperty(options=set())
    
class M3CompositeMaterialSection(bpy.types.PropertyGroup):
    # The material name is getting called "name" so that blender names it properly in the list view
    name = bpy.props.StringProperty(options=set()) 
    alphaFactor = bpy.props.FloatProperty(name="alphaFactor", options={"ANIMATABLE"}, min=0.0, max=1.0, default=1.0, description="Defines the factor with which the alpha channel gets multiplicated")

class M3CompositeMaterial(bpy.types.PropertyGroup):
    name = bpy.props.StringProperty(name="name", default="Material", update=handleMaterialNameChange, options=set())
    # the following field gets used to update the name of the material reference:
    materialReferenceIndex = bpy.props.IntProperty(options=set(), default=-1)
    layers = bpy.props.CollectionProperty(type=M3MaterialLayer, options=set())
    sections = bpy.props.CollectionProperty(type=M3CompositeMaterialSection, options=set())
    sectionIndex = bpy.props.IntProperty(options=set(), default=0)
    
class M3TerrainMaterial(bpy.types.PropertyGroup):
    name = bpy.props.StringProperty(name="name", default="Material", update=handleMaterialNameChange, options=set())
    # the following field gets used to update the name of the material reference:
    materialReferenceIndex = bpy.props.IntProperty(options=set(), default=-1)
    layers = bpy.props.CollectionProperty(type=M3MaterialLayer, options=set())

class M3VolumeMaterial(bpy.types.PropertyGroup):
    name = bpy.props.StringProperty(name="name", default="Material", update=handleMaterialNameChange, options=set())
    # the following field gets used to update the name of the material reference:
    materialReferenceIndex = bpy.props.IntProperty(options=set(), default=-1)
    volumeDensity = bpy.props.FloatProperty(name="volume density",options={"ANIMATABLE"}, default=1.0, description="Factor that gets multiplicated with the strength values")
    layers = bpy.props.CollectionProperty(type=M3MaterialLayer, options=set())

class M3Camera(bpy.types.PropertyGroup):
    name = bpy.props.StringProperty(name="name", default="Camera", update=handleCameraNameChange, options=set())
    oldName = bpy.props.StringProperty(name="oldName", options=set())
    fieldOfView = bpy.props.FloatProperty(name="fieldOfView", options={"ANIMATABLE"}, default=0.5)
    farClip = bpy.props.FloatProperty(name="farClip", options={"ANIMATABLE"}, default=10.0)
    nearClip = bpy.props.FloatProperty(name="nearClip", options={"ANIMATABLE"}, default=10.0)
    clip2 = bpy.props.FloatProperty(name="clip2", options={"ANIMATABLE"}, default=10.0)
    focalDepth = bpy.props.FloatProperty(name="focalDepth", options={"ANIMATABLE"}, default=2)
    falloffStart = bpy.props.FloatProperty(name="falloffStart", options={"ANIMATABLE"}, default=1.0)
    falloffEnd = bpy.props.FloatProperty(name="falloffEnd", options={"ANIMATABLE"}, default=2.0)
    depthOfField = bpy.props.FloatProperty(name="depthOfField", options={"ANIMATABLE"}, default=0.5)

class M3ParticleSystemCopy(bpy.types.PropertyGroup):
    name = bpy.props.StringProperty(options=set(), update=handleParticleSystemCopyRename)
    boneName = bpy.props.StringProperty(options=set())
    emissionRate = bpy.props.FloatProperty(default=10.0, name="emiss. rate", options={"ANIMATABLE"})
    partEmit = bpy.props.IntProperty(default=0, subtype="UNSIGNED", options={"ANIMATABLE"})

  
class M3Boundings(bpy.types.PropertyGroup):
    minBorder = bpy.props.FloatVectorProperty(name="minBorder", default=(0.0, 0.0, 0.0), size=3, subtype="XYZ", options={"ANIMATABLE"})
    maxBorder = bpy.props.FloatVectorProperty(name="maxBorder", default=(0.0, 0.0, 0.0), size=3, subtype="XYZ", options={"ANIMATABLE"})
    radius = bpy.props.FloatProperty(name="radius", options={"ANIMATABLE"}, default=0.5)


class M3ParticleSystem(bpy.types.PropertyGroup):

    # name attribute seems to be needed for template_list but is not actually in the m3 file
    # The name gets calculated like this: name = boneSuffix (type)
    name = bpy.props.StringProperty(options=set())
    boneSuffix = bpy.props.StringProperty(options=set(), update=handleParticleSystemTypeOrBoneSuffixChange, default="Particle System")
    boneName = bpy.props.StringProperty(options=set())
    updateBlenderBoneShapes = bpy.props.BoolProperty(default=True, options=set())
    materialName = bpy.props.StringProperty(options=set())
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
    emissionAreaType = bpy.props.EnumProperty(default="2", items=emissionAreaTypeList, update=handleParticleSystemTypeOrBoneSuffixChange, options=set())
    emissionAreaSize = bpy.props.FloatVectorProperty(default=(0.1, 0.1, 0.1), name="emis. area size", update=handleParticleSystemAreaSizeChange, size=3, subtype="XYZ", options={"ANIMATABLE"})
    tailUnk1 = bpy.props.FloatVectorProperty(default=(0.05, 0.05, 0.05), name="tail unk.", size=3, subtype="XYZ", options={"ANIMATABLE"})
    emissionAreaRadius = bpy.props.FloatProperty(default=2.0, name="emis. area radius", update=handleParticleSystemAreaSizeChange, options={"ANIMATABLE"})
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
    particleType = bpy.props.EnumProperty(default="0", items=particleTypeList, options=set())
    lengthWidthRatio = bpy.props.FloatProperty(default=1.0, name="lengthWidthRatio",options=set())
    forceChannels = bpy.props.BoolVectorProperty(default=tuple(32*[False]), size=32, subtype="LAYER", options=set(), description="If a force shares a force channel with a particle system then it affects it")
    copies = bpy.props.CollectionProperty(type=M3ParticleSystemCopy)
    copyIndex = bpy.props.IntProperty(options=set(), update=handlePartileSystemCopyIndexChanged)
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

class M3Force(bpy.types.PropertyGroup):
    # name attribute seems to be needed for template_list but is not actually in the m3 file
    # The name gets calculated like this: name = boneSuffix (type)
    name = bpy.props.StringProperty(options=set())
    updateBlenderBoneShape = bpy.props.BoolProperty(default=True, options=set())
    boneSuffix = bpy.props.StringProperty(options=set(), update=handleForceTypeOrBoneSuffixChange, default="Particle System")
    boneName = bpy.props.StringProperty(options=set())
    forceType = bpy.props.EnumProperty(default="0", items=forceTypeList, update=handleForceTypeOrBoneSuffixChange, options=set())
    forceChannels = bpy.props.BoolVectorProperty(default=tuple(32*[False]), size=32, subtype="LAYER", options=set(), description="If a force shares a force channel with a particle system then it affects it")
    forceStrength = bpy.props.FloatProperty(default=1.0, name="forceStrength", options={"ANIMATABLE"})
    forceRange = bpy.props.FloatProperty(default=1.0, name="forceRange", options={"ANIMATABLE"})
    unknownAt64 = bpy.props.FloatProperty(default=0.05, name="unknownAt64", options={"ANIMATABLE"})
    unknownAt84 = bpy.props.FloatProperty(default=0.05, name="unknownAt84", options={"ANIMATABLE"})

class M3PhysicsShape(bpy.types.PropertyGroup):
    name = bpy.props.StringProperty(options=set())
    updateBlenderBoneShapes = bpy.props.BoolProperty(default=True, options=set())
    offset = bpy.props.FloatVectorProperty(default=(0.0, 0.0, 0.0), size=3, subtype="XYZ", update=handlePhysicsShapeUpdate)
    rotationEuler = bpy.props.FloatVectorProperty(default=(0.0, 0.0, 0.0), size=3, subtype="EULER", unit="ROTATION", update=handlePhysicsShapeUpdate)
    scale = bpy.props.FloatVectorProperty(default=(1.0, 1.0, 1.0), size=3, subtype="XYZ", update=handlePhysicsShapeUpdate)
    shape = bpy.props.EnumProperty(default="0", items=physicsShapeTypeList, update=handlePhysicsShapeUpdate, options=set())
    meshObjectName = bpy.props.StringProperty(name="meshName", options=set())
    # TODO: convex hull properties...
    size0 = bpy.props.FloatProperty(default=1.0, name="size0", update=handlePhysicsShapeUpdate, options=set())
    size1 = bpy.props.FloatProperty(default=1.0, name="size1", update=handlePhysicsShapeUpdate, options=set())
    size2 = bpy.props.FloatProperty(default=1.0, name="size2", update=handlePhysicsShapeUpdate, options=set())

class M3RigidBody(bpy.types.PropertyGroup):
    name = bpy.props.StringProperty(options=set())
    boneName = bpy.props.StringProperty(name="boneName", update=handleRigidBodyBoneChange, options=set())
    unknownAt0 = bpy.props.FloatProperty(default=5.0, name="unknownAt0", options=set())
    unknownAt4 = bpy.props.FloatProperty(default=4.0, name="unknownAt4", options=set())
    unknownAt8 = bpy.props.FloatProperty(default=0.8, name="unknownAt8", options=set())
    # skip other unknown values for now
    physicsShapes = bpy.props.CollectionProperty(type=M3PhysicsShape)
    physicsShapeIndex = bpy.props.IntProperty(options=set())
    collidable = bpy.props.BoolProperty(default=True, options=set())
    walkable = bpy.props.BoolProperty(default=False, options=set())
    stackable = bpy.props.BoolProperty(default=False, options=set())
    simulateOnCollision = bpy.props.BoolProperty(default=False, options=set())
    ignoreLocalBodies = bpy.props.BoolProperty(default=False, options=set())
    alwaysExists = bpy.props.BoolProperty(default=False, options=set())
    doNotSimulate = bpy.props.BoolProperty(default=False, options=set())
    localForces = bpy.props.BoolVectorProperty(default=tuple(16*[False]), size=16, subtype="LAYER", options=set())
    wind = bpy.props.BoolProperty(default=False, options=set())
    explosion = bpy.props.BoolProperty(default=False, options=set())
    energy = bpy.props.BoolProperty(default=False, options=set())
    blood = bpy.props.BoolProperty(default=False, options=set())
    magnetic = bpy.props.BoolProperty(default=False, options=set())
    grass = bpy.props.BoolProperty(default=False, options=set())
    brush = bpy.props.BoolProperty(default=False, options=set())
    trees = bpy.props.BoolProperty(default=False, options=set())
    priority = bpy.props.IntProperty(default=0, options=set())

class M3AttachmentPoint(bpy.types.PropertyGroup):
    name = bpy.props.StringProperty(name="name", options=set())
    updateBlenderBone = bpy.props.BoolProperty(default=True, options=set())
    boneSuffix = bpy.props.StringProperty(name="boneSuffix", update=handleAttachmentPointTypeOrBoneSuffixChange)
    boneName = bpy.props.StringProperty(name="boneName", options=set())
    volumeType = bpy.props.EnumProperty(default="-1",update=handleAttachmentVolumeTypeChange, items=attachmentVolumeTypeList, options=set())
    volumeSize0 = bpy.props.FloatProperty(default=1.0, options=set(), update=handleAttachmentVolumeSizeChange)
    volumeSize1 = bpy.props.FloatProperty(default=0.0, options=set(), update=handleAttachmentVolumeSizeChange)
    volumeSize2 = bpy.props.FloatProperty(default=0.0, options=set(), update=handleAttachmentVolumeSizeChange)

class M3SimpleGeometricShape(bpy.types.PropertyGroup):
    name = bpy.props.StringProperty(name="name", default="", options=set())
    updateBlenderBoneShapes = bpy.props.BoolProperty(default=True, options=set())
    shape = bpy.props.EnumProperty(default="1", items=fuzzyHitTestShapeList,update=handleGeometicShapeUpdate, options=set())
    size0 = bpy.props.FloatProperty(default=1.0, update=handleGeometicShapeUpdate, options=set())
    size1 = bpy.props.FloatProperty(default=0.0, update=handleGeometicShapeUpdate, options=set())
    size2 = bpy.props.FloatProperty(default=0.0, update=handleGeometicShapeUpdate, options=set())
    offset = bpy.props.FloatVectorProperty(default=(0.0, 0.0, 0.0), size=3, subtype="XYZ", update=handleGeometicShapeUpdate,options=set())
    rotationEuler = bpy.props.FloatVectorProperty(default=(0.0, 0.0, 0.0), size=3, subtype="EULER", unit="ROTATION", update=handleGeometicShapeUpdate, options=set())
    scale = bpy.props.FloatVectorProperty(default=(1.0, 1.0, 1.0), size=3, subtype="XYZ", update=handleGeometicShapeUpdate, options=set())

class M3BoneVisiblityOptions(bpy.types.PropertyGroup):
    showFuzzyHitTests = bpy.props.BoolProperty(default=True, options=set(), update=handleFuzzyHitTestVisiblityUpdate)
    showTightHitTest = bpy.props.BoolProperty(default=True, options=set(), update=handleTightHitTestVisiblityUpdate)
    showAttachmentPoints = bpy.props.BoolProperty(default=True, options=set(), update=handleAttachmentPointVisibilityUpdate)
    showParticleSystems = bpy.props.BoolProperty(default=True, options=set(), update=handleParticleSystemsVisiblityUpdate)
    showLights = bpy.props.BoolProperty(default=True, options=set(), update=handleLightsVisiblityUpdate)
    showCameras = bpy.props.BoolProperty(default=True, options=set(), update=handleCamerasVisiblityUpdate)
    showPhysicsShapes = bpy.props.BoolProperty(default=True, options=set(), update=handlePhysicsShapeVisibilityUpdate)

class M3ExportOptions(bpy.types.PropertyGroup):
    path = bpy.props.StringProperty(name="path", default="ExportedModel.m3", options=set())

class M3Light(bpy.types.PropertyGroup):
    # name attribute seems to be needed for template_list but is not actually in the m3 file
    # The name gets calculated like this: name = boneSuffix (type)
    name = bpy.props.StringProperty(name="name", default="", options=set())
    updateBlenderBone = bpy.props.BoolProperty(default=True, options=set())
    lightType = bpy.props.EnumProperty(default="1", items=lightTypeList, options=set(), update=handleLightTypeOrBoneSuffixChange)
    boneSuffix = bpy.props.StringProperty(options=set(), update=handleLightTypeOrBoneSuffixChange, default="Particle System")
    boneName = bpy.props.StringProperty(options=set())
    lightColor = bpy.props.FloatVectorProperty(default=(1.0, 1.0, 1.0), size=3, subtype="COLOR", options={"ANIMATABLE"})
    lightIntensity = bpy.props.FloatProperty(default=1.0, name="Light Intensity", options={"ANIMATABLE"})
    specColor =  bpy.props.FloatVectorProperty(default=(1.0, 1.0, 1.0), size=3, subtype="COLOR", options={"ANIMATABLE"})
    specIntensity = bpy.props.FloatProperty(default=0.0, name="Specular Intensity", options={"ANIMATABLE"})
    attenuationNear = bpy.props.FloatProperty(default=2.5, name="attenuationNear", options={"ANIMATABLE"})
    unknownAt148 = bpy.props.FloatProperty(default=2.5, name="unknownAt148", options=set())
    attenuationFar = bpy.props.FloatProperty(default=3.0, name="attenuationFar", update=handleLightSizeChange, options={"ANIMATABLE"})
    hotSpot = bpy.props.FloatProperty(default=1.0, name="Hot Spot", options={"ANIMATABLE"})
    falloff = bpy.props.FloatProperty(default=1.0, name="Fall Off", update=handleLightSizeChange, options={"ANIMATABLE"})
    unknownAt12 = bpy.props.IntProperty(default=-1, name="unknownAt12", options=set())
    unknownAt8 = bpy.props.BoolProperty(default=False,options=set())
    shadowCast = bpy.props.BoolProperty(options=set())
    specular = bpy.props.BoolProperty(options=set())
    unknownFlag0x04 = bpy.props.BoolProperty(options=set())
    turnOn = bpy.props.BoolProperty(default=True,options=set())
    

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

class BoneVisibilityPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_M3_bone_visibility"
    bl_label = "M3 Bone Visibility"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.prop(scene.m3_bone_visiblity_options, "showFuzzyHitTests", text="Fuzzy Hit Tests")
        layout.prop(scene.m3_bone_visiblity_options, "showTightHitTest", text="Tight Hit Test")
        layout.prop(scene.m3_bone_visiblity_options, "showAttachmentPoints", text="Attachment Points")
        layout.prop(scene.m3_bone_visiblity_options, "showParticleSystems", text="Particle Systems")
        layout.prop(scene.m3_bone_visiblity_options, "showLights", text="Lights")
        layout.prop(scene.m3_bone_visiblity_options, "showCameras", text="Cameras")
        layout.prop(scene.m3_bone_visiblity_options, "showPhysicsShapes", text="Physics Shapes")

class AnimationSequencesPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_M3_animations"
    bl_label = "M3 Animation Sequences"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_options = {'DEFAULT_CLOSED'}

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
        
        if not len(scene.m3_rigid_bodies) > 0:
            return
        
        layout.separator()
        layout.prop(animation, 'useSimulateFrame', text="Use physics")
        if animation.useSimulateFrame:
            layout.prop(animation, 'simulateFrame', text="Simulate after frame")

class AnimationSequenceTransformationCollectionsPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_M3_STCs"
    bl_label = "M3 Animation STCs"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        row = layout.row()
        col = row.column()
        animationIndex = scene.m3_animation_index
        if animationIndex >= 0 and animationIndex < len(scene.m3_animations):
            animation = scene.m3_animations[animationIndex]

            col.template_list(animation, "transformationCollections", animation, "transformationCollectionIndex", rows=2)
            
            col = row.column(align=True)
            col.operator("m3.stc_add", icon='ZOOMIN', text="")
            col.operator("m3.stc_remove", icon='ZOOMOUT', text="")
            index = animation.transformationCollectionIndex
            if index >= 0 and index < len(animation.transformationCollections):
                transformationCollection = animation.transformationCollections[index]
                layout.separator()
                layout.prop(transformationCollection, 'name', text="Name")
                layout.prop(transformationCollection, 'runsConcurrent', text="Runs Concurrent")
                row = layout.row()
                col = row.column()
                col.operator("m3.stc_select", text="Select FCurves")
                col = row.column()
                col.operator("m3.stc_assign", text="Assign FCurves")
     
class MaterialReferencesPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_M3_material_references"
    bl_label = "M3 Materials"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_options = {'DEFAULT_CLOSED'}

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
    bl_options = {'DEFAULT_CLOSED'}

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
                layout.prop(material, 'darkNormalMapping', text="Dark Normal Mapping")
            elif materialType == shared.displacementMaterialTypeIndex:
                material = scene.m3_displacement_materials[materialIndex]
                layout.prop(material, 'name', text="Name")
                layout.prop(material, 'strengthFactor', text="Strength Factor")
                layout.prop(material, 'priority', text="Priority")
            elif materialType == shared.compositeMaterialTypeIndex:
                material = scene.m3_composite_materials[materialIndex]
                layout.prop(material, 'name', text="Name")
                layout.label("Sections:")
                row = layout.row()
                col = row.column()
                col.template_list(material, "sections", material, "sectionIndex", rows=2)
                
                col = row.column(align=True)
                col.operator("m3.composite_material_add_section", icon='ZOOMIN', text="")
                col.operator("m3.composite_material_remove_section", icon='ZOOMOUT', text="")
                sectionIndex = material.sectionIndex
                if (sectionIndex >= 0) and (sectionIndex < len(material.sections)):
                    section = material.sections[sectionIndex]
                    layout.prop_search(section, 'name', scene, 'm3_material_references', text="Material", icon='NONE')
                    layout.prop(section, "alphaFactor", text="Alpha Factor")
                
            elif materialType == shared.terrainMaterialTypeIndex:
                material = scene.m3_terrain_materials[materialIndex]
                layout.prop(material, 'name', text="Name")
            elif materialType == shared.volumeMaterialTypeIndex:
                material = scene.m3_volume_materials[materialIndex]
                layout.prop(material, 'name', text="Name")
                layout.prop(material, 'volumeDensity', text="Volume Density")
            else:
                layout.label(text=("Unsupported material type %d" % materialType))

class MatrialLayersPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_M3_material_layers"
    bl_label = "M3 Material Layers"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_options = {'DEFAULT_CLOSED'}
    
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
            
            material = shared.getMaterial(scene, materialType, materialIndex)
            if material != None:
                col.template_list(material, "layers", scene, "m3_material_layer_index", rows=2)
                layerIndex = scene.m3_material_layer_index
                if layerIndex >= 0 and layerIndex < len(material.layers):
                    layer = material.layers[layerIndex]
                    layout.prop(layer, 'imagePath', text="Image Path")
                    layout.prop(layer, 'uvSource', text="UV Source")
                    layout.prop(layer, 'unknown11', text="Unknown11")
                    layout.prop(layer, 'textureWrapX', text="Tex. Wrap X")
                    layout.prop(layer, 'textureWrapY', text="Tex. Wrap Y")
                    layout.prop(layer, 'alphaAsTeamColor', text="Alpha As Team Color")
                    layout.prop(layer, 'alphaOnly', text="Alpha Only")
                    layout.prop(layer, 'alphaBasedShading', text="Alpha Based Shading")
                    layout.prop(layer, 'useTint', text="Use Tint")
                    layout.prop(layer, 'tintAlpha', text="Tint Alpha")
                    layout.prop(layer, 'tintStrength', text="Tint Strength")
                    layout.prop(layer, 'tintStart', text="Tint Start")
                    layout.prop(layer, 'tintCutout', text="Tint Cutout")
                    split = layout.split()
                    row = split.row()
                    row.prop(layer, 'colorEnabled', text="Color:")
                    sub = row.column(align=True)
                    sub.active = layer.colorEnabled
                    sub.prop(layer, 'color', text="")
                    
                                        
                    split = layout.split()
                    col = split.column()
                    sub = col.column(align=True)
                    sub.label(text="UV Offset:")
                    sub.prop(layer, "uvOffset", text="X", index=0)
                    sub.prop(layer, "uvOffset", text="Y", index=1)

                    split = layout.split()
                    col = split.column()
                    sub = col.column(align=True)
                    sub.label(text="UV Angle:")
                    sub.prop(layer, "uvAngle", text="X", index=0)
                    sub.prop(layer, "uvAngle", text="Y", index=1)
                    sub.prop(layer, "uvAngle", text="Z", index=2)

                    split = layout.split()
                    col = split.column()
                    sub = col.column(align=True)
                    sub.label(text="UV Tiling:")
                    sub.prop(layer, "uvTiling", text="X", index=0)
                    sub.prop(layer, "uvTiling", text="Y", index=1)
                    
                    split = layout.split()
                    col = split.column()
                    sub = col.column(align=True)
                    sub.label(text="Brightness:")
                    sub.prop(layer, "brightness", text="")
                    sub.prop(layer, "brightMult", text="Multiplier")
                    sub.prop(layer, "midtoneOffset", text="Midtone Offset")
        else:
            col.label(text="No properties to display")

class CameraPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_M3_cameras"
    bl_label = "M3 Cameras"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        row = layout.row()
        col = row.column()
        col.template_list(scene, "m3_cameras", scene, "m3_camera_index", rows=2)

        col = row.column(align=True)
        col.operator("m3.cameras_add", icon='ZOOMIN', text="")
        col.operator("m3.cameras_remove", icon='ZOOMOUT', text="")
        currentIndex = scene.m3_camera_index
        if currentIndex >= 0 and currentIndex < len(scene.m3_cameras):
            camera = scene.m3_cameras[currentIndex]
            layout.separator()
            layout.prop(camera, 'name',text="Name")
            layout.prop(camera, 'fieldOfView',text="Field Of View")
            layout.prop(camera, 'farClip',text="Far Clip")
            layout.prop(camera, 'nearClip',text="Near Clip")
            layout.prop(camera, 'clip2',text="Clip 2")
            layout.prop(camera, 'focalDepth',text="Focal Depth")
            layout.prop(camera, 'falloffStart',text="Falloff Start")
            layout.prop(camera, 'falloffEnd',text="Falloff End")
            layout.prop(camera, 'depthOfField',text="Depth Of Field")

            
class ParticleSystemsPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_M3_particles"
    bl_label = "M3 Particle Systems"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_options = {'DEFAULT_CLOSED'}

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
            layout.prop_search(particle_system, 'materialName', scene, 'm3_material_references', text="Material", icon='NONE')
            split = layout.split()
            col = split.column()
            col.row().label("Emis. Area:")
            col = col.row().column(align=True)
            col.prop(particle_system, 'emissionAreaType', text="")
            sub = col.row()
            sub.active = particle_system.emissionAreaType in emissionAreaTypesWithLength
            sub.prop(particle_system, 'emissionAreaSize', index=0, text="Length")
            sub =  col.row()
            sub.active = particle_system.emissionAreaType in emissionAreaTypesWithWidth
            sub.prop(particle_system, 'emissionAreaSize', index=1, text="Width")
            sub = col.row()
            sub.active = particle_system.emissionAreaType in emissionAreaTypesWithHeight
            sub.prop(particle_system, 'emissionAreaSize', index=2, text="Height")
            sub = col.row()
            sub.active = particle_system.emissionAreaType in emissionAreaTypesWithRadius
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


            split = layout.split()
            col = split.column()
            col.prop(particle_system, 'particleType', text="Particle Type")
            sub = col.column(align=True)
            sub.active = particle_system.particleType in ["1", "6"]
            sub.prop(particle_system, 'lengthWidthRatio', text="Length/Width Ratio")
            
            layout.prop(particle_system, 'forceChannels', text="Force Channels")

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



class ForcePanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_M3_forces"
    bl_label = "M3 Forces"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        row = layout.row()
        col = row.column()
        col.template_list(scene, "m3_forces", scene, "m3_force_index", rows=2)

        col = row.column(align=True)
        col.operator("m3.forces_add", icon='ZOOMIN', text="")
        col.operator("m3.forces_remove", icon='ZOOMOUT', text="")
        currentIndex = scene.m3_force_index
        if currentIndex >= 0 and currentIndex < len(scene.m3_forces):
            force = scene.m3_forces[currentIndex]
            layout.separator()
            layout.prop(force, 'boneSuffix', text="Name")
            layout.prop(force, "forceType", text="Type")
            layout.prop(force, "forceChannels", text="Channels")
            layout.prop(force, "forceStrength", text="Strength")
            layout.prop(force, "forceRange", text="Range")
            layout.prop(force, "unknownAt64", text="Unknown 1")
            layout.prop(force, "unknownAt84", text="Unknown 2")

class RigidBodyPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_M3_rigid_bodies"
    bl_label = "M3 Rigid Bodies"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        row = layout.row()
        col = row.column()
        col.template_list(scene, "m3_rigid_bodies", scene, "m3_rigid_body_index", rows=2)
        
        col = row.column(align=True)
        col.operator("m3.rigid_bodies_add", icon='ZOOMIN', text="")
        col.operator("m3.rigid_bodies_remove", icon='ZOOMOUT', text="")
        
        currentIndex = scene.m3_rigid_body_index
        if not 0 <= currentIndex < len(scene.m3_rigid_bodies):
            return
        rigid_body = scene.m3_rigid_bodies[currentIndex]
        
        layout.separator()
        layout.prop(rigid_body, 'name', text="Name")
        layout.prop(rigid_body, 'boneName', text="Bone")
        
        # TODO: Bone selection from list would be ideal.
        # This is almost correct, but bpy.data contains deleted items too. :(
        #if bpy.data.armatures:
        #    sub.prop_search(rigid_body, 'armatureName', bpy.data, "armatures", text="Armature")    
        #    if rigid_body.armatureName and bpy.data.armatures[rigid_body.armatureName]:
        #        sub.prop_search(rigid_body, 'boneName', bpy.data.armatures[rigid_body.armatureName], "bones", text="Bone")
        
        split = layout.split()
        col = split.column()
        sub = col.column(align=True)
        sub.label(text="Collision Flags:")
        sub.prop(rigid_body, 'collidable', text="Collidable")
        sub.prop(rigid_body, 'walkable', text="Walkable")
        sub.prop(rigid_body, 'stackable', text="Stackable")
        sub.prop(rigid_body, 'simulateOnCollision', text="Simulate On Collision")
        sub.prop(rigid_body, 'ignoreLocalBodies', text="Ignore Local Bodies")
        sub.prop(rigid_body, 'alwaysExists', text="Always Exists")
        sub.prop(rigid_body, 'doNotSimulate', text="Do Not Simulate")
        
        layout.prop(rigid_body, 'localForces', text="Local Forces")
        
        split = layout.split()
        col = split.column()
        sub = col.column(align=True)
        sub.label(text="World Forces:")
        sub.prop(rigid_body, 'wind', text="Wind")
        sub.prop(rigid_body, 'explosion', text="Explosion")
        sub.prop(rigid_body, 'energy', text="Energy")
        sub.prop(rigid_body, 'blood', text="Blood")
        sub.prop(rigid_body, 'magnetic', text="Magnetic")
        sub.prop(rigid_body, 'grass', text="Grass")
        sub.prop(rigid_body, 'brush', text="Brush")
        sub.prop(rigid_body, 'trees', text="Trees")
        
        layout.prop(rigid_body, 'priority', text="Priority")

class PhyscisShapePanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_M3_physics_shapes"
    bl_label = "M3 Physics Shapes"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        row = layout.row()
        col = row.column()
        
        currentIndex = scene.m3_rigid_body_index
        if not 0 <= currentIndex < len(scene.m3_rigid_bodies):
            layout.label("No rigid body has been selected")
            return
        rigid_body = scene.m3_rigid_bodies[currentIndex]
        
        col.template_list(rigid_body, "physicsShapes", rigid_body, "physicsShapeIndex", rows=2)
        col = row.column(align=True)
        col.operator("m3.physics_shapes_add", icon='ZOOMIN', text="")
        col.operator("m3.physics_shapes_remove", icon='ZOOMOUT', text="")
        
        currentIndex = rigid_body.physicsShapeIndex
        if not 0 <= currentIndex < len(rigid_body.physicsShapes):
            return
        physics_shape = rigid_body.physicsShapes[currentIndex]
        
        layout.separator()
        layout.prop(physics_shape, 'name', text="Name")
        
        addUIForShapeProperties(layout, physics_shape)

class LightPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_M3_lights"
    bl_label = "M3 Lights"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        row = layout.row()
        col = row.column()
        col.template_list(scene, "m3_lights", scene, "m3_light_index", rows=2)

        col = row.column(align=True)
        col.operator("m3.lights_add", icon='ZOOMIN', text="")
        col.operator("m3.lights_remove", icon='ZOOMOUT', text="")
        currentIndex = scene.m3_light_index
        if currentIndex >= 0 and currentIndex < len(scene.m3_lights):
            light = scene.m3_lights[currentIndex]
            layout.separator()
            layout.prop(light, 'boneSuffix', text="Name")
            layout.prop(light, "lightType", text="Light Type")
            layout.prop(light, "lightColor", text="Light Color")
            layout.prop(light, "lightIntensity", text="Light Intensity")
            
            split = layout.split()
            col = split.column()
            col.prop(light, "specular", text="Use Specular")
            sub = col.column(align=True)
            sub.active = light.specular
            sub.prop(light, "specColor", text="")
            sub.prop(light, "specIntensity", text="Specular Intensity")
            
            split = layout.split()
            col = split.column()
            col.label(text="Attenuation:");
            sub = col.row(align=True)
            sub.prop(light, "attenuationNear", text="Near")
            sub.prop(light, "attenuationFar", text="Far")
            layout.prop(light, "unknownAt148", text="unknownAt148")
            layout.prop(light, "hotSpot", text="Hot Spot")
            layout.prop(light, "falloff", text="Fall Off")
            layout.prop(light, "unknownAt12", text="unknownAt12")
            layout.prop(light, "shadowCast", text="Shadow Cast")
            layout.prop(light, "unknownFlag0x04", text="Unknown Flag 0x04")
            layout.prop(light, "turnOn", text="Turn On")
            layout.prop(light, "unknownAt8", text="unknownAt8")


            
class ParticleSystemCopiesPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_M3_particle_copies"
    bl_label = "M3 Particle Systems Copies"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        row = layout.row()
        col = row.column()
        
        particleSystemIndex = scene.m3_particle_system_index
        if not(particleSystemIndex >= 0 and particleSystemIndex < len(scene.m3_particle_systems)):
            layout.label("No particle system has been selected")
            return
        particle_system = scene.m3_particle_systems[particleSystemIndex]
        copyIndex = particle_system.copyIndex            
        col.template_list(particle_system, "copies", particle_system, "copyIndex", rows=2)

        col = row.column(align=True)
        col.operator("m3.particle_system_copies_add", icon='ZOOMIN', text="")
        col.operator("m3.particle_system_copies_remove", icon='ZOOMOUT', text="")
        if copyIndex >= 0 and copyIndex < len(particle_system.copies):
            copy = particle_system.copies[copyIndex]
            layout.separator()
            layout.prop(copy, 'name',text="Name")
            layout.prop(copy, 'emissionRate', text="Particles Per Second")
            layout.prop(copy, 'partEmit', text="Part. Emit.")

class MaterialSelectionPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_M3_material_selection"
    bl_label = "M3 Material Settings"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "material"
 
    @classmethod
    def poll(cls, context):
        o = context.object
        return o and (o.data != None) and (o.type == 'MESH')
 
    def draw(self, context):
        scene = context.scene
        layout = self.layout
        meshObject = context.object
        mesh = meshObject.data
        layout.prop_search(mesh, 'm3_material_name', scene, 'm3_material_references', text="M3 Material", icon='NONE')

class AttachmentPointsPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_M3_attachments"
    bl_label = "M3 Attachment Points"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_options = {'DEFAULT_CLOSED'}
    
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
            layout.prop(attachment_point, 'boneSuffix', text="Name")
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


def addUIForShapeProperties(layout, shapeObject):
    layout.prop(shapeObject, 'shape', text="Shape: ")
    
    if shapeObject.shape in ["0", "1", "2", "3"]:
        split = layout.split()
        col = split.column()
        sub = col.column(align=True)
        sub.label(text="Dimensions")
        if shapeObject.shape in ["0"]: #cuboid
            sub.prop(shapeObject, "size0", text="Width")
            sub.prop(shapeObject, "size1", text="Length")
            sub.prop(shapeObject, "size2", text="Height")
        elif shapeObject.shape in ["1"]: #sphere
            sub.prop(shapeObject, "size0", text="Radius")
        elif shapeObject.shape in ["2"]: #capsule
            sub.prop(shapeObject, "size0", text="Radius")
            sub.prop(shapeObject, "size1", text="Height")
        elif shapeObject.shape in ["3"]: #cylinder
            sub.prop(shapeObject, "size0", text="Radius")
            sub.prop(shapeObject, "size1", text="Height")
    
    split = layout.split()
    col = split.column()
    sub = col.column(align=True)
    
    sub.label(text="Offset")
    sub.prop(shapeObject, 'offset', index=0, text="X")
    sub.prop(shapeObject, 'offset', index=1, text="Y")
    sub.prop(shapeObject, 'offset', index=2, text="Z")
    
    sub.label(text="Rotation (Euler)")
    sub.prop(shapeObject, 'rotationEuler', index=0, text="X")
    sub.prop(shapeObject, 'rotationEuler', index=1, text="Y")
    sub.prop(shapeObject, 'rotationEuler', index=2, text="Z")
    
    sub.label(text="Scale")
    sub.prop(shapeObject, 'scale', index=0, text="X")
    sub.prop(shapeObject, 'scale', index=1, text="Y")
    sub.prop(shapeObject, 'scale', index=2, text="Z")

class FuzzyHitTestPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_M3_fuzzyhittests"
    bl_label = "M3 Fuzzy Hit Tests"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        row = layout.row()
        col = row.column()
        col.template_list(scene, "m3_fuzzy_hit_tests", scene, "m3_fuzzy_hit_test_index", rows=2)

        col = row.column(align=True)
        col.operator("m3.fuzzy_hit_tests_add", icon='ZOOMIN', text="")
        col.operator("m3.fuzzy_hit_tests_remove", icon='ZOOMOUT', text="")

        currentIndex = scene.m3_fuzzy_hit_test_index
        if currentIndex >= 0 and currentIndex < len(scene.m3_fuzzy_hit_tests):
            fuzzy_hit_test = scene.m3_fuzzy_hit_tests[currentIndex]
            layout.separator()
            addUIForShapeProperties(layout, fuzzy_hit_test)

class TightHitTestPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_M3_tighthittest"
    bl_label = "M3 Tight Hit Test"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        if scene.m3_tight_hit_test.name == "":
            layout.operator("m3.tight_hit_test_select_or_create_bone", text="Create Bone")
        else:
            layout.operator("m3.tight_hit_test_select_or_create_bone", text="Select Bone")

        split = layout.split()
        row = split.row()
        sub = row.column(align=False)
        sub.active = scene.m3_tight_hit_test.name != ""
        addUIForShapeProperties(sub, scene.m3_tight_hit_test)

class BoundingsPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_M3_boundings"
    bl_label = "M3 Boundings"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        boundingsObject = scene.m3_boundings
        
        split = layout.split()
        col = split.column()
        sub = col.column(align=True)
        sub.label(text="Min")
        sub.prop(boundingsObject, 'minBorder', index=0, text="X")
        sub.prop(boundingsObject, 'minBorder', index=1, text="Y")
        sub.prop(boundingsObject, 'minBorder', index=2, text="Z")
        col = split.column()
        sub = col.column(align=True)
        sub.label(text="Max")
        sub.prop(boundingsObject, 'maxBorder', index=0, text="X")
        sub.prop(boundingsObject, 'maxBorder', index=1, text="Y")
        sub.prop(boundingsObject, 'maxBorder', index=2, text="Z")
        layout.prop(boundingsObject, 'radius', text="Radius")

class ExtraBonePropertiesPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_M3_bone_properties"
    bl_label = "M3 Bone Properties"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "bone"
    
    def draw(self, context):
        layout = self.layout
        bone = context.bone
        row = layout.row()
        col = row.column()
        layout.prop(bone, 'm3_unapplied_scale', text="Unapplied Scale")



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
        defaultSettingDisplacement = "DISPLACEMENT"
        defaultSettingComposite = "COMPOSITE"
        defaultSettingTerrain = "TERRAIN"
        defaultSettingVolume = "VOLUME"

        if self.defaultSetting in [defaultSettingMesh, defaultSettingParticle]:
            materialType = shared.standardMaterialTypeIndex
            materialIndex = len(scene.m3_standard_materials)
            material = scene.m3_standard_materials.add()
            for (layerName, layerFieldName) in zip(shared.standardMaterialLayerNames, shared.standardMaterialLayerFieldNames):
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
        elif self.defaultSetting == defaultSettingDisplacement:
            materialType = shared.displacementMaterialTypeIndex
            materialIndex = len(scene.m3_displacement_materials)
            material = scene.m3_displacement_materials.add()
            for (layerName, layerFieldName) in zip(shared.displacementMaterialLayerNames, shared.displacementMaterialLayerFieldNames):
                layer = material.layers.add()
                layer.name = layerName
        elif self.defaultSetting == defaultSettingComposite:
            materialType = shared.compositeMaterialTypeIndex
            materialIndex = len(scene.m3_composite_materials)
            material = scene.m3_composite_materials.add()
        elif self.defaultSetting == defaultSettingTerrain:
            materialType = shared.terrainMaterialTypeIndex
            materialIndex = len(scene.m3_terrain_materials)
            material = scene.m3_terrain_materials.add()
            for (layerName, layerFieldName) in zip(shared.terrainMaterialLayerNames, shared.terrainMaterialLayerFieldNames):
                layer = material.layers.add()
                layer.name = layerName
        elif self.defaultSetting == defaultSettingVolume:
            materialType = shared.volumeMaterialTypeIndex
            materialIndex = len(scene.m3_volume_materials)
            material = scene.m3_volume_materials.add()
            for (layerName, layerFieldName) in zip(shared.volumeMaterialLayerNames, shared.volumeMaterialLayerFieldNames):
                layer = material.layers.add()
                layer.name = layerName
        elif self.defaultSetting == defaultSettingTerrain:
            materialType = shared.volumeMaterialTypeIndex
            materialIndex = len(scene.m3_volume_materials)
            material = scene.m3_volume_materials.add()
            for (layerName, layerFieldName) in zip(shared.volumeMaterialLayerNames, shared.volumeMaterialLayerFieldNames):
                layer = material.layers.add()
                layer.name = layerName
        materialReferenceIndex = len(scene.m3_material_references)
        materialReference = scene.m3_material_references.add()
        materialReference.materialIndex = materialIndex
        materialReference.materialType = materialType
        material.materialReferenceIndex = materialReferenceIndex
        material.name = self.name # will also set materialReference name


        scene.m3_material_reference_index = len(scene.m3_material_references)-1
        return {'FINISHED'}
    def findUnusedName(self, scene):
        usedNames = set()
        for materialReferenceIndex in range(0, len(scene.m3_material_references)):
            materialReference = scene.m3_material_references[materialReferenceIndex]
            material = shared.getMaterial(scene, materialReference.materialType, materialReference.materialIndex)
            if material != None:
                usedNames.add(material.name)
        unusedName = None
        counter = 1
        while unusedName == None:
            suggestedName = "%02d" % counter
            if not suggestedName in usedNames:
                unusedName = suggestedName
            counter += 1
        return unusedName

class M3_MATERIALS_OT_remove(bpy.types.Operator):
    bl_idname      = 'm3.materials_remove'
    bl_label       = "Remove M3 Material"
    bl_description = "Removes the active M3 Material"
    
    def invoke(self, context, event):
        scene = context.scene
        referenceIndex = scene.m3_material_reference_index
        if referenceIndex>= 0:
            materialReference = scene.m3_material_references[referenceIndex]
            materialName = materialReference.name
            # Check if material is in use, and abort:
            for particle_system in scene.m3_particle_systems:
                if particle_system.materialName == materialName:
                    self.report({"ERROR"}, "Can't delete: The particle system '%s' is using this material" % particle_system.name)
                    return {"CANCELLED"}
            for meshObject in shared.findMeshObjects(scene):
                mesh = meshObject.data
                if mesh.m3_material_name == materialName:
                    self.report({"ERROR"}, "Can't delete: The object '%s' (mesh '%s') is using this material." % (meshObject.name, mesh.name))
                    return {"CANCELLED"}
            
            for higherReferenceIndex in range(referenceIndex+1,len(scene.m3_material_references)):
                higherReference = scene.m3_material_references[higherReferenceIndex]
                material = shared.getMaterial(scene, higherReference.materialType, higherReference.materialIndex)
                if material != None:
                    material.materialReferenceIndex -= 1
                    
            materialReference = scene.m3_material_references[referenceIndex]
            materialIndex = materialReference.materialIndex
            materialType = materialReference.materialType
            
            for otherReference in scene.m3_material_references:
                if otherReference.materialType == materialType and otherReference.materialIndex > materialIndex:
                    otherReference.materialIndex -= 1

            if materialType == shared.standardMaterialTypeIndex:
                scene.m3_standard_materials.remove(materialIndex)
            
            scene.m3_material_references.remove(scene.m3_material_reference_index)
            scene.m3_material_reference_index -= 1
        return{'FINISHED'}

class M3_COMPOSITE_MATERIAL_OT_add_section(bpy.types.Operator):
    bl_idname      = 'm3.composite_material_add_section'
    bl_label       = "Add a section/layer to the composite material"
    bl_description = "Adds a section/layer to the composite material"

    def invoke(self, context, event):
        scene = context.scene
        materialIndex = scene.m3_material_reference_index
        if materialIndex >= 0 and materialIndex < len(scene.m3_material_references):
            materialReference = scene.m3_material_references[materialIndex]
            materialType = materialReference.materialType
            materialIndex = materialReference.materialIndex
            if materialType == shared.compositeMaterialTypeIndex:
                material = shared.getMaterial(scene, materialType, materialIndex)
                section = material.sections.add()
                if len(scene.m3_material_references) >= 1:
                    section.name = scene.m3_material_references[0].name
                material.sectionIndex = len(material.sections)-1                
        return{'FINISHED'}

class M3_COMPOSITE_MATERIAL_OT_remove_section(bpy.types.Operator):
    bl_idname      = 'm3.composite_material_remove_section'
    bl_label       = "Removes the selected section/layer from the composite material"
    bl_description = "Removes the selected section/layer from the composite material"

    def invoke(self, context, event):
        scene = context.scene
        materialIndex = scene.m3_material_reference_index
        if materialIndex >= 0 and materialIndex < len(scene.m3_material_references):
            materialReference = scene.m3_material_references[materialIndex]
            materialType = materialReference.materialType
            materialIndex = materialReference.materialIndex
            if materialType == shared.compositeMaterialTypeIndex:
                material = shared.getMaterial(scene, materialType, materialIndex)
                sectionIndex = material.sectionIndex
                if (sectionIndex >= 0) and (sectionIndex < len(material.sections)):
                    material.sections.remove(sectionIndex)
                    material.sectionIndex = material.sectionIndex-1                
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

class M3_ANIMATIONS_OT_STC_add(bpy.types.Operator):
    bl_idname      = 'm3.stc_add'
    bl_label       = "Add STC to animation"
    bl_description = "Adds a new sequence transformation collection to the active animation sequence"
    
    def invoke(self, context, event):
        scene = context.scene
        if scene.m3_animation_index >= 0:
            animation = scene.m3_animations[scene.m3_animation_index]
            stcIndex = len(animation.transformationCollections)
            stc = animation.transformationCollections.add()
            stc.name = self.findUnusedName(animation.transformationCollections)
            animation.transformationCollectionIndex = stcIndex

        return{'FINISHED'}
        
    def findUnusedName(self, existingSTCs):
        usedNames = set()
        for stc in existingSTCs:
            usedNames.add(stc.name)
        suggestedNames = ["full"]
        unusedName = None
        for suggestedName in suggestedNames:
            if not suggestedName in usedNames:
                unusedName = suggestedName
                break
        counter = 2
        while unusedName == None:
            suggestedName = "%02d" % counter
            if not suggestedName in usedNames:
                unusedName = suggestedName
            counter += 1
        return unusedName
        
class M3_ANIMATIONS_OT_STC_remove(bpy.types.Operator):
    bl_idname      = 'm3.stc_remove'
    bl_label       = "Remove STC from animation"
    bl_description = "Removes the active STC from animation sequence"
    
    def invoke(self, context, event):
        scene = context.scene
        if scene.m3_animation_index >= 0:
            animation = scene.m3_animations[scene.m3_animation_index]
            stcIndex = animation.transformationCollectionIndex
            if stcIndex >= 0 and stcIndex < len(animation.transformationCollections):
                animation.transformationCollections.remove(stcIndex)
                animation.transformationCollectionIndex -= 1

        return{'FINISHED'}

class M3_ANIMATIONS_OT_STC_select(bpy.types.Operator):
    bl_idname      = 'm3.stc_select'
    bl_label       = "Select all FCurves of the active STC"
    bl_description = "Selects all FCURVES of the active sequence transformation collection"
    
    def invoke(self, context, event):
        scene = context.scene        
        longAnimIds = set()
        
        stc = None
        if scene.m3_animation_index >= 0:
            animation = scene.m3_animations[scene.m3_animation_index]
            stcIndex = animation.transformationCollectionIndex
            if stcIndex >= 0 and stcIndex < len(animation.transformationCollections):
                stc = animation.transformationCollections[stcIndex]
        if stc != None:
            for animatedProperty in stc.animatedProperties:
                longAnimId = animatedProperty.longAnimId
                longAnimIds.add(longAnimId)
                        
        for obj in bpy.data.objects:
            if obj.type == "ARMATURE":
                armature = obj.data
                selectObject = False
                for bone in armature.bones:
                    animPathPrefix = 'pose.bones["' + bone.name + '"].'
                    objectId = shared.animObjectIdArmature
                    boneLongAnimIds = set()
                    rotLongAnimId = shared.getLongAnimIdOf(objectId, animPathPrefix + "rotation_quaternion")
                    locLongAnimId = shared.getLongAnimIdOf(objectId, animPathPrefix + "location")
                    scaleLongAnimId = shared.getLongAnimIdOf(objectId, animPathPrefix + "scale")
                    if (rotLongAnimId in longAnimIds) or (locLongAnimId in longAnimIds) or (scaleLongAnimId in longAnimIds):
                        bone.select = True
                        selectObject = True
                    else:
                        bone.select = False
                # Select object at the end, otherwise Blender 2.63a
                # does not notice bone selection even if object is already selected
                obj.select = selectObject
                if obj.animation_data != None:
                    action = obj.animation_data.action
                    if action != None:
                        for fcurve in action.fcurves:
                            animPath = fcurve.data_path
                            objectId = shared.animObjectIdArmature
                            longAnimId = shared.getLongAnimIdOf(objectId, animPath)
                            fcurve.select = longAnimId in longAnimIds
                        
        if scene.animation_data != None:
            action = scene.animation_data.action
            if action != None:
                for fcurve in action.fcurves:
                    animPath = fcurve.data_path
                    objectId = shared.animObjectIdScene
                    longAnimId = shared.getLongAnimIdOf(objectId, animPath)
                    fcurve.select = longAnimId in longAnimIds
                        
                    
        return{'FINISHED'}


    
class M3_ANIMATIONS_OT_STC_assign(bpy.types.Operator):
    bl_idname      = 'm3.stc_assign'
    bl_label       = "Assign FCurves to STC"
    bl_description = "Assigns all selected FCurves to the active STC"
    
    def invoke(self, context, event):
        scene = context.scene
        if scene.m3_animation_index < 0:
            return {'FINISHED'}
        
        selectedLongAnimIds = set(self.getSelectedLongAnimIdsOfCurrentActions(scene))

        animation = scene.m3_animations[scene.m3_animation_index]
        selectedSTCIndex = animation.transformationCollectionIndex
        
        for stcIndex, stc in enumerate(animation.transformationCollections):
            if stcIndex == selectedSTCIndex:
                stc.animatedProperties.clear()
                for longAnimId in selectedLongAnimIds:
                    animatedProperty = stc.animatedProperties.add()
                    animatedProperty.longAnimId = longAnimId
            else:
                #Remove selected properties from the other STCs:
                longAnimIds = set()
                for animatedProperty in stc.animatedProperties:
                    longAnimIds.add(longAnimIds.longAnimId)
                longAnimIds = longAnimIds - selectedLongAnimIds
                stc.animatedProperties.clear()
                for longAnimId in longAnimIds:
                    animatedProperty = stc.animatedProperties.add()
                    animatedProperty.longAnimId = longAnimId

        return{'FINISHED'}
           
                
    def getSelectedAnimationPaths(self, objectWithAnimData):
        if objectWithAnimData.animation_data != None:
            action = objectWithAnimData.animation_data.action
            if action != None:
                for fcurve in action.fcurves:
                    if fcurve.select:
                        animPath = fcurve.data_path
                        yield animPath

    def getSelectedLongAnimIdsOfCurrentActions(self, scene):
        for obj in bpy.data.objects:
            if obj.type == "ARMATURE":
                for animPath in self.getSelectedAnimationPaths(obj):
                    yield shared.getLongAnimIdOf(shared.animObjectIdArmature, animPath)
        for animPath in self.getSelectedAnimationPaths(scene):          
            yield shared.getLongAnimIdOf(shared.animObjectIdScene, animPath)
            
class M3_CAMERAS_OT_add(bpy.types.Operator):
    bl_idname      = 'm3.cameras_add'
    bl_label       = "Add M3 Camera"
    bl_description = "Adds a camera description for the export as m3"

    def invoke(self, context, event):
        scene = context.scene
        camera = scene.m3_cameras.add()
        camera.name = self.findUnusedName(scene)

        scene.m3_camera_index = len(scene.m3_cameras)-1
        
        selectOrCreateBoneForCamera(scene, camera)
        return{'FINISHED'}

    def findUnusedName(self, scene):
        usedNames = set()
        for camera in scene.m3_cameras:
            usedNames.add(camera.name)
        
        suggestedNames = ["CameraPortrait", "CameraAvatar"]
        unusedName = None
        for suggestedName in suggestedNames:
            if not suggestedName in usedNames:
                unusedName = suggestedName
                break
        counter = 1
        while unusedName == None:
            suggestedName = "Camera %02d" % counter
            if not suggestedName in usedNames:
                unusedName = suggestedName
            counter += 1
        return unusedName


class M3_CAMERAS_OT_remove(bpy.types.Operator):
    bl_idname      = 'm3.cameras_remove'
    bl_label       = "Remove Camera"
    bl_description = "Removes the active M3 camera"
    
    def invoke(self, context, event):
        scene = context.scene
        if scene.m3_camera_index >= 0:
                scene.m3_cameras.remove(scene.m3_camera_index)
                scene.m3_camera_index-= 1
        return{'FINISHED'}

 

class M3_PARTICLE_SYSTEMS_OT_add(bpy.types.Operator):
    bl_idname      = 'm3.particle_systems_add'
    bl_label       = "Add Particle System"
    bl_description = "Adds a particle system for the export to the m3 model format"

    def invoke(self, context, event):
        scene = context.scene
        particle_system = scene.m3_particle_systems.add()
        particle_system.boneSuffix = findUnusedParticleSystemName(scene)
        if len(scene.m3_material_references) >= 1:
            particle_system.materialName = scene.m3_material_references[0].name

        handleParticleSystemTypeOrBoneSuffixChange(particle_system, context)
        
        # The following selection causes a new bone to be created:
        scene.m3_particle_system_index = len(scene.m3_particle_systems)-1
        return{'FINISHED'}

  

class M3_PARTICLE_SYSTEMS_OT_remove(bpy.types.Operator):
    bl_idname      = 'm3.particle_systems_remove'
    bl_label       = "Remove Particle System"
    bl_description = "Removes the active M3 particle system"
    
    def invoke(self, context, event):
        scene = context.scene
        if scene.m3_particle_system_index >= 0:
            particleSystem = scene.m3_particle_systems[scene.m3_particle_system_index]
            removeBone(scene, particleSystem.boneName)
            for copy in particleSystem.copies:
                removeBone(scene, copy.boneName)
            scene.m3_particle_systems.remove(scene.m3_particle_system_index)
            scene.m3_particle_system_index-= 1
            
        return{'FINISHED'}
        
        

class M3_PARTICLE_SYSTEM_COPIES_OT_add(bpy.types.Operator):
    bl_idname      = 'm3.particle_system_copies_add'
    bl_label       = "Add Particle System Copy"
    bl_description = "Adds a particle system copy for the export to the m3 model format"

    @classmethod
    def poll(cls, context):
        scene = context.scene
        particleSystemIndex = scene.m3_particle_system_index
        return (particleSystemIndex >= 0 and particleSystemIndex < len(scene.m3_particle_systems))


    def invoke(self, context, event):
        scene = context.scene
        particle_system = scene.m3_particle_systems[scene.m3_particle_system_index]
        copy = particle_system.copies.add()
        copy.name = findUnusedParticleSystemName(scene)
        if len(scene.m3_material_references) >= 1:
            particle_system.materialName = scene.m3_material_references[0].name

        handleParticleSystemCopyRename(copy,context)
        particle_system.copyIndex = len(particle_system.copies)-1
        
        selectOrCreateBoneForPartileSystemCopy(scene, particle_system, copy)
        return{'FINISHED'}


class M3_PARTICLE_SYSTEMS_COPIES_OT_remove(bpy.types.Operator):
    bl_idname      = 'm3.particle_system_copies_remove'
    bl_label       = "Remove Particle System Copy"
    bl_description = "Removes the active copy from the M3 particle system"
    
    @classmethod
    def poll(cls, context):
        scene = context.scene
        particleSystemIndex = scene.m3_particle_system_index
        if not (particleSystemIndex >= 0 and particleSystemIndex < len(scene.m3_particle_systems)):
            return False
        particleSystem = scene.m3_particle_systems[particleSystemIndex]
        copyIndex = particleSystem.copyIndex
        return (copyIndex >= 0 and copyIndex < len(particleSystem.copies))

    def invoke(self, context, event):
        scene = context.scene
        particleSystemIndex = scene.m3_particle_system_index
        particleSystem = scene.m3_particle_systems[particleSystemIndex]
        copyIndex = particleSystem.copyIndex
        copy = particleSystem.copies[copyIndex]
        removeBone(scene, copy.boneName)
        particleSystem.copies.remove(particleSystem.copyIndex)
        particleSystem.copyIndex -= 1

        
        return{'FINISHED'}

class M3_FORCES_OT_add(bpy.types.Operator):
    bl_idname      = 'm3.forces_add'
    bl_label       = "Add Force"
    bl_description = "Adds a particle system force for the export to the m3 model format"

    def invoke(self, context, event):
        scene = context.scene
        force = scene.m3_forces.add()
        force.updateBlenderBoneShape = False
        force.boneSuffix = self.findUnusedName(scene)
        handleForceTypeOrBoneSuffixChange(force, context)
        force.boneName = shared.boneNameForForce(force)
        force.updateBlenderBoneShape = True

        # The following selection causes a new bone to be created:
        scene.m3_force_index = len(scene.m3_forces)-1
        return{'FINISHED'}

    def findUnusedName(self, scene):
        usedNames = set()
        for force in scene.m3_forces:
            usedNames.add(force.boneSuffix)
        unusedName = None
        counter = 1
        while unusedName == None:
            suggestedName = "%02d" % counter
            if not suggestedName in usedNames:
                unusedName = suggestedName
            counter += 1
        return unusedName 

class M3_FORCES_OT_remove(bpy.types.Operator):
    bl_idname      = 'm3.forces_remove'
    bl_label       = "Remove M3 Force"
    bl_description = "Removes the active M3 particle system force"
    
    def invoke(self, context, event):
        scene = context.scene
        if scene.m3_force_index >= 0:
            force = scene.m3_forces[scene.m3_force_index]
            removeBone(scene, force.boneName)
            scene.m3_forces.remove(scene.m3_force_index)
            scene.m3_force_index-= 1
        return{'FINISHED'}

class M3_RIGID_BODIES_OT_add(bpy.types.Operator):
    bl_idname      = 'm3.rigid_bodies_add'
    bl_label       = "Add Rigid Body"
    bl_description = "Adds a rigid body for export to the m3 model format"
    
    def invoke(self, context, event):
        scene = context.scene
        rigid_body = scene.m3_rigid_bodies.add()
        
        rigid_body.name = self.findUnusedName(scene)
        rigid_body.boneName = ""
        
        scene.m3_rigid_body_index = len(scene.m3_rigid_bodies) - 1
        return {'FINISHED'}
    
    def findUnusedName(self, scene):
        usedNames = set()
        for rigid_body in scene.m3_rigid_bodies:
            usedNames.add(rigid_body.name)
        unusedName = None
        counter = 1
        while unusedName == None:
            suggestedName = "%d" % counter
            if not suggestedName in usedNames:
                unusedName = suggestedName
            counter += 1
        return unusedName

class M3_RIGID_BODIES_OT_remove(bpy.types.Operator):
    bl_idname = 'm3.rigid_bodies_remove'
    bl_label = "Remove M3 Rigid Body"
    bl_description = "Removes the active M3 rigid body (and the M3 Physics Shapes it contains)"
    
    def invoke(self, context, event):
        scene = context.scene
        
        currentIndex = scene.m3_rigid_body_index
        if not 0 <= currentIndex < len(scene.m3_rigid_bodies):
            return {'CANCELLED'}
        
        shared.removeRigidBodyBoneShape(scene, scene.m3_rigid_bodies[currentIndex])
        
        scene.m3_rigid_bodies.remove(currentIndex)
        scene.m3_rigid_body_index -= 1
        
        return {'FINISHED'}

class M3_PHYSICS_SHAPES_OT_add(bpy.types.Operator):
    bl_idname      = 'm3.physics_shapes_add'
    bl_label       = "Add Physics Shape"
    bl_description = "Adds an M3 physics shape to the active M3 rigid body"
    
    def invoke(self, context, event):
        scene = context.scene
        
        currentIndex = scene.m3_rigid_body_index
        if not 0 <= currentIndex < len(scene.m3_rigid_bodies):
            return {'CANCELLED'}
        rigid_body = scene.m3_rigid_bodies[currentIndex]
        
        physics_shape = rigid_body.physicsShapes.add()
        physics_shape.name = self.findUnusedName(rigid_body)
        
        rigid_body.physicsShapeIndex = len(rigid_body.physicsShapes) - 1
        shared.updateBoneShapeOfRigidBody(scene, rigid_body)
        
        return {'FINISHED'}
    
    def findUnusedName(self, rigid_body):
        usedNames = set()
        for physics_shape in rigid_body.physicsShapes:
            usedNames.add(physics_shape.name)
        unusedName = None
        counter = 1
        while unusedName == None:
            suggestedName = "%d" % counter
            if not suggestedName in usedNames:
                unusedName = suggestedName
            counter += 1
        return unusedName

class M3_PHYSICS_SHAPES_OT_remove(bpy.types.Operator):
    bl_idname = 'm3.physics_shapes_remove'
    bl_label = "Remove M3 Physics Shape"
    bl_description = "Removes the active M3 physics shape"
    
    def invoke(self, context, event):
        scene = context.scene
        
        currentIndex = scene.m3_rigid_body_index
        if not 0 <= currentIndex < len(scene.m3_rigid_bodies):
            return {'CANCELLED'}
        rigid_body = scene.m3_rigid_bodies[currentIndex]
        
        currentIndex = rigid_body.physicsShapeIndex
        if not 0 <= currentIndex < len(rigid_body.physicsShapes):
            return {'CANCELLED'}
        
        rigid_body.physicsShapes.remove(currentIndex)
        rigid_body.physicsShapeIndex -= 1
        shared.updateBoneShapeOfRigidBody(scene, rigid_body)
        
        return {'FINISHED'}

class M3_LIGHTS_OT_add(bpy.types.Operator):
    bl_idname      = 'm3.lights_add'
    bl_label       = "Add Light"
    bl_description = "Adds a particle system light for the export to the m3 model format"

    def invoke(self, context, event):
        scene = context.scene
        light = scene.m3_lights.add()
        light.updateBlenderBone = False
        light.boneSuffix = self.findUnusedName(scene)
        light.boneName = shared.boneNameForLight(light)
        handleLightTypeOrBoneSuffixChange(light, context)
        light.updateBlenderBone = True
        
        # The following selection causes a new bone to be created:
        scene.m3_light_index = len(scene.m3_lights)-1
        
        return{'FINISHED'}

    def findUnusedName(self, scene):
        usedNames = set()
        for light in scene.m3_lights:
            usedNames.add(light.boneSuffix)
        unusedName = None
        counter = 1
        while unusedName == None:
            suggestedName = "%02d" % counter
            if not suggestedName in usedNames:
                unusedName = suggestedName
            counter += 1
        return unusedName 

class M3_LIGHTS_OT_remove(bpy.types.Operator):
    bl_idname      = 'm3.lights_remove'
    bl_label       = "Remove M3 Light"
    bl_description = "Removes the active M3 particle system light"
    
    def invoke(self, context, event):
        scene = context.scene
        if scene.m3_light_index >= 0:
            light = scene.m3_lights[scene.m3_light_index]
            removeBone(scene, light.boneName)
            scene.m3_lights.remove(scene.m3_light_index)
            scene.m3_light_index-= 1
        return{'FINISHED'}
        

class M3_ATTACHMENT_POINTS_OT_add(bpy.types.Operator):
    bl_idname      = 'm3.attachment_points_add'
    bl_label       = "Add Attachment Point"
    bl_description = "Adds an attachment point for the export to Starcraft 2"

    def invoke(self, context, event):
        scene = context.scene
        attachmentPoint = scene.m3_attachment_points.add()
        name = self.findUnusedName(scene)
        attachmentPoint.updateBlenderBone = False
        attachmentPoint.boneSuffix = name
        attachmentPoint.boneName = shared.boneNameForAttachmentPoint(attachmentPoint)
        attachmentPoint.updateBlenderBone = True

        # The following selection causes a new bone to be created:
        scene.m3_attachment_point_index = len(scene.m3_attachment_points)-1
        return{'FINISHED'}
        
    def findUnusedName(self, scene):
        usedNames = set()
        for attachmentPoint in scene.m3_attachment_points:
            usedNames.add(attachmentPoint.boneSuffix)
        suggestedNames = {"Center", "Origin", "Overhead", "Target"}

        unusedName = None
        for suggestedName in suggestedNames:
            if not suggestedName in usedNames:
                unusedName = suggestedName
                break
        counter = 1
        while unusedName == None:
            suggestedName = "Target %02d" % counter
            if not suggestedName in usedNames:
                unusedName = suggestedName
            counter += 1
        return unusedName


class M3_TIGHT_HIT_TESTS_OT_selectorcreatebone(bpy.types.Operator):
    bl_idname      = 'm3.tight_hit_test_select_or_create_bone'
    bl_label       = "Select or create the HitTestFuzzy bone"
    bl_description = "Adds a shape for the fuzzy hit test"

    def invoke(self, context, event):
        scene = context.scene
        tightHitTest = scene.m3_tight_hit_test
        tightHitTest.name = shared.tightHitTestBoneName
        selectOrCreateBoneForShapeObject(scene, tightHitTest)
        return{'FINISHED'}


class M3_FUZZY_HIT_TESTS_OT_add(bpy.types.Operator):
    bl_idname      = 'm3.fuzzy_hit_tests_add'
    bl_label       = "Add Fuzzy Hit Test Shape"
    bl_description = "Adds a shape for the fuzzy hit test"

    def invoke(self, context, event):
        scene = context.scene
        m3_fuzzy_hit_test = scene.m3_fuzzy_hit_tests.add()
        m3_fuzzy_hit_test.name = self.findUnusedName(scene)

        # The following selection causes a new bone to be created:
        scene.m3_fuzzy_hit_test_index = len(scene.m3_fuzzy_hit_tests)-1
        return{'FINISHED'}
        
    def findUnusedName(self, scene):
        usedNames = set()
        for m3_fuzzy_hit_test in scene.m3_fuzzy_hit_tests:
            usedNames.add(m3_fuzzy_hit_test.name)
        unusedName = None
        bestName = "HitTestFuzzy"
        if not bestName in usedNames:
            unusedName = bestName
        counter = 1
        while unusedName == None:
            suggestedName = bestName + ("%02d" % counter)
            if not suggestedName in usedNames:
                unusedName = suggestedName
            counter += 1
        return unusedName

class M3_FUZZY_HIT_TESTS_OT_remove(bpy.types.Operator):
    bl_idname      = 'm3.fuzzy_hit_tests_remove'
    bl_label       = "Remove Fuzzy Hit Test Shape"
    bl_description = "Removes a fuzzy hit test shape"
    
    def invoke(self, context, event):
        scene = context.scene
        if scene.m3_fuzzy_hit_test_index >= 0:
            hitTest = scene.m3_fuzzy_hit_tests[scene.m3_fuzzy_hit_test_index]
            removeBone(scene, hitTest.name)
            scene.m3_fuzzy_hit_tests.remove(scene.m3_fuzzy_hit_test_index)
            scene.m3_fuzzy_hit_test_index-= 1
        return{'FINISHED'}
        

class M3_ATTACHMENT_POINTS_OT_remove(bpy.types.Operator):
    bl_idname      = 'm3.attachment_points_remove'
    bl_label       = "Remove Attachment Point"
    bl_description = "Removes the active M3 attachment point"
    
    def invoke(self, context, event):
        scene = context.scene
        if scene.m3_attachment_point_index >= 0:
            attackmentPoint = scene.m3_attachment_points[scene.m3_attachment_point_index]
            removeBone(scene, attackmentPoint.boneName)
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
        m3export.export(scene, fileName)
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

        scene.m3_export_options.path = self.properties.filepath
        m3export.export(scene, self.properties.filepath)
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

    bpy.types.Scene.m3_animation_index = bpy.props.IntProperty(update=handleAnimationSequenceIndexChange, options=set())
    bpy.types.Scene.m3_animation_old_index = bpy.props.IntProperty(options=set())
    bpy.types.Scene.m3_animations = bpy.props.CollectionProperty(type=M3Animation)
    bpy.types.Scene.m3_material_layer_index = bpy.props.IntProperty(options=set())
    bpy.types.Scene.m3_material_references = bpy.props.CollectionProperty(type=M3Material)
    bpy.types.Scene.m3_standard_materials = bpy.props.CollectionProperty(type=M3StandardMaterial)
    bpy.types.Scene.m3_displacement_materials = bpy.props.CollectionProperty(type=M3DisplacementMaterial)
    bpy.types.Scene.m3_composite_materials = bpy.props.CollectionProperty(type=M3CompositeMaterial)
    bpy.types.Scene.m3_terrain_materials = bpy.props.CollectionProperty(type=M3TerrainMaterial)
    bpy.types.Scene.m3_volume_materials = bpy.props.CollectionProperty(type=M3VolumeMaterial)
    bpy.types.Scene.m3_material_reference_index = bpy.props.IntProperty(options=set())
    bpy.types.Scene.m3_cameras = bpy.props.CollectionProperty(type=M3Camera)
    bpy.types.Scene.m3_camera_index = bpy.props.IntProperty(options=set(), update=handleCameraIndexChanged)
    bpy.types.Scene.m3_particle_systems = bpy.props.CollectionProperty(type=M3ParticleSystem)
    bpy.types.Scene.m3_particle_system_index = bpy.props.IntProperty(options=set(), update=handlePartileSystemIndexChanged)
    bpy.types.Scene.m3_forces = bpy.props.CollectionProperty(type=M3Force)
    bpy.types.Scene.m3_force_index = bpy.props.IntProperty(options=set(), update=handleForceIndexChanged)
    bpy.types.Scene.m3_rigid_bodies = bpy.props.CollectionProperty(type=M3RigidBody)
    bpy.types.Scene.m3_rigid_body_index = bpy.props.IntProperty(options=set(), update=handleRigidBodyIndexChange)
    bpy.types.Scene.m3_lights = bpy.props.CollectionProperty(type=M3Light)
    bpy.types.Scene.m3_light_index = bpy.props.IntProperty(options=set(), update=handleLightIndexChanged)
    bpy.types.Scene.m3_attachment_points = bpy.props.CollectionProperty(type=M3AttachmentPoint)
    bpy.types.Scene.m3_attachment_point_index = bpy.props.IntProperty(options=set(), update=handleAttachmentPointIndexChanged)
    bpy.types.Scene.m3_export_options = bpy.props.PointerProperty(type=M3ExportOptions)
    bpy.types.Scene.m3_bone_visiblity_options = bpy.props.PointerProperty(type=M3BoneVisiblityOptions)
    bpy.types.Scene.m3_animation_ids = bpy.props.CollectionProperty(type=M3AnimIdData)
    bpy.types.Scene.m3_fuzzy_hit_tests = bpy.props.CollectionProperty(type=M3SimpleGeometricShape)
    bpy.types.Scene.m3_fuzzy_hit_test_index = bpy.props.IntProperty(options=set(), update=handleFuzzyHitTestIndexChanged)
    bpy.types.Scene.m3_tight_hit_test = bpy.props.PointerProperty(type=M3SimpleGeometricShape)
    bpy.types.Scene.m3_boundings = bpy.props.PointerProperty(type=M3Boundings)
    bpy.types.Mesh.m3_material_name = bpy.props.StringProperty(options=set())
    bpy.types.INFO_MT_file_import.append(menu_func_import)
    bpy.types.INFO_MT_file_export.append(menu_func_export)
    bpy.types.Bone.m3_unapplied_scale = bpy.props.FloatVectorProperty(default=(1.0, 1.0, 1.0), size=3, options=set()) 
    bpy.types.EditBone.m3_unapplied_scale = bpy.props.FloatVectorProperty(default=(1.0, 1.0, 1.0), size=3, options=set()) 
    bpy.types.Scene.m3_default_value_action_assignments = bpy.props.CollectionProperty(type=AssignedActionOfM3Animation, options=set())


 
def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.INFO_MT_file_import.remove(menu_func_import)
    bpy.types.INFO_MT_file_export.remove(menu_func_export)
 
if __name__ == "__main__":
    register()