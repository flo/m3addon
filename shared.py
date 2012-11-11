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

import bpy
import mathutils
import random
import math
from bpy_extras import io_utils

standardMaterialLayerFieldNames = ["diffuseLayer", "decalLayer", "specularLayer", "selfIllumLayer",
    "emissiveLayer", "reflectionLayer", "evioLayer", "evioMaskLayer", "alphaMaskLayer", 
    "bumpLayer", "heightLayer", "layer12", "layer13"]

standardMaterialLayerNames = ["Diffuse", "Decal", "Specular", "Self Illumination", 
    "Emissive", "Reflection", "Evio", "Evio Mask", "Alpha Mask", "Bump", "Height", "Layer 12", "Layer 13"]

displacementMaterialLayerFieldNames = ["normalLayer", "strengthLayer"]
displacementMaterialLayerNames = ["Normal", "Strength"]

terrainMaterialLayerFieldNames = ["layer"]
terrainMaterialLayerNames = ["Terrain"]

volumeMaterialLayerFieldNames = ["colorDefiningLayer", "unknownLayer2", "unknownLayer3"]
volumeMaterialLayerNames = ["Color Defining Layer", "Layer 2", "Layer 3"]

creepMaterialLayerFieldNames = ["layer"]
creepMaterialLayerNames = ["Creep"]

materialNames = ["No Material", "Standard", "Displacement", "Composite", "Terrain", "Volume", "Unknown", "Creep"]
standardMaterialTypeIndex = 1
displacementMaterialTypeIndex = 2
compositeMaterialTypeIndex = 3
terrainMaterialTypeIndex = 4
volumeMaterialTypeIndex = 5
creepMaterialTypeIndex = 7

emssionAreaTypePoint = "0"
emssionAreaTypePlane = "1"
emssionAreaTypeSphere = "2"
emssionAreaTypeCuboid = "3"
emssionAreaTypeCylinder = "4"

attachmentVolumeNone = "-1"
attachmentVolumeCuboid = "0"
attachmentVolumeSphere = "1"
attachmentVolumeCapsule = "2"

lightTypePoint = "1"
lightTypeSpot = "2"


tightHitTestBoneName = "HitTestTight"

rotFixMatrix = mathutils.Matrix((( 0, 1, 0, 0,),
                                 (-1, 0, 0, 0),
                                 ( 0, 0, 1, 0),
                                 ( 0, 0, 0, 1)))
rotFixMatrixInverted = rotFixMatrix.transposed()

animFlagsForAnimatedProperty = 6

star2ParticlePrefix = "Star2Part"
star2ForcePrefix = "Star2Force"
# Ref_ is the bone prefix for attachment points without volume and
# the prefix for all attachment point names (for volume attachment point names too)
attachmentPointPrefix = "Ref_" 
attachmentVolumePrefix = "Vol_"
animObjectIdModel = "MODEL"
animObjectIdArmature = "ARMATURE"
animObjectIdScene = "SCENE"
lightPrefixMap = {"1": "Star2Omni", "2": "Star2Spot"}


def toValidBoneName(name):
    maxLength = 31
    return name[:maxLength]    

def boneNameForAttachmentPoint(attachmentPoint):
    if attachmentPoint.volumeType == "-1":
        bonePrefix = attachmentPointPrefix
    else:
        bonePrefix = attachmentVolumePrefix
    return bonePrefix + attachmentPoint.boneSuffix

def boneNameForPartileSystem(particleSystem):
    return toValidBoneName(star2ParticlePrefix + particleSystem.boneSuffix)
    
def boneNameForForce(force):
    return toValidBoneName(star2ForcePrefix + force.boneSuffix)

def boneNameForLight(light):
    boneSuffix = light.boneSuffix
    lightType = light.lightType
    lightPrefix = lightPrefixMap.get(lightType)
    if lightPrefix == None:
        raise Exception("No prefix is known for light %s" % lightType)
    else:
        return toValidBoneName(lightPrefix + boneSuffix)
        
def boneNameForPartileSystemCopy(copy):
    return toValidBoneName(star2ParticlePrefix + copy.name)


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
        bone = armature.bones.get(boneName)
        if bone != None:
            return (bone, armatureObject)
    return (None, None)


def locRotScaleMatrix(location, rotation, scale):
    """ Important: rotation must be a normalized quaternion """
    # to_matrix() only works properly with normalized quaternions.
    result = rotation.to_matrix().to_4x4()
    result.col[0] *= scale.x
    result.col[1] *= scale.y
    result.col[2] *= scale.z
    result.translation = location
    return result

def setAnimationWithIndexToCurrentData(scene, animationIndex):
    if (animationIndex < 0) or (animationIndex >= len(scene.m3_animations)):
        return
    animation = scene.m3_animations[animationIndex]
    animation.startFrame = scene.frame_start
    animation.exlusiveEndFrame = scene.frame_end+1
    while len(animation.assignedActions) > 0:
        animation.assignedActions.remove(0)

    for targetObject in bpy.data.objects:
        if targetObject.animation_data != None:
            assignedAction = animation.assignedActions.add()
            assignedAction.targetName = targetObject.name
            if targetObject.animation_data.action != None:
                assignedAction.actionName = targetObject.animation_data.action.name
    if scene.animation_data != None and scene.animation_data.action != None:
        assignedAction = animation.assignedActions.add()
        assignedAction.targetName = scene.name
        assignedAction.actionName = scene.animation_data.action.name

def getMaterial(scene, materialTypeIndex, materialIndex):
    if materialTypeIndex == standardMaterialTypeIndex:
        return scene.m3_standard_materials[materialIndex]
    elif materialTypeIndex == displacementMaterialTypeIndex:
        return scene.m3_displacement_materials[materialIndex]
    elif materialTypeIndex == compositeMaterialTypeIndex:
        return scene.m3_composite_materials[materialIndex] 
    elif materialTypeIndex == terrainMaterialTypeIndex:
        return scene.m3_terrain_materials[materialIndex] 
    elif materialTypeIndex == volumeMaterialTypeIndex:
        return scene.m3_volume_materials[materialIndex] 
    elif materialTypeIndex == creepMaterialTypeIndex:
        return scene.m3_creep_materials[materialIndex] 
    return None

def sqr(x):
    return x*x

def smoothQuaternionTransition(previousQuaternion, quaternionToFix):
    sumOfSquares =  sqr(quaternionToFix.x - previousQuaternion.x) + sqr(quaternionToFix.y - previousQuaternion.y) + sqr(quaternionToFix.z - previousQuaternion.z) + sqr(quaternionToFix.w - previousQuaternion.w)
    sumOfSquaresMinus =  sqr(-quaternionToFix.x - previousQuaternion.x) + sqr(-quaternionToFix.y - previousQuaternion.y) + sqr(-quaternionToFix.z - previousQuaternion.z) + sqr(-quaternionToFix.w - previousQuaternion.w)
    if sumOfSquaresMinus < sumOfSquares:
        quaternionToFix.negate()


def floatInterpolationFunction(leftInterpolationValue, rightInterpolationValue, rightFactor):
    leftFactor = 1.0 - rightFactor
    return leftInterpolationValue * leftFactor + rightInterpolationValue * rightFactor

def vectorInterpolationFunction(leftInterpolationValue, rightInterpolationValue, rightFactor):
    return leftInterpolationValue.lerp(rightInterpolationValue, rightFactor)

def quaternionInterpolationFunction(leftInterpolationValue, rightInterpolationValue, rightFactor):
    return leftInterpolationValue.slerp(rightInterpolationValue, rightFactor)

def floatsAlmostEqual(floatExpected, floatActual):
    delta = abs(floatExpected - floatActual)
    return delta < 0.00001
    
def vectorsAlmostEqual(vectorExpected, vectorActual):
    diff = vectorExpected - vectorActual
    return diff.length < 0.00001
    
def quaternionsAlmostEqual(q0, q1):
    distanceSqr = sqr(q0.x-q1.x)+sqr(q0.y-q1.y)+sqr(q0.z-q1.z)+sqr(q0.w-q1.w)
    return distanceSqr < sqr(0.00001)

def simplifyFloatAnimationWithInterpolation(timeValuesInMS, values):
    return simplifyAnimationWithInterpolation(timeValuesInMS, values, floatInterpolationFunction, floatsAlmostEqual)

def simplifyVectorAnimationWithInterpolation(timeValuesInMS, vectors):
    return simplifyAnimationWithInterpolation(timeValuesInMS, vectors, vectorInterpolationFunction, vectorsAlmostEqual)

def simplifyQuaternionAnimationWithInterpolation(timeValuesInMS, vectors):
    return simplifyAnimationWithInterpolation(timeValuesInMS, vectors, quaternionInterpolationFunction, quaternionsAlmostEqual)

def simplifyAnimationWithInterpolation(timeValuesInMS, values, interpolationFunction, almostEqualFunction):
    if len(timeValuesInMS) < 2:
        return timeValuesInMS, values
    leftTimeInMS = timeValuesInMS[0]
    leftValue = values[0]
    currentTimeInMS = timeValuesInMS[1]
    currentValue = values[1]
    newTimeValuesInMS = [leftTimeInMS]
    newValues = [leftValue]
    for rightTimeInMS, rightValue in zip(timeValuesInMS[2:], values[2:]):
        timeSinceLeftTime =  currentTimeInMS - leftTimeInMS
        intervalLength = rightTimeInMS - leftTimeInMS
        rightFactor = timeSinceLeftTime / intervalLength
        expectedValue = interpolationFunction(leftValue, rightValue, rightFactor)
        if almostEqualFunction(expectedValue, currentValue):
            # ignore current value since it's interpolatable:
            pass
        else:
            newTimeValuesInMS.append(currentTimeInMS)
            newValues.append(currentValue)
            leftTimeInMS = currentTimeInMS
            leftValue = currentValue
        currentValue = rightValue
        currentTimeInMS = rightTimeInMS
    newTimeValuesInMS.append(timeValuesInMS[-1])
    newValues.append(values[-1])
    return newTimeValuesInMS, newValues

def findMeshObjects(scene):
    for currentObject in scene.objects:
        if currentObject.type == 'MESH':
            yield currentObject
            
def createDefaulValuesAction(scene, ownerName, actionIdRoot):
    action = bpy.data.actions.new("DEFAULTS_FOR_" + ownerName)
    action.id_root = actionIdRoot
    actionAssignment = scene.m3_default_value_action_assignments.add()
    actionAssignment.actionName = action.name
    actionAssignment.targetName = ownerName
    return action
    

def findActionOfAssignedAction(assignedAction, actionOwnerName, actionOwnerType):
    if actionOwnerName == assignedAction.targetName:
        actionName = assignedAction.actionName
        action = bpy.data.actions.get(actionName)
        if action == None:
            print("Warning: The action %s was referenced by name but does no longer exist" % assignedAction.actionName)
        else:
            if action.id_root == actionOwnerType:
                return action
    return None
    
def composeMatrix(location, rotation, scale):
    locMatrix= mathutils.Matrix.Translation(location)
    rotationMatrix = rotation.to_matrix().to_4x4()
    scaleMatrix = mathutils.Matrix()
    for i in range(3):
        scaleMatrix[i][i] = scale[i]
    return locMatrix * rotationMatrix * scaleMatrix

def determineDefaultActionFor(scene, actionOwnerName, actionOwnerType):
    for assignedAction in scene.m3_default_value_action_assignments:
        action = findActionOfAssignedAction(assignedAction, actionOwnerName, actionOwnerType)
        if action != None:
            return action
            
def getLongAnimIdOf(objectId, animPath):
    if objectId == animObjectIdScene and animPath.startswith("m3_boundings"):
        return objectId + "m3_boundings"
    return objectId + animPath;


def getRandomAnimIdNotIn(animIdSet):
    maxValue = 0x0fffffff
    unusedAnimId = random.randint(1, maxValue)
    while unusedAnimId in animIdSet:
        unusedAnimId = random.randint(1, maxValue)
    return unusedAnimId

def createHiddenMeshObject(name, untransformedPositions, faces, matrix):
    mesh = bpy.data.meshes.new(name)
    meshObject = bpy.data.objects.new(name, mesh)
    meshObject.location = (0,0,0) 

    transformedPositions = []
    for v in untransformedPositions:
        transformedPositions.append(matrix * mathutils.Vector(v))

    mesh.vertices.add(len(transformedPositions))
    mesh.vertices.foreach_set("co", io_utils.unpack_list(transformedPositions))

    mesh.tessfaces.add(len(faces))
    mesh.tessfaces.foreach_set("vertices_raw", io_utils.unpack_face_list(faces))
    
    mesh.update(calc_edges=True)
    return meshObject

def setBoneVisibility(scene, boneName, visibility):
    bone, armatureObject = findBoneWithArmatureObject(scene, boneName)
    boneExists = bone != None
    if boneExists:
        bone.hide = not visibility

def updateBoneShapeOfShapeObject(shapeObject, bone, poseBone):
    cubeShapeConstant = "0"
    sphereShapeConstant = "1"
    capsuleShapeConstant = "2"
    if shapeObject.shape == capsuleShapeConstant:
        radius = shapeObject.size0
        height = shapeObject.size1
        untransformedPositions, faces = createMeshDataForCapsule(radius, height)
    elif shapeObject.shape == sphereShapeConstant:
        radius = shapeObject.size0
        untransformedPositions, faces = createMeshDataForSphere(radius)
    else:
        sizeX, sizeY, sizeZ = 2*shapeObject.size0, 2*shapeObject.size1, 2*shapeObject.size2
        untransformedPositions, faces = createMeshDataForCuboid(sizeX, sizeY, sizeZ)

    matrix = composeMatrix(shapeObject.offset, shapeObject.rotationEuler, shapeObject.scale)
    meshName = 'ShapeObjectBoneMesh'
    updateBoneShape(bone, poseBone, meshName, untransformedPositions, faces, matrix)


def updateBoneShapeOfParticleSystem(particleSystem, bone, poseBone):
    emissionAreaType = particleSystem.emissionAreaType
    if emissionAreaType == emssionAreaTypePoint:
        untransformedPositions, faces = createMeshDataForSphere(0.02)
    elif emissionAreaType == emssionAreaTypePlane:
        length = particleSystem.emissionAreaSize[0]
        width = particleSystem.emissionAreaSize[1]
        height = 0
        untransformedPositions, faces = createMeshDataForCuboid(length, width, height)
    elif emissionAreaType == emssionAreaTypeSphere:
        radius = particleSystem.emissionAreaRadius
        untransformedPositions, faces = createMeshDataForSphere(radius)
    elif emissionAreaType == emssionAreaTypeCuboid:
        length = particleSystem.emissionAreaSize[0]
        width = particleSystem.emissionAreaSize[1]
        height = particleSystem.emissionAreaSize[2]
        untransformedPositions, faces = createMeshDataForCuboid(length, width, height)
    else:
        radius = particleSystem.emissionAreaRadius
        height = particleSystem.emissionAreaSize[2]
        untransformedPositions, faces = createMeshDataForCylinder(radius, height)
       
    boneName = particleSystem.boneName
    meshName = boneName + 'Mesh'
    updateBoneShape(bone, poseBone, meshName, untransformedPositions, faces)

def updateBoneShapeOfAttachmentPoint(attachmentPoint, bone, poseBone):
    volumeType = attachmentPoint.volumeType
    if volumeType == attachmentVolumeNone:
        untransformedPositions, faces = createAttachmentPointSymbolMesh()
    elif volumeType == attachmentVolumeCuboid:
        length = 2*attachmentPoint.volumeSize0
        width = 2*attachmentPoint.volumeSize1
        height = 2*attachmentPoint.volumeSize2
        untransformedPositions, faces = createMeshDataForCuboid(length, width, height)
    elif volumeType == attachmentVolumeSphere:
        radius = attachmentPoint.volumeSize0
        untransformedPositions, faces = createMeshDataForSphere(radius)
    elif volumeType == attachmentVolumeCapsule:
        radius = attachmentPoint.volumeSize0
        height = attachmentPoint.volumeSize1
        untransformedPositions, faces = createMeshDataForCapsule(radius, height)
    else:
        #TODO create proper meshes for the 2 unknown shape types:
        print("Warning: The attachment volume %s has the unsupported type id %s" % (attachmentPoint.name, volumeType))
        untransformedPositions, faces= ([(0,0,0), (0,0,1), (0,1,1)], [(0,1,2)])
        
    boneName = boneNameForAttachmentPoint(attachmentPoint)
    meshName = boneName + 'Mesh'
    updateBoneShape(bone, poseBone, meshName, untransformedPositions, faces)


def updateBoneShapeOfLight(light, bone, poseBone):
    lightType = light.lightType
    if lightType == lightTypePoint:
        radius = light.attenuationFar
        untransformedPositions, faces = createMeshDataForSphere(radius)
    elif lightType == lightTypeSpot:
        radius = light.falloff
        height = light.attenuationFar
        untransformedPositions, faces = createMeshDataForLightCone(radius, height)
    else:
        raise Exception("Unsupported light type")
        
    boneName = boneNameForLight(light)
    meshName = boneName + 'Mesh'
    updateBoneShape(bone, poseBone, meshName, untransformedPositions, faces)

def updateBoneShapeOfForce(force, bone, poseBone):
    untransformedPositions, faces = createMeshDataForSphere(force.forceRange)
    boneName = force.boneName
    meshName = boneName + 'Mesh'
    updateBoneShape(bone, poseBone, meshName, untransformedPositions, faces)

def getRigidBodyBones(scene, rigidBody):
    bone, armature = findBoneWithArmatureObject(scene, rigidBody.boneName)
    if armature == None or bone == None:
        print("Warning: Could not find bone name specified in rigid body: %s" % rigidBody.name)
        return None, None
    
    poseBone = armature.pose.bones[rigidBody.boneName]
    if poseBone == None:
        print("Warning: Could not find posed bone: %s" % rigidBody.boneName)
        return None, None
    
    return bone, poseBone

def createPhysicsShapeMeshData(shape):
    if shape.shape == "0":
        vertices, faces = createMeshDataForCuboid(2 * shape.size0, 2 * shape.size1, 2 * shape.size2)
    elif shape.shape == "1":
        vertices, faces = createMeshDataForSphere(shape.size0)
    elif shape.shape == "2":
        vertices, faces = createMeshDataForCapsule(shape.size0, shape.size1)
    elif shape.shape == "3":
        vertices, faces = createMeshDataForCylinder(shape.size0, shape.size1)
    else:
        meshObject = bpy.data.objects[shape.meshObjectName]
        mesh = meshObject.data
        
        vertices = [v.co for v in mesh.vertices]
        faces = [f.vertices for f in mesh.polygons]
    
    matrix = composeMatrix(shape.offset, shape.rotationEuler, shape.scale)
    vertices = [matrix * mathutils.Vector(v) for v in vertices]
    
    return vertices, faces

def updateBoneShapeOfRigidBody(scene, rigidBody):
    bone, poseBone = getRigidBodyBones(scene, rigidBody)
    if bone == None or poseBone == None:
        return
    
    if len(rigidBody.physicsShapes) == 0:
        removeRigidBodyBoneShape(scene, rigidBody)
        return
    
    combinedVertices, combinedFaces = [], []
    for shape in rigidBody.physicsShapes:
        vertices, faces = createPhysicsShapeMeshData(shape)
        # TODO: remove this check when mesh / convex hull is implemented
        if vertices == None or faces == None:
            continue
        
        faces = [[fe + len(combinedVertices) for fe in f] for f in faces]
        
        combinedVertices.extend(vertices)
        combinedFaces.extend(faces)
    
    updateBoneShape(bone, poseBone, "PhysicsShapeBoneMesh", combinedVertices, combinedFaces)

def removeRigidBodyBoneShape(scene, rigidBody):
    bone, poseBone = getRigidBodyBones(scene, rigidBody)
    if bone == None or poseBone == None:
        return
    
    poseBone.custom_shape = None
    bone.show_wire = False

def updateBoneShape(bone, poseBone, meshName, untransformedPositions, faces, matrix=mathutils.Matrix()):
    # Undo the rotation fix:
    matrix = rotFixMatrixInverted * matrix
    boneScale = (bone.head - bone.tail).length
    invertedBoneScale = 1.0 / boneScale
    scaleMatrix = mathutils.Matrix()
    scaleMatrix[0][0] = invertedBoneScale
    scaleMatrix[1][1] = invertedBoneScale
    scaleMatrix[2][2] = invertedBoneScale
    matrix = scaleMatrix * matrix
    
    #TODO reuse existing mesh of bone if it exists
    poseBone.custom_shape = createHiddenMeshObject(meshName, untransformedPositions, faces, matrix)
    bone.show_wire = True


def createAttachmentPointSymbolMesh():
    xd = 0.05
    yd = 0.025
    zd = 0.1
    vertices = [(-xd, 0, 0), (xd, 0, 0), (0, -yd, 0),  (0, 0, zd)]
    faces = [(0,1,2), (0,1,3), (1,2,3), (0,2,3)]
    return vertices, faces

def createMeshDataForLightCone(radius, height, numberOfSideFaces = 10):
    vertices = []
    faces = []
    for i in range(numberOfSideFaces):
        angle0 = 2*math.pi * i / float(numberOfSideFaces)
        x = math.cos(angle0)*radius
        y = math.sin(angle0)*radius
        vertices.append((x,y, -height))
        
    tipVertexIndex = len(vertices)
    vertices.append((0, 0, 0))
    for i in range(numberOfSideFaces):
        nextI = ((i+1) % numberOfSideFaces)
        i0 = nextI
        i1 = tipVertexIndex
        i2 = i
        faces.append((i0, i1, i2))
    return (vertices, faces)

def createMeshDataForSphere(radius, numberOfSideFaces = 10, numberOfCircles = 10):
    """returns vertices and faces"""
    vertices = []
    faces = []
    for circleIndex in range(numberOfCircles):
        circleAngle = math.pi * (circleIndex+1) / float(numberOfCircles+1)
        circleRadius = radius*math.sin(circleAngle)
        circleHeight = -radius*math.cos(circleAngle)
        nextCircleIndex = (circleIndex+1) % numberOfCircles
        for i in range(numberOfSideFaces):
            angle = 2*math.pi * i / float(numberOfSideFaces)
            nextI = ((i+1) % numberOfSideFaces)
            if nextCircleIndex != 0:
                i0 = circleIndex * numberOfSideFaces + i
                i1 = circleIndex * numberOfSideFaces + nextI
                i2 = nextCircleIndex * numberOfSideFaces + nextI
                i3 = nextCircleIndex * numberOfSideFaces + i
                faces.append((i0, i1 ,i2, i3))
            x = math.cos(angle)*circleRadius
            y = math.sin(angle)*circleRadius
            vertices.append((x, y, circleHeight))
    
    bottomVertexIndex = len(vertices)
    vertices.append((0, 0,-radius))
    for i in range(numberOfSideFaces):
        nextI = ((i+1) % numberOfSideFaces)
        i0 = i
        i1 = bottomVertexIndex
        i2 = nextI
        faces.append((i0, i1, i2))
    
    topVertexIndex = len(vertices)
    vertices.append((0, 0,radius))
    for i in range(numberOfSideFaces):
        nextI = ((i+1) % numberOfSideFaces)
        i0 = ((numberOfCircles-1)* numberOfSideFaces) + nextI
        i1 = topVertexIndex
        i2 = ((numberOfCircles-1)* numberOfSideFaces) + i
        faces.append((i0, i1, i2))
    return (vertices, faces)

def createMeshDataForCuboid(sizeX, sizeY, sizeZ):
    """returns vertices and faces"""
    s0 = sizeX / 2.0
    s1 = sizeY / 2.0
    s2 = sizeZ / 2.0
    faces = []
    faces.append((0, 1, 3, 2))
    faces.append((6,7,5,4))
    faces.append((4,5,1,0))
    faces.append((2, 3, 7, 6))
    faces.append((0, 2, 6, 4 ))
    faces.append((5, 7, 3, 1 ))
    vertices = [(-s0, -s1, -s2), (-s0, -s1, s2), (-s0, s1, -s2), (-s0, s1, s2), (s0, -s1, -s2), (s0, -s1, s2), (s0, s1, -s2), (s0, s1, s2)]
    return (vertices, faces)


def createMeshDataForCapsule(radius, height, numberOfSideFaces = 10, numberOfCircles = 10):
    """returns vertices and faces"""
    vertices = []
    faces = []
    halfHeight = height / 2.0
    for circleIndex in range(numberOfCircles):
        if circleIndex < numberOfCircles/2:
            circleAngle = math.pi * (circleIndex+1) / float(numberOfCircles+1-1)
            circleHeight = -halfHeight -radius*math.cos(circleAngle)
        else:
            circleAngle = math.pi * (circleIndex) / float(numberOfCircles+1-1)
            circleHeight =  halfHeight -radius*math.cos(circleAngle)
        circleRadius = radius*math.sin(circleAngle)
        nextCircleIndex = (circleIndex+1) % numberOfCircles
        for i in range(numberOfSideFaces):
            angle = 2*math.pi * i / float(numberOfSideFaces)
            nextI = ((i+1) % numberOfSideFaces)
            if nextCircleIndex != 0:
                i0 = circleIndex * numberOfSideFaces + i
                i1 = circleIndex * numberOfSideFaces + nextI
                i2 = nextCircleIndex * numberOfSideFaces + nextI
                i3 = nextCircleIndex * numberOfSideFaces + i
                faces.append((i0, i1 ,i2, i3))
            x = math.cos(angle)*circleRadius
            y = math.sin(angle)*circleRadius
            vertices.append((x, y, circleHeight))
    
    bottomVertexIndex = len(vertices)
    vertices.append((0, 0,-halfHeight -radius))
    for i in range(numberOfSideFaces):
        nextI = ((i+1) % numberOfSideFaces)
        i0 = i
        i1 = bottomVertexIndex
        i2 = nextI
        faces.append((i0, i1, i2))
    
    topVertexIndex = len(vertices)
    vertices.append((0, 0,halfHeight + radius))
    for i in range(numberOfSideFaces):
        nextI = ((i+1) % numberOfSideFaces)
        i0 = ((numberOfCircles-1)* numberOfSideFaces) + nextI
        i1 = topVertexIndex
        i2 = ((numberOfCircles-1)* numberOfSideFaces) + i
        faces.append((i0, i1, i2))
    return (vertices, faces)


def createMeshDataForCylinder(radius, height, numberOfSideFaces = 10):
    """returns the vertices and faces for a cylinder without head and bottom plane"""
    halfHeight = height / 2.0
    vertices = []
    faces = []
    for i in range(numberOfSideFaces):
        angle0 = 2*math.pi * i / float(numberOfSideFaces)
        i0 = i*2+1
        i1 = i*2
        i2 = ((i+1)*2) % (numberOfSideFaces*2)
        i3 = ((i+1)*2 +1)% (numberOfSideFaces*2)
        faces.append((i0, i1 ,i2, i3))
        x = math.cos(angle0)*radius
        y = math.sin(angle0)*radius
        vertices.append((x,y,-halfHeight))
        vertices.append((x,y,+halfHeight))
    return (vertices, faces)

def transferParticleSystem(transferer):
    transferer.transferAnimatableFloat("emissionSpeed1")
    transferer.transferAnimatableFloat("emissionSpeed2")
    transferer.transferBoolean("randomizeWithEmissionSpeed2")
    transferer.transferAnimatableFloat("emissionAngleX")
    transferer.transferAnimatableFloat("emissionAngleY")
    transferer.transferAnimatableFloat("emissionSpreadX")
    transferer.transferAnimatableFloat("emissionSpreadY")
    transferer.transferAnimatableFloat("lifespan1")
    transferer.transferAnimatableFloat("lifespan2")
    transferer.transferBoolean("randomizeWithLifespan2")
    transferer.transferFloat("zAcceleration")
    transferer.transferFloat("unknownFloat1a")
    transferer.transferFloat("unknownFloat1b")
    transferer.transferFloat("unknownFloat1c")
    transferer.transferFloat("unknownFloat1d")
    transferer.transferAnimatableVector3("particleSizes1")
    transferer.transferAnimatableVector3("rotationValues1")
    transferer.transferAnimatableColor("initialColor1")
    transferer.transferAnimatableColor("finalColor1")
    transferer.transferAnimatableColor("unknownColor1")
    transferer.transferFloat("slowdown")
    transferer.transferFloat("unknownFloat2a")
    transferer.transferFloat("unknownFloat2b")
    transferer.transferFloat("unknownFloat2c")
    transferer.transferBoolean("trailingEnabled")
    transferer.transferInt("maxParticles")
    transferer.transferAnimatableFloat("emissionRate")
    transferer.transferEnum("emissionAreaType")
    transferer.transferAnimatableVector3("emissionAreaSize")
    transferer.transferAnimatableVector3("tailUnk1")
    transferer.transferAnimatableFloat("emissionAreaRadius")
    transferer.transferAnimatableFloat("spreadUnk")
    transferer.transferEnum("emissionType")
    transferer.transferBoolean("randomizeWithParticleSizes2")
    transferer.transferAnimatableVector3("particleSizes2")
    transferer.transferBoolean("randomizeWithRotationValues2")
    transferer.transferAnimatableVector3("rotationValues2")
    transferer.transferBoolean("randomizeWithColor2")
    transferer.transferAnimatableColor("initialColor2")
    transferer.transferAnimatableColor("finalColor2")
    transferer.transferAnimatableColor("unknownColor2")
    transferer.transferAnimatableInt16("partEmit")
    transferer.transferInt("phase1StartImageIndex")
    transferer.transferInt("phase1EndImageIndex")
    transferer.transferInt("phase2StartImageIndex")
    transferer.transferInt("phase2EndImageIndex")
    transferer.transferFloat("relativePhase1Length")
    transferer.transferInt("numberOfColumns")
    transferer.transferInt("numberOfRows")
    transferer.transferFloat("columnWidth")
    transferer.transferFloat("rowHeight")
    transferer.transferEnum("particleType")
    transferer.transferFloat("lengthWidthRatio")
    transferer.transfer32Bits("forceChannels")
    transferer.transferAnimatableFloat("unknownAt908")
    transferer.transferAnimatableFloat("unknownAt952")
    transferer.transferAnimatableFloat("unknownAt1168")
    transferer.transferBit("flags", "sort")
    transferer.transferBit("flags", "collideTerrain")
    transferer.transferBit("flags", "collideObjects")
    transferer.transferBit("flags", "spawnOnBounce")
    transferer.transferBit("flags", "useInnerShape")
    transferer.transferBit("flags", "inheritEmissionParams")
    transferer.transferBit("flags", "inheritParentVel")
    transferer.transferBit("flags", "sortByZHeight")
    transferer.transferBit("flags", "reverseIteration")
    transferer.transferBit("flags", "smoothRotation")
    transferer.transferBit("flags", "bezSmoothRotation")
    transferer.transferBit("flags", "smoothSize")
    transferer.transferBit("flags", "bezSmoothSize")
    transferer.transferBit("flags", "smoothColor")
    transferer.transferBit("flags", "bezSmoothColor")
    transferer.transferBit("flags", "litParts")
    transferer.transferBit("flags", "randFlipBookStart")
    transferer.transferBit("flags", "multiplyByGravity")
    transferer.transferBit("flags", "clampTailParts")
    transferer.transferBit("flags", "spawnTrailingParts")
    transferer.transferBit("flags", "useVertexAlpha")
    transferer.transferBit("flags", "modelParts")
    transferer.transferBit("flags", "swapYZonModelParts")
    transferer.transferBit("flags", "scaleTimeByParent")
    transferer.transferBit("flags", "useLocalTime")
    transferer.transferBit("flags", "simulateOnInit")
    transferer.transferBit("flags", "copy")

def transferParticleSystemCopy(transferer):
    transferer.transferAnimatableFloat("emissionRate")
    transferer.transferAnimatableInt16("partEmit")
    
def transferForce(transferer):
    transferer.transferEnum("forceType")
    transferer.transfer32Bits("forceChannels")
    transferer.transferAnimatableFloat("forceStrength")
    transferer.transferAnimatableFloat("forceRange")
    transferer.transferAnimatableFloat("unknownAt64")
    transferer.transferAnimatableFloat("unknownAt84")

def transferRigidBody(transferer):
    transferer.transferFloat("unknownAt0")
    transferer.transferFloat("unknownAt4")
    transferer.transferFloat("unknownAt8")
    # skip other unknown values for now
    transferer.transferBit("flags", "collidable")
    transferer.transferBit("flags", "walkable")
    transferer.transferBit("flags", "stackable")
    transferer.transferBit("flags", "simulateOnCollision")
    transferer.transferBit("flags", "ignoreLocalBodies")
    transferer.transferBit("flags", "alwaysExists")
    transferer.transferBit("flags", "doNotSimulate")
    transferer.transfer16Bits("localForces")
    transferer.transferBit("worldForces", "wind")
    transferer.transferBit("worldForces", "explosion")
    transferer.transferBit("worldForces", "energy")
    transferer.transferBit("worldForces", "blood")
    transferer.transferBit("worldForces", "magnetic")
    transferer.transferBit("worldForces", "grass")
    transferer.transferBit("worldForces", "brush")
    transferer.transferBit("worldForces", "trees")
    transferer.transferInt("priority")

def transferPhysicsShape(transferer):
    transferer.transferEnum("shape")
    # skip unknown values for now
    transferer.transferFloat("size0")
    transferer.transferFloat("size1")
    transferer.transferFloat("size2")

def transferStandardMaterial(transferer):
    transferer.transferString("name")
    transferer.transferBit("flags", "unfogged")
    transferer.transferBit("flags", "twoSided")
    transferer.transferBit("flags", "unshaded")
    transferer.transferBit("flags", "noShadowsCast")
    transferer.transferBit("flags", "noHitTest")
    transferer.transferBit("flags", "noShadowsReceived")
    transferer.transferBit("flags", "depthPrepass")
    transferer.transferBit("flags", "useTerrainHDR")
    transferer.transferBit("flags", "splatUVfix")
    transferer.transferBit("flags", "softBlending")
    transferer.transferBit("flags", "forParticles")
    transferer.transferBit("flags", "darkNormalMapping")
    transferer.transferBit("unknownFlags", "unknownFlag0x1")
    transferer.transferBit("unknownFlags", "unknownFlag0x4")
    transferer.transferBit("unknownFlags", "unknownFlag0x8")
    transferer.transferBit("unknownFlags", "unknownFlag0x200")
    transferer.transferEnum("blendMode")
    transferer.transferInt("priority")
    transferer.transferFloat("specularity")
    transferer.transferFloat("specMult")
    transferer.transferFloat("emisMult")
    transferer.transferEnum("layerBlendType")
    transferer.transferEnum("emisBlendType")
    transferer.transferEnum("specType")
    
def transferDisplacementMaterial(transferer):
    transferer.transferString("name")
    transferer.transferAnimatableFloat("strengthFactor")
    transferer.transferInt("priority")

def transferCompositeMaterial(transferer):
    transferer.transferString("name")

def transferCompositeMaterialSection(transferer):
    transferer.transferAnimatableFloat("alphaFactor")

def transferTerrainMaterial(transferer):
    transferer.transferString("name")

def transferVolumeMaterial(transferer):
    transferer.transferString("name")
    transferer.transferAnimatableFloat("volumeDensity")

def transferCreepMaterial(transferer):
    transferer.transferString("name")

def transferMaterialLayer(transferer):
    transferer.transferString("imagePath")
    transferer.transferInt("unknown11")
    transferer.transferAnimatableColor("color")
    transferer.transferBit("flags", "textureWrapX")
    transferer.transferBit("flags", "textureWrapY")
    transferer.transferBit("flags", "colorEnabled")
    transferer.transferEnum("uvSource")
    transferer.transferBit("alphaFlags", "alphaAsTeamColor")
    transferer.transferBit("alphaFlags", "alphaOnly")
    transferer.transferBit("alphaFlags", "alphaBasedShading")
    transferer.transferAnimatableFloat("brightMult")
    transferer.transferAnimatableFloat("midtoneOffset")
    transferer.transferAnimatableVector2("uvOffset")
    transferer.transferAnimatableVector3("uvAngle")
    transferer.transferAnimatableVector2("uvTiling")
    transferer.transferAnimatableFloat("brightness")
    transferer.transferBit("tintFlags", "useTint")
    transferer.transferBit("tintFlags", "tintAlpha")
    transferer.transferFloat("tintStrength")
    transferer.transferFloat("tintStart")
    transferer.transferFloat("tintCutout")

def transferAnimation(transferer):
    transferer.transferString("name")
    transferer.transferFloat("movementSpeed")
    transferer.transferInt("frequency")
    transferer.transferBit("flags", "notLooping")
    transferer.transferBit("flags", "alwaysGlobal")
    transferer.transferBit("flags", "globalInPreviewer")
    
def transferSTC(transferer):
    transferer.transferBoolean("runsConcurrent")

def transferCamera(transferer):
    transferer.transferString("name")
    transferer.transferAnimatableFloat("fieldOfView")
    transferer.transferAnimatableFloat("farClip")
    transferer.transferAnimatableFloat("nearClip")
    transferer.transferAnimatableFloat("clip2")
    transferer.transferAnimatableFloat("focalDepth")
    transferer.transferAnimatableFloat("falloffStart")
    transferer.transferAnimatableFloat("falloffEnd")
    transferer.transferAnimatableFloat("depthOfField")

def transferFuzzyHitTest(transferer):
    transferer.transferEnum("shape")
    transferer.transferFloat("size0")
    transferer.transferFloat("size1") 
    transferer.transferFloat("size2")

def transferLight(transferer):
    transferer.transferEnum("lightType")
    transferer.transferAnimatableVector3("lightColor")
    transferer.transferBit("flags", "shadowCast")
    transferer.transferBit("flags", "specular")
    transferer.transferBit("flags", "unknownFlag0x04")
    transferer.transferBit("flags", "turnOn")
    transferer.transferBoolean("unknownAt8")
    transferer.transferAnimatableFloat("lightIntensity")
    transferer.transferAnimatableVector3("specColor")
    transferer.transferAnimatableFloat("specIntensity")
    transferer.transferAnimatableFloat("attenuationFar")
    transferer.transferFloat("unknownAt148")
    transferer.transferAnimatableFloat("attenuationNear")
    transferer.transferAnimatableFloat("hotSpot")
    transferer.transferAnimatableFloat("falloff")
    transferer.transferInt("unknownAt12")

def transferBoundings(transferer):
    transferer.transferAnimatableBoundings()

