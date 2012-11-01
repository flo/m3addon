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

if "bpy" in locals():
    import imp
    if "generateM3Library" in locals():
        imp.reload(generateM3Library)
from . import generateM3Library
generateM3Library.generateM3Library()

if "bpy" in locals():
    import imp
    if "m3" in locals():
        imp.reload(m3)
    if "shared" in locals():
        imp.reload(shared)

from . import m3
from . import shared
import bpy
import mathutils
import math
from bpy_extras import io_utils

def toBlenderQuaternion(m3Quaternion):
    return mathutils.Quaternion((m3Quaternion.w, m3Quaternion.x, m3Quaternion.y, m3Quaternion.z))

def toBlenderVector3(m3Vector3):
    return mathutils.Vector((m3Vector3.x, m3Vector3.y, m3Vector3.z))

def toBlenderVector2(m3Vector2):
    return mathutils.Vector((m3Vector2.x, m3Vector2.y))

def toBlenderColorVector(m3Color):
    return mathutils.Vector((m3Color.red /255.0, m3Color.green /255.0, m3Color.blue /255.0, m3Color.alpha /255.0))

def toBlenderUVCoordinate(m3UVCoordinate):
    return (m3UVCoordinate.x / 2048.0, 1 - m3UVCoordinate.y / 2048.0)

def toBlenderMatrix(m3Matrix):
    return mathutils.Matrix((
        (m3Matrix.x.x, m3Matrix.y.x, m3Matrix.z.x, m3Matrix.w.x),
        (m3Matrix.x.y, m3Matrix.y.y, m3Matrix.z.y, m3Matrix.w.y),
        (m3Matrix.x.z, m3Matrix.y.z, m3Matrix.z.z, m3Matrix.w.z),
        (m3Matrix.x.w, m3Matrix.y.w, m3Matrix.z.w, m3Matrix.w.w)
    ))

FRAME_RATE = 30.0



def msToFrame(timeInMS):
    return round(timeInMS / 1000.0 * FRAME_RATE)

def insertLinearKeyFrame(curve, frame, value):
    keyFrame = curve.keyframe_points.insert(frame, value)
    keyFrame.interpolation = "LINEAR"

def insertConstantKeyFrame(curve, frame, value):
    keyFrame = curve.keyframe_points.insert(frame, value)
    keyFrame.interpolation = "CONSTANT"


def frameValuePairs(timeValueMap):
    timeValues = list(timeValueMap.keys())
    timeValues.sort()
    for timeInMS in timeValues:
        frame = msToFrame(timeInMS)
        value = timeValueMap[timeInMS]
        yield(frame, value)
        
def extendTimeToValueMapByInterpolation(timeToVectorMap, wantedTimes, interpolationFunc):
    timesWithValues = list(timeToVectorMap.keys())
    timesWithValues.sort()
    wantedTimes = list(wantedTimes)
    wantedTimes.sort()
    
    wantedTimesIndex = 0
    leftInterpolationTime = timesWithValues[0]
    leftInterpolationValue = timeToVectorMap[leftInterpolationTime]
    while (wantedTimesIndex < len(wantedTimes)) and (wantedTimes[wantedTimesIndex] <= leftInterpolationTime):
        timeToVectorMap[wantedTimes[wantedTimesIndex]] = leftInterpolationValue
        wantedTimesIndex += 1
    
    if wantedTimesIndex == len(wantedTimes):
        return
    wantedTime = wantedTimes[wantedTimesIndex]

    for timeWithValue in timesWithValues[1:]:
        rightInterpolationTime = timeWithValue
        rightInterpolationValue = timeToVectorMap[rightInterpolationTime]
        while wantedTime <= rightInterpolationTime:
            if wantedTime == rightInterpolationTime:
                timeToVectorMap[wantedTime] = rightInterpolationValue
            else:
                timeSinceLeftTime =  wantedTime - leftInterpolationTime
                intervalLength = rightInterpolationTime - leftInterpolationTime
                rightFactor = timeSinceLeftTime / intervalLength
                leftFactor = 1 - rightFactor
                timeToVectorMap[wantedTime] = interpolationFunc(leftInterpolationValue, rightInterpolationValue, rightFactor)
            wantedTimesIndex += 1
            if wantedTimesIndex == len(wantedTimes):
                return
            wantedTime = wantedTimes[wantedTimesIndex]
        leftInterpolationTime = rightInterpolationTime
        leftInterpolationValue = rightInterpolationValue

    for wantedTime in wantedTimes[wantedTimesIndex:]:
        timeToVectorMap[wantedTime] = leftInterpolationValue

def extendTimeToVectorMapByInterpolation(timeToVectorMap, wantedTimes):
    return extendTimeToValueMapByInterpolation(timeToVectorMap, wantedTimes, shared.vectorInterpolationFunction)

def extendTimeToQuaternionMapByInterpolation(timeToVectorMap, wantedTimes):
    return extendTimeToValueMapByInterpolation(timeToVectorMap, wantedTimes, shared.quaternionInterpolationFunction)

def convertToBlenderVector3Map(timeToM3VectorMap):
    result = {}
    for key, m3Vector3 in timeToM3VectorMap.items():
        result[key] = toBlenderVector3(m3Vector3)
    return result
    
def convertToBlenderQuaternionMap(timeToM3VectorMap):
    result = {}
    for key, m3Quaternion in timeToM3VectorMap.items():
        result[key] = toBlenderQuaternion(m3Quaternion)
    return result


def visualizeMatrix(matrix):
    mesh = bpy.data.meshes.new('AxisMesh')
    meshObject = bpy.data.objects.new('AxisMesh', mesh)
    meshObject.location = (0,0,0)
    meshObject.show_name = True
    oVertex = matrix.translation
    matrix3x3 = matrix.to_3x3()
    xVertex = oVertex + matrix3x3.col[0]
    yVertex = oVertex + matrix3x3.col[1]
    zVertex = oVertex + matrix3x3.col[2]
    vertices = [oVertex, xVertex,yVertex,zVertex]
    edges = [(0,1),(0,2),(0,3)]
    bpy.context.scene.objects.link(meshObject)
    mesh.from_pydata(vertices, edges, [])
    mesh.update(calc_edges=True)
    
def checkOrder(boneEntries):
    index = 0
    for boneEntry in boneEntries:
        if boneEntry.parent != -1:
            if (boneEntry.parent >= index):
                raise Exception("Bones are not sorted as expected")
        index += 1



def determineTails(m3Bones, heads, boneDirectionVectors, absoluteScales):
    childBoneIndexLists = []
    for boneIndex, boneEntry in enumerate(m3Bones):
        childBoneIndexLists.append([])
        if boneEntry.parent != -1:
            childBoneIndexLists[boneEntry.parent].append(boneIndex)
    
    tails = []
    for m3Bone, head, childIndices, boneDirectionVector, absoluteScale in zip(m3Bones, heads, childBoneIndexLists, boneDirectionVectors, absoluteScales):
        skinned = m3Bone.getNamedBit("flags", "skinned")
        length = 0.1
        for childIndex in childIndices:
            headToChildHead = heads[childIndex] - head
            if headToChildHead.length >= 0.0001:
                if abs(headToChildHead.angle(boneDirectionVector)) < 0.1:
                    length = headToChildHead.length 
        tailOffset = length * boneDirectionVector
        for i in range(3):
            tailOffset[i] /= absoluteScale[i]
        tail = head + tailOffset
        tails.append(tail)
    return tails

def determineRolls(absoluteBoneRestPositions, heads, tails):
    rolls = []
    for absBoneRestMatrix, head, tail in zip(absoluteBoneRestPositions, heads, tails):
        editBoneMatrix = boneMatrix(head=head, tail=tail, roll=0)
        boneMatrix3x3 = editBoneMatrix.to_3x3()

        angleZToZ = boneMatrix3x3.col[2].angle(absBoneRestMatrix.col[2].to_3d())
        angleZToX = boneMatrix3x3.col[2].angle(absBoneRestMatrix.col[0].to_3d())
        
        if angleZToX > math.pi / 2.0:
            rollAngle = angleZToZ
        else:
            rollAngle = -angleZToZ

        rolls.append(rollAngle)
    return rolls

def determineAbsoluteBoneRestPositions(model):
    matrices = []
    for inverseBoneRestPosition in model.absoluteInverseBoneRestPositions:
        matrix = toBlenderMatrix(inverseBoneRestPosition.matrix)
        matrix = matrix.inverted()
        matrix = matrix * shared.rotFixMatrix        
        matrices.append(matrix)
    return matrices

ownerTypeScene = "Scene"
ownerTypeArmature = "Armature"          
                
class M3ToBlenderDataTransferer:
    def __init__(self, importer, animPathPrefix, blenderObject, m3Object):
        self.importer = importer
        self.animPathPrefix = animPathPrefix
        self.blenderObject = blenderObject
        self.m3Object = m3Object
    
    def transferAnimatableFloat(self, fieldName):
        animationReference = getattr(self.m3Object, fieldName)
        setattr(self.blenderObject, fieldName, animationReference.initValue)
        animationHeader = animationReference.header
        animId = animationHeader.animId
        animPath = self.animPathPrefix +  fieldName
        defaultValue = animationReference.initValue
        self.importer.animateFloat(ownerTypeScene, animPath, animId, defaultValue)
        
    def transferAnimatableInteger(self, fieldName):
        """ Helper method"""
        animationReference = getattr(self.m3Object, fieldName)
        setattr(self.blenderObject, fieldName, animationReference.initValue)
        animationHeader = animationReference.header
        animId = animationHeader.animId
        animPath = self.animPathPrefix + fieldName
        defaultValue = animationReference.initValue
        self.importer.animateInteger(ownerTypeScene, animPath, animId, defaultValue)

    def transferAnimatableInt16(self, fieldName):
        self.transferAnimatableInteger(fieldName)

    def transferAnimatableUInt32(self, fieldName):
        self.transferAnimatableInteger(fieldName)

    
    def transferFloat(self, fieldName):
        setattr(self.blenderObject, fieldName, getattr(self.m3Object, fieldName))
        
    def transferInt(self, fieldName):
        setattr(self.blenderObject, fieldName, getattr(self.m3Object, fieldName))
        
    def transferString(self, fieldName):
        value = getattr(self.m3Object, fieldName)
        if value == None:
            value = ""
        setattr(self.blenderObject, fieldName, value)

    def transferBoolean(self, fieldName):
        integerValue = getattr(self.m3Object, fieldName)
        if integerValue == 0:
            setattr(self.blenderObject, fieldName, False)
        elif integerValue == 1:
            setattr(self.blenderObject, fieldName, True)
        else:
            print("WARNING: %s was neither 0 nor 1" % fieldName)
            
    def transferBit(self, m3FieldName, bitName):
        setattr(self.blenderObject, bitName, self.m3Object.getNamedBit(m3FieldName, bitName))
    
    def transfer16Bits(self, fieldName):
        integerValue = getattr(self.m3Object, fieldName)
        vector = getattr(self.blenderObject, fieldName)
        for bitIndex in range(0, 16):
            mask = 1 << bitIndex
            vector[bitIndex] = (mask & integerValue) > 0
    
    def transfer32Bits(self, fieldName):
        integerValue = getattr(self.m3Object, fieldName)
        vector = getattr(self.blenderObject, fieldName)
        for bitIndex in range(0, 32):
            mask = 1 << bitIndex 
            vector[bitIndex] = (mask & integerValue) > 0   
    
    def transferAnimatableVector3(self, fieldName):
        animationReference = getattr(self.m3Object, fieldName)
        setattr(self.blenderObject, fieldName, toBlenderVector3(animationReference.initValue))
        animationHeader = animationReference.header
        animId = animationHeader.animId
        animPath = self.animPathPrefix + fieldName
        defaultValue = animationReference.initValue
        self.importer.animateVector3(ownerTypeScene, animPath, animId, defaultValue)

    def transferAnimatableVector2(self, fieldName):
        animationReference = getattr(self.m3Object, fieldName)
        setattr(self.blenderObject, fieldName, toBlenderVector2(animationReference.initValue))
        animationHeader = animationReference.header
        animId = animationHeader.animId
        animPath = self.animPathPrefix + fieldName
        defaultValue = animationReference.initValue
        self.importer.animateVector2(ownerTypeScene, animPath, animId, defaultValue)

        
    def transferAnimatableColor(self, fieldName):
        animationReference = getattr(self.m3Object, fieldName)
        setattr(self.blenderObject, fieldName, toBlenderColorVector(animationReference.initValue))
        animationHeader = animationReference.header
        animId = animationHeader.animId
        animPath = self.animPathPrefix + fieldName
        defaultValue = animationReference.initValue
        self.importer.animateColor(ownerTypeScene, animPath, animId, defaultValue)
        
        
    def transferAnimatableBoundings(self):
        animationReference = self.m3Object
        animationHeader = animationReference.header
        animId = animationHeader.animId
        boundingsObject = self.blenderObject
        animPathMinBorder = self.animPathPrefix + "minBorder"
        animPathMaxBorder = self.animPathPrefix +  "maxBorder"
        animPathRadius = self.animPathPrefix + "radius"
        m3InitValue = animationReference.initValue
        boundingsObject.minBorder = toBlenderVector3(m3InitValue.minBorder)
        boundingsObject.maxBorder = toBlenderVector3(m3InitValue.maxBorder)
        boundingsObject.radius = m3InitValue.radius
        minBorderDefault = toBlenderVector3(m3InitValue.minBorder)
        maxBorderDefault = toBlenderVector3(m3InitValue.maxBorder)
        radiusDefault = m3InitValue.radius
        self.importer.animateBoundings(ownerTypeScene, animPathMinBorder, animPathMaxBorder, animPathRadius, animId, minBorderDefault, maxBorderDefault, radiusDefault)


    def transferEnum(self, fieldName):
        value = str(getattr(self.m3Object, fieldName))
        setattr(self.blenderObject, fieldName, value)

class AnimationData:
    def __init__(self, animIdToTimeValueMap, ownerTypeToActionMap, animationIndex):
        self.animIdToTimeValueMap = animIdToTimeValueMap
        self.ownerTypeToActionMap = ownerTypeToActionMap
        # The animation object can't be stored in this structure
        # as it seems to get invalid when the mode changes
        # To avoid a blender crash an index is used to obtain a valid instance of the animation
        self.animationIndex = animationIndex

    
class Importer:
    
    def importFile(self, filename):
        scene = bpy.context.scene
        self.scene = scene
        self.model = m3.loadModel(filename)
        self.armature = bpy.data.armatures.new(name="Armature")
        scene.render.fps = FRAME_RATE
        self.animations = []
        self.ownerTypeToDefaultValuesActionMap = {}
        self.animIdToLongAnimIdMap = {}
        self.storeModelId()
        self.createAnimations()
        self.createArmatureObject()
        self.createBones()
        self.createMaterials()
        self.createCameras()
        self.createFuzzyHitTests()
        self.initTightHitTest()
        self.createParticleSystems()
        self.createForces()
        self.createRigidBodies()
        self.createLights()
        self.createAttachmentPoints()
        self.createMesh()
        self.createBoundings()
        # init stcs of animations at last
        # when all animation properties are known
        self.initSTCsOfAnimations()
        
        if len(scene.m3_animations) >= 1:
            scene.m3_animation_old_index = -1
            scene.m3_animation_index = -1
            scene.m3_animation_index = 0
    
    def addAnimIdData(self, animId, objectId, animPath):
        longAnimId = shared.getLongAnimIdOf(objectId, animPath)
        self.animIdToLongAnimIdMap[animId] = longAnimId
        animIdData = self.scene.m3_animation_ids.add()
        animIdData.animIdMinus2147483648 = animId - 2147483648
        animIdData.longAnimId = longAnimId
        
    def storeModelId(self):
        self.addAnimIdData(self.model.uniqueUnknownNumber, objectId=(shared.animObjectIdModel), animPath="")

    def createArmatureObject(self):
        #bpy.ops.object.mode_set(mode='OBJECT')
        #alternative: armature = bpy.ops.object.armature_add(view_align=False,enter_editmode=False, location=location, rotation=(0,0,0), layers=firstLayerOnly)
        currentScene = bpy.context.scene
        armatureObject = bpy.data.objects.new("Armature Object", self.armature)
        currentScene.objects.link(armatureObject)
        currentScene.objects.active = armatureObject
        armatureObject.select = True
        self.armatureObject = armatureObject

        
    def createBones(self):
        """ Imports the bones 
        
        About the bone import:
        Let m_i be the matrix which does the rotation, scale and translation specified in the m3 file for a given bone i
        
        Since the matrix is relative to it's parent bone, the absolut transformation done by a bone 2 can be calculated with:
        F_2 = m_0 * m_1 * m_2 where bone 1 is the parent of bone 2 and bone 0 is the parent of bone 1
        
        The bone i in blender should have then the transformation F_i plus maybe a rotation fix r_i to have bones point to each other:
        f_2 = F_2 * r_2 = m_0 * m_ 1 * m_2 * r_2
        
        
        In blender however there is the concept of a rest position of an armature.
        A bone like it's seen in Blender's edit mode has an absolute transformation matrix
        This absolute transformation matrix E_i of a bone i can be used to calculate a relative matrix called e_i:
        E_i = E_parent * e_i <=> e_i = E_parent^-1 * E_i 
        The rotation, location and scale specified in the pose mode can be used to calculate a relative pose matrix p_i for a bone i
        For a bone 2 with parent 1, and grandparent 0 the final transformation gets calculated like this:
        f_2 = (e_0 * p_0) * (e_1 * p_1) * (e_2 * p_2)
        The goal is now to determine p_i so that f_2 is the same as:
        f_2 = m_0 * m_1 * m_2 * r_2 <=>
        f_2 = E * m_0 * E * m_1 * E * m_2 * r_2 <=>
        f_2 = (e_0 * e_0^-1)  * m_0 * (r_0 * e_1 * e_1^-1 * r_0^-1) * m_1 * (r_1 * e_2 * e_2^-1 * r_1^-1) * m_2 * r_2) <=>
        f_2 = e_0 * (e_0^-1  * m_0 * r_0) * e_1 * (e_1^-1 * r_0^-1 * m_1 * r_1) * e_2 * (e_2^-1 * r_1^-1 * m_2 * r_2)
        thus:
        p_0 = (e_0^-1  * m_0 * r_0)
        p_1 = (e_1^-1 * r_0^-1 * m_1 * r_1)
        p_2 =  (e_2^-1 * r_1^-1 * m_2 * r_2)
        
        In the following code is
        r_i = rotFixMatrix
        e_i = relEditBoneMatrices[i]
        """
        model = self.model
        print("Creating bone structure in rest position")

        absoluteBoneRestPositions = determineAbsoluteBoneRestPositions(model)
                    
        bpy.ops.object.mode_set(mode='EDIT')
        checkOrder(model.bones)
        
        absoluteScales = self.determineAbsoluteRestPosScales(absoluteBoneRestPositions)
        relativeScales = self.determineRelativeRestPosScales(absoluteScales, model.bones)

        heads = list(m.translation for m in absoluteBoneRestPositions)  
        # In blender the edit bone with the vector (0,1,0) stands for a idenity matrix
        # So the second column of a edit bone matrix represents the bone vector
        boneDirectionVectors = list(m.col[1].to_3d().normalized() for m in absoluteBoneRestPositions)
        tails = determineTails(model.bones, heads, boneDirectionVectors, absoluteScales)
        rolls = determineRolls(absoluteBoneRestPositions, heads , tails)

        editBones = self.createEditBones(model.bones, heads, tails, rolls, absoluteScales)
            
        
        relEditBoneMatrices = self.determineRelEditBoneMatrices(model.bones, editBones)

        print("Adjusting pose bones")
        bpy.ops.object.mode_set(mode='POSE')
        self.adjustPoseBones(model.bones, relEditBoneMatrices)
    
    def adjustPoseBones(self, m3Bones, relEditBoneMatrices):
        index = 0
        for bone, relEditBoneMatrix in zip(m3Bones, relEditBoneMatrices):
            poseBone = self.armatureObject.pose.bones[self.boneNames[index]]
            scale = toBlenderVector3(bone.scale.initValue)
            rotation = toBlenderQuaternion(bone.rotation.initValue)
            location = toBlenderVector3(bone.location.initValue)
            
            if bone.parent != -1:
                leftCorrectionMatrix = relEditBoneMatrix.inverted() * shared.rotFixMatrixInverted
                rightCorrectionMatrix = shared.rotFixMatrix
            else:
                leftCorrectionMatrix = relEditBoneMatrix.inverted()
                rightCorrectionMatrix = shared.rotFixMatrix
            
            _, leftRotCorrection, leftScaleCorrection = leftCorrectionMatrix.decompose()
            _, rightRotCorrection, rightScaleCorrection = rightCorrectionMatrix.decompose()
            
            location = leftCorrectionMatrix * location
            rotation = leftRotCorrection * rotation * rightRotCorrection

            poseBone.scale = scale
            poseBone.rotation_quaternion = rotation
            poseBone.location = location
            
            self.animateBone(index, bone, leftCorrectionMatrix, rightCorrectionMatrix, location, rotation, scale)
            index+=1
    def determineAbsoluteRestPosScales(self, absoluteBoneRestPositions):
        absoluteScales = []
        for absoluteBoneRestMatrix in absoluteBoneRestPositions:
            mat3x3 = absoluteBoneRestMatrix.to_3x3()
            scaleX = mat3x3.col[0].length
            scaleY = mat3x3.col[1].length
            scaleZ = mat3x3.col[2].length
            scaleVec = mathutils.Vector((scaleX, scaleY, scaleZ))
            absoluteScales.append(scaleVec)
        return absoluteScales
    def determineRelativeRestPosScales(self, absoluteScales, m3Bones):
        relativeScales = []
        for absoluteScale, m3Bone in zip(absoluteScales, m3Bones):
            relativeScale = absoluteScale.copy()
            if m3Bone.parent != -1:
                parentAbsScale = absoluteScales[m3Bone.parent]
                for i in range(3):
                    relativeScale[i] = absoluteScale[i] / parentAbsScale[i]
            relativeScales.append(relativeScale)
        return relativeScales

    def fix180DegreeRotationsInMapWithKeys(self, timeToRotationMap, timeEntries):
        previousRotation = None
        for timeInMS in timeEntries:
            rotation = timeToRotationMap.get(timeInMS)
            if previousRotation != None:
                shared.smoothQuaternionTransition(previousQuaternion=previousRotation, quaternionToFix=rotation)
            previousRotation = rotation        
            
    def applyCorrectionToLocRotScaleMaps(self, leftCorrectionMatrix, rightCorrectionMatrix, timeToLocationMap, timeToRotationMap, timeToScaleMap, timeEntries):
        for timeInMS in timeEntries:
            location = timeToLocationMap.get(timeInMS)
            rotation = timeToRotationMap.get(timeInMS)
            scale = timeToScaleMap.get(timeInMS)

            location = toBlenderVector3(location)
            rotation = toBlenderQuaternion(rotation)
            scale = toBlenderVector3(scale)
            relSpecifiedMatrix = shared.locRotScaleMatrix(location, rotation, scale)

            newMatrix = leftCorrectionMatrix * relSpecifiedMatrix * rightCorrectionMatrix
            location, rotation, scale = newMatrix.decompose()
            timeToLocationMap[timeInMS] = location
            timeToRotationMap[timeInMS] = rotation
            timeToScaleMap[timeInMS] = scale
        
    def animateBone(self, boneIndex, m3Bone, leftCorrectionMatrix, rightCorrectionMatrix, defaultLocation, defaultRotation, defaultScale):
        boneName = self.boneNames[boneIndex]
        locationAnimId = m3Bone.location.header.animId
        locationAnimPath = 'pose.bones["%s"].location' % boneName
        self.addAnimIdData(locationAnimId, objectId=shared.animObjectIdArmature, animPath=locationAnimPath)

        rotationAnimId = m3Bone.rotation.header.animId
        rotationAnimPath = 'pose.bones["%s"].rotation_quaternion' % boneName
        self.addAnimIdData(rotationAnimId, objectId=shared.animObjectIdArmature, animPath=rotationAnimPath)
        
        scaleAnimId = m3Bone.scale.header.animId
        scaleAnimPath = 'pose.bones["%s"].scale' % boneName
        self.addAnimIdData(scaleAnimId, objectId=shared.animObjectIdArmature, animPath=scaleAnimPath)

        for animationData in self.animations:
            scene = bpy.context.scene
            animation =  scene.m3_animations[animationData.animationIndex]
            animIdToTimeValueMap = animationData.animIdToTimeValueMap
            action = self.createOrGetActionFor(animationData, ownerTypeArmature)

            timeToLocationMap = animIdToTimeValueMap.get(locationAnimId,{0:m3Bone.location.initValue})
            timeToLocationMap = convertToBlenderVector3Map(timeToLocationMap)

            timeToRotationMap = animIdToTimeValueMap.get(rotationAnimId, {0:m3Bone.rotation.initValue})
            timeToRotationMap = convertToBlenderQuaternionMap(timeToRotationMap)

            timeToScaleMap = animIdToTimeValueMap.get(scaleAnimId,{0:m3Bone.scale.initValue})
            timeToScaleMap = convertToBlenderVector3Map(timeToScaleMap)

            rotKeys = list(timeToRotationMap.keys())
            rotKeys.sort()
            self.fix180DegreeRotationsInMapWithKeys(timeToRotationMap, rotKeys)

            timeEntries = []
            timeEntries.extend(timeToLocationMap.keys())
            timeEntries.extend(timeToRotationMap.keys())
            timeEntries.extend(timeToScaleMap.keys())        
            timeEntries = list(set(timeEntries))#elimate duplicates
            timeEntries.sort()
            
            extendTimeToVectorMapByInterpolation(timeToLocationMap, timeEntries)
            extendTimeToQuaternionMapByInterpolation(timeToRotationMap, timeEntries)
            extendTimeToVectorMapByInterpolation(timeToScaleMap, timeEntries)
            
            self.applyCorrectionToLocRotScaleMaps(leftCorrectionMatrix, rightCorrectionMatrix, timeToLocationMap, timeToRotationMap, timeToScaleMap, timeEntries)

            self.fix180DegreeRotationsInMapWithKeys(timeToRotationMap, timeEntries)


            frames = []
            for timeInMS in timeEntries:
                frames.append(msToFrame(timeInMS))

            group = boneName
            if locationAnimId in animIdToTimeValueMap:
                locXCurve = action.fcurves.new(locationAnimPath, 0, group)
                locYCurve = action.fcurves.new(locationAnimPath, 1, group)
                locZCurve = action.fcurves.new(locationAnimPath, 2, group)
                for timeInMS, frame in zip(timeEntries, frames):
                    location = timeToLocationMap.get(timeInMS)
                    insertLinearKeyFrame(locXCurve, frame, location.x)
                    insertLinearKeyFrame(locYCurve, frame, location.y)
                    insertLinearKeyFrame(locZCurve, frame, location.z)
            
            if rotationAnimId in animIdToTimeValueMap:
                rotWCurve = action.fcurves.new(rotationAnimPath, 0, group)
                rotXCurve = action.fcurves.new(rotationAnimPath, 1, group)
                rotYCurve = action.fcurves.new(rotationAnimPath, 2, group)
                rotZCurve = action.fcurves.new(rotationAnimPath, 3, group)
                for timeInMS, frame in zip(timeEntries, frames):
                    rotation = timeToRotationMap.get(timeInMS)
                    insertLinearKeyFrame(rotWCurve, frame, rotation.w)
                    insertLinearKeyFrame(rotXCurve, frame, rotation.x)
                    insertLinearKeyFrame(rotYCurve, frame, rotation.y)
                    insertLinearKeyFrame(rotZCurve, frame, rotation.z)
                
            if scaleAnimId in animIdToTimeValueMap:
                scaXCurve = action.fcurves.new(scaleAnimPath, 0, group)
                scaYCurve = action.fcurves.new(scaleAnimPath, 1, group)
                scaZCurve = action.fcurves.new(scaleAnimPath, 2, group)
                for timeInMS, frame in zip(timeEntries, frames):
                    scale = timeToScaleMap.get(timeInMS)
                    insertLinearKeyFrame(scaXCurve, frame, scale.x)
                    insertLinearKeyFrame(scaYCurve, frame, scale.y)
                    insertLinearKeyFrame(scaZCurve, frame, scale.z)
    
    
    def createStandardMaterials(self, scene):
        for materialIndex, m3Material in enumerate(self.model.standardMaterials):
            material = scene.m3_standard_materials.add()
            animPathPrefix = "m3_standard_materials[%s]." % materialIndex
            materialTransferer = M3ToBlenderDataTransferer(self, animPathPrefix, blenderObject=material, m3Object=m3Material)
            shared.transferStandardMaterial(materialTransferer)
            layerIndex = 0
            for (layerName, layerFieldName) in zip(shared.standardMaterialLayerNames, shared.standardMaterialLayerFieldNames):
                materialLayersEntry = getattr(m3Material, layerFieldName)[0]
                materialLayer = material.layers.add()
                materialLayer.name = layerName
                animPathPrefix = "m3_standard_materials[%s].layers[%s]." % (materialIndex, layerIndex)
                layerTransferer = M3ToBlenderDataTransferer(self, animPathPrefix, blenderObject=materialLayer, m3Object=materialLayersEntry)
                shared.transferMaterialLayer(layerTransferer)
                layerIndex += 1
    
    def createDisplacementMaterials(self, scene):
        for materialIndex, m3Material in enumerate(self.model.displacementMaterials):
            material = scene.m3_displacement_materials.add()
            animPathPrefix = "m3_displacement_materials[%s]." % materialIndex
            materialTransferer = M3ToBlenderDataTransferer(self, animPathPrefix, blenderObject=material, m3Object=m3Material)
            shared.transferDisplacementMaterial(materialTransferer)
            layerIndex = 0
            for (layerName, layerFieldName) in zip(shared.displacementMaterialLayerNames, shared.displacementMaterialLayerFieldNames):
                materialLayersEntry = getattr(m3Material, layerFieldName)[0]
                materialLayer = material.layers.add()
                materialLayer.name = layerName
                animPathPrefix = "m3_displacement_materials[%s].layers[%s]." % (materialIndex, layerIndex)
                layerTransferer = M3ToBlenderDataTransferer(self, animPathPrefix, blenderObject=materialLayer, m3Object=materialLayersEntry)
                shared.transferMaterialLayer(layerTransferer)
                layerIndex += 1

    def createCompositeMaterials(self, scene):
        for materialIndex, m3Material in enumerate(self.model.compositeMaterials):
            material = scene.m3_composite_materials.add()
            animPathPrefix = "m3_composite_materials[%s]." % materialIndex
            materialTransferer = M3ToBlenderDataTransferer(self, animPathPrefix, blenderObject=material, m3Object=m3Material)
            shared.transferCompositeMaterial(materialTransferer)
            for sectionIndex, m3Section in enumerate(m3Material.sections):
                section = material.sections.add()
                animPathPrefix = "m3_composite_materials[%s].sections[%s]." % (materialIndex, sectionIndex)
                materialSectionTransferer = M3ToBlenderDataTransferer(self, animPathPrefix, blenderObject=section, m3Object=m3Section)
                shared.transferCompositeMaterialSection(materialSectionTransferer)
                section.name = self.getNameOfMaterialWithReferenceIndex(m3Section.materialReferenceIndex)

    def createTerrainMaterials(self, scene):
        for materialIndex, m3Material in enumerate(self.model.terrainMaterials):
            material = scene.m3_terrain_materials.add()
            animPathPrefix = "m3_terrain_materials[%s]." % materialIndex
            materialTransferer = M3ToBlenderDataTransferer(self, animPathPrefix, blenderObject=material, m3Object=m3Material)
            shared.transferTerrainMaterial(materialTransferer)
            layerIndex = 0
            for (layerName, layerFieldName) in zip(shared.terrainMaterialLayerNames, shared.terrainMaterialLayerFieldNames):
                materialLayersEntry = getattr(m3Material, layerFieldName)[0]
                materialLayer = material.layers.add()
                materialLayer.name = layerName
                animPathPrefix = "m3_terrain_materials[%s].layers[%s]." % (materialIndex, layerIndex)
                layerTransferer = M3ToBlenderDataTransferer(self, animPathPrefix, blenderObject=materialLayer, m3Object=materialLayersEntry)
                shared.transferMaterialLayer(layerTransferer)
                layerIndex += 1

    def createVolumeMaterials(self, scene):
        for materialIndex, m3Material in enumerate(self.model.volumeMaterials):
            material = scene.m3_volume_materials.add()
            animPathPrefix = "m3_volume_materials[%s]." % materialIndex
            materialTransferer = M3ToBlenderDataTransferer(self, animPathPrefix, blenderObject=material, m3Object=m3Material)
            shared.transferVolumeMaterial(materialTransferer)
            layerIndex = 0
            for (layerName, layerFieldName) in zip(shared.volumeMaterialLayerNames, shared.volumeMaterialLayerFieldNames):
                materialLayersEntry = getattr(m3Material, layerFieldName)[0]
                materialLayer = material.layers.add()
                materialLayer.name = layerName
                animPathPrefix = "m3_volume_materials[%s].layers[%s]." % (materialIndex, layerIndex)
                layerTransferer = M3ToBlenderDataTransferer(self, animPathPrefix, blenderObject=materialLayer, m3Object=materialLayersEntry)
                shared.transferMaterialLayer(layerTransferer)
                layerIndex += 1

    def createMaterialReferences(self, scene):
        for m3MaterialReference in self.model.materialReferences:
            materialType = m3MaterialReference.materialType
            materialIndex = m3MaterialReference.materialIndex
            material = shared.getMaterial(scene, materialType, materialIndex)
            if material == None:
                raise Exception("Model contains unsupported material type %s" % materialType)
            materialReference = scene.m3_material_references.add()
            materialReference.name = material.name
            materialReference.materialType = materialType
            materialReference.materialIndex = materialIndex
    
    def initMaterialReferenceIndexToNameMap(self):
        self.materialReferenceIndexToNameMap = {}
        for materialReferenceIndex, materialReference in enumerate(self.model.materialReferences):
            materialName = self.getMaterialNameByM3MaterialReference(materialReference)
            self.materialReferenceIndexToNameMap[materialReferenceIndex] = materialName
                
            
    def getMaterialNameByM3MaterialReference(self, materialReference):
        materialIndex = materialReference.materialIndex
        materialType = materialReference.materialType
        if materialType == shared.standardMaterialTypeIndex:
            return self.model.standardMaterials[materialIndex].name
        elif materialType == shared.displacementMaterialTypeIndex:
            return self.model.displacementMaterials[materialIndex].name
        elif materialType == shared.compositeMaterialTypeIndex:
            return self.model.compositeMaterials[materialIndex].name
        elif materialType == shared.terrainMaterialTypeIndex:
            return self.model.terrainMaterials[materialIndex].name
        elif materialType == shared.volumeMaterialTypeIndex:
            return self.model.volumeMaterials[materialIndex].name
        else:
            return None
        
    def createMaterials(self):
        print("Loading materials")
        scene = bpy.context.scene
        self.initMaterialReferenceIndexToNameMap()
        self.createStandardMaterials(scene)
        self.createDisplacementMaterials(scene)
        self.createCompositeMaterials(scene)
        self.createTerrainMaterials(scene)
        self.createVolumeMaterials(scene)
        self.createMaterialReferences(scene)

    def createCameras(self):
        scene = bpy.context.scene
        print("Loading cameras")
        for cameraIndex, m3Camera in enumerate(self.model.cameras):
            camera = scene.m3_cameras.add()
            animPathPrefix = "m3_cameras[%s]." % cameraIndex
            transferer = M3ToBlenderDataTransferer(self, animPathPrefix, blenderObject=camera, m3Object=m3Camera)
            shared.transferCamera(transferer)
            m3Bone = self.model.bones[m3Camera.boneIndex]
            if m3Bone.name != camera.name:
                raise Exception("Bone of camera '%s' had different name: '%s'" % (camera.name, m3Bone.name))


    def intShapeObject(self, blenderShapeObject, m3ShapeObject):
        blenderShapeObject.updateBlenderBoneShapes = False
        transferer = M3ToBlenderDataTransferer(self, None, blenderObject=blenderShapeObject, m3Object=m3ShapeObject)
        shared.transferFuzzyHitTest(transferer)
        matrix = toBlenderMatrix(m3ShapeObject.matrix)
        offset, rotation, scale = matrix.decompose()
        blenderShapeObject.offset = offset
        blenderShapeObject.rotationEuler = rotation.to_euler("XYZ")
        blenderShapeObject.scale = scale
        if m3ShapeObject.boneIndex != -1:
            m3Bone = self.model.bones[m3ShapeObject.boneIndex]
            blenderShapeObject.name = m3Bone.name
            bone = self.armature.bones[self.boneNames[m3ShapeObject.boneIndex]]
            poseBone = self.armatureObject.pose.bones[self.boneNames[m3ShapeObject.boneIndex]]
            shared.updateBoneShapeOfShapeObject(blenderShapeObject, bone, poseBone)
        blenderShapeObject.updateBlenderBoneShapes = True


    def initTightHitTest(self):
        print("Loading tight hit test shape")
        scene = bpy.context.scene
        self.intShapeObject(scene.m3_tight_hit_test, self.model.tightHitTest)

    def createFuzzyHitTests(self):
        scene = bpy.context.scene
        print("Loading fuzzy hit tests")
        for index, m3FuzzyHitTest in enumerate(self.model.fuzzyHitTestObjects):
            fuzzyHitTest = scene.m3_fuzzy_hit_tests.add()
            self.intShapeObject(fuzzyHitTest, m3FuzzyHitTest)
    
    def createBoundings(self):
        scene = bpy.context.scene
        if len(self.model.divisions) != 1 or len(self.model.divisions[0].msec) != 1:
            raise Exception("Unsupported Model type: Model has more then one division or msec per division")
        m3Boundings = self.model.divisions[0].msec[0].boundingsAnimation
        boundingsObject = scene.m3_boundings
        animPathPrefix = "m3_boundings."
        transferer = M3ToBlenderDataTransferer(self, animPathPrefix, blenderObject=boundingsObject, m3Object=m3Boundings)
        shared.transferBoundings(transferer)

    
    def createParticleSystems(self):
        currentScene = bpy.context.scene
        print("Loading particle systems")
        for particleSystemIndex, m3ParticleSystem in enumerate(self.model.particles):
            particleSystem = currentScene.m3_particle_systems.add()
            particleSystem.updateBlenderBoneShapes = False
            animPathPrefix = "m3_particle_systems[%s]." % particleSystemIndex
            transferer = M3ToBlenderDataTransferer(self, animPathPrefix, blenderObject=particleSystem, m3Object=m3ParticleSystem)
            shared.transferParticleSystem(transferer)
            boneEntry = self.model.bones[m3ParticleSystem.bone]
            fullBoneName = boneEntry.name
            if fullBoneName.startswith(shared.star2ParticlePrefix):
                particleSystem.boneSuffix = fullBoneName[len(shared.star2ParticlePrefix):]
            else:
                print("Warning: A particle system was bound to bone %s which does not start with %s" %(fullBoneName, shared.star2ParticlePrefix))
                particleSystem.boneSuffix = fullBoneName
            blenderBoneName = self.boneNames[m3ParticleSystem.bone]
            particleSystem.boneName = blenderBoneName
            
            bone = self.armature.bones[blenderBoneName]
            poseBone = self.armatureObject.pose.bones[blenderBoneName]
            shared.updateBoneShapeOfParticleSystem(particleSystem, bone, poseBone)
            

            particleSystem.materialName = self.getNameOfMaterialWithReferenceIndex(m3ParticleSystem.materialReferenceIndex)
            if m3ParticleSystem.forceChannelsCopy != m3ParticleSystem.forceChannels:
                print("Warning: Unexpected model content: forceChannels != forceChannelsCopy")

            for blenderCopyIndex, m3CopyIndex in enumerate(m3ParticleSystem.copyIndices):
                m3Copy = self.model.particleCopies[m3CopyIndex]
                copy = particleSystem.copies.add()
                copyAnimPathPrefix = animPathPrefix + "copies[%d]." % blenderCopyIndex
                transferer = M3ToBlenderDataTransferer(self, copyAnimPathPrefix, blenderObject=copy, m3Object=m3Copy)
                shared.transferParticleSystemCopy(transferer)
                m3Bone = self.model.bones[m3Copy.bone]
                fullCopyBoneName = m3Bone.name
                
                blenderBoneName = self.boneNames[m3Copy.bone]
                copy.boneName = blenderBoneName
                
                bone = self.armature.bones[blenderBoneName]
                poseBone = self.armatureObject.pose.bones[blenderBoneName]
                shared.updateBoneShapeOfParticleSystem(particleSystem, bone, poseBone)

                
                if fullCopyBoneName.startswith(shared.star2ParticlePrefix):
                    copy.name = fullCopyBoneName[len(shared.star2ParticlePrefix):]
                else:
                    print("Warning: A particle system copy was bound to bone %s which does not start with %s" %(fullBoneName, shared.star2ParticlePrefix))
                    copy.name = fullCopyBoneName
            particleSystem.updateBlenderBoneShapes = True

    def createForces(self):
        currentScene = bpy.context.scene
        print("Loading forces")
        for forceIndex, m3Force in enumerate(self.model.forces):
            force = currentScene.m3_forces.add()
            animPathPrefix = "m3_forces[%s]." % forceIndex
            transferer = M3ToBlenderDataTransferer(self, animPathPrefix, blenderObject=force, m3Object=m3Force)
            shared.transferForce(transferer)
            boneEntry = self.model.bones[m3Force.boneIndex]
            fullBoneName = boneEntry.name
            if fullBoneName.startswith(shared.star2ForcePrefix):
                force.boneSuffix = fullBoneName[len(shared.star2ForcePrefix):]
            else:
                print("Warning: A force was bound to bone %s which does not start with %s" %(fullBoneName, shared.star2ForcePrefix))
                force.boneSuffix = fullBoneName
    
    def createRigidBodies(self):
        currentScene = bpy.context.scene
        print("Loading rigid bodies")
        for rigidBodyIndex, m3RigidBody in enumerate(self.model.rigidBodies):
            rigid_body = currentScene.m3_rigid_bodies.add()
            animPathPrefix = "m3_rigid_bodies[%s]." % rigidBodyIndex
            transferer = M3ToBlenderDataTransferer(self, animPathPrefix, blenderObject=rigid_body, m3Object=m3RigidBody)
            shared.transferRigidBody(transferer)
            boneEntry = self.model.bones[m3RigidBody.boneIndex]
            rigid_body.name = boneEntry.name
            rigid_body.boneName = boneEntry.name
            
            for physicsShapeIndex, m3PhysicsShape in enumerate(m3RigidBody.physicsShapes):
                physics_shape = rigid_body.physicsShapes.add()
                physics_shape.updateBlenderBoneShapes = False
                
                animPathPrefix = "m3_physics_shapes[%s]." % physicsShapeIndex
                transferer = M3ToBlenderDataTransferer(self, animPathPrefix, blenderObject=physics_shape, m3Object=m3PhysicsShape)
                shared.transferPhysicsShape(transferer)
                
                physics_shape.name = "%d" % (physicsShapeIndex + 1)
                matrix = toBlenderMatrix(m3PhysicsShape.matrix)
                offset, rotation, scale = matrix.decompose()
                physics_shape.offset = offset
                physics_shape.rotationEuler = rotation.to_euler("XYZ")
                physics_shape.scale = scale
                
                if physics_shape.shape in ["4", "5"]: # convex hull or mesh
                    vertices = [(v.x, v.y, v.z) for v in m3PhysicsShape.vertices]
                    
                    indices = range(0, len(m3PhysicsShape.faces), 3)
                    faces = [m3PhysicsShape.faces[i : i+3] for i in indices]
                    
                    mesh = bpy.data.meshes.new('PhysicsMesh')
                    mesh.from_pydata(vertices = vertices, faces = faces, edges = [])
                    mesh.update(calc_edges = True)
                    
                    meshObject = bpy.data.objects.new('PhysicsMeshObject', mesh)
                    meshObject.location = (0,0,0)
                    meshObject.show_name = True
                    
                    # TODO - either:
                    # don't put mesh in scene (have edit button in physics shape - add to scene in edit mode / remove afterwards)?
                    # exclude from export somehow (update when edited)?
                    bpy.context.scene.objects.link(meshObject)
                    
                    physics_shape.meshObjectName = meshObject.name
                
                physics_shape.updateBlenderBoneShapes = True
            
            shared.updateBoneShapeOfRigidBody(currentScene, rigid_body)
            
    
    def createLights(self):
        currentScene = bpy.context.scene
        print("Loading lights")
        for lightIndex, m3Light in enumerate(self.model.lights):
            light = currentScene.m3_lights.add()
            light.updateBlenderBone = False
            animPathPrefix = "m3_lights[%s]." % lightIndex
            transferer = M3ToBlenderDataTransferer(self, animPathPrefix, blenderObject=light, m3Object=m3Light)
            shared.transferLight(transferer)
            boneEntry = self.model.bones[m3Light.boneIndex]
            fullBoneName = boneEntry.name
            lightPrefix =  shared.lightPrefixMap.get(str(m3Light.lightType))
            if fullBoneName.startswith(lightPrefix):
                light.boneSuffix = fullBoneName[len(lightPrefix):]
            else:
                print("Warning: A light was bound to bone %s which does not start with %s" %(fullBoneName, lightPrefix))
                light.boneSuffix = fullBoneName
            blenderBoneName = self.boneNames[m3Light.boneIndex]
            light.boneName = blenderBoneName
            bone = self.armature.bones[blenderBoneName]
            poseBone = self.armatureObject.pose.bones[blenderBoneName]
            shared.updateBoneShapeOfLight(light, bone, poseBone)
            light.updateBlenderBone = True

    def createAttachmentPoints(self):
        print("Loading attachment points and volumes")
        currentScene = bpy.context.scene
        
        boneIndexToM3AttachmentVolumeMap = {}
        for m3AttchmentVolume in self.model.attachmentVolumes:
            if m3AttchmentVolume.bone0 != m3AttchmentVolume.bone1 or m3AttchmentVolume.bone0 != m3AttchmentVolume.bone2:
                raise Exception("Can't handle a special attachment volume")
            boneIndex = m3AttchmentVolume.bone0
            if not m3AttchmentVolume.type in [0, 1, 2, 3, 4]:
                raise Exception("Unhandled attachment volume type %d" % m3AttchmentVolume.type)
            if boneIndex in boneIndexToM3AttachmentVolumeMap:
                raise Exception("Found two attachment volumes for one attachment points")
            boneIndexToM3AttachmentVolumeMap[boneIndex] = m3AttchmentVolume

        for attachmentPointIndex, m3AttachmentPoint in enumerate(self.model.attachmentPoints):
            boneIndex = m3AttachmentPoint.bone
            attachmentPoint = currentScene.m3_attachment_points.add()
            attachmentPoint.updateBlenderBone = False
            m3AttchmentVolume = boneIndexToM3AttachmentVolumeMap.get(boneIndex)
            if m3AttchmentVolume == None:
                attachmentPoint.volumeType = "-1"
            else:
                attachmentPoint.volumeType = str(m3AttchmentVolume.type)
                attachmentPoint.volumeSize0 = m3AttchmentVolume.size0
                attachmentPoint.volumeSize1 = m3AttchmentVolume.size1
                attachmentPoint.volumeSize2 = m3AttchmentVolume.size2
            
            prefixedName = m3AttachmentPoint.name
            if not prefixedName.startswith(shared.attachmentPointPrefix):
                print("Warning: The name of the attachment %s does not start with %s" %(prefixedName, shared.attachmentPointPrefix))
            attachmentName = prefixedName[len(shared.attachmentPointPrefix):]
            attachmentPoint.boneSuffix = attachmentName
            boneEntry = self.model.bones[boneIndex]
            expectedBoneName = shared.boneNameForAttachmentPoint(attachmentPoint)
            if boneEntry.name != expectedBoneName:
                print("Warning: The attachment bone %s did not have the name %s as expected" %(boneEntry.name, expectedBoneName))
            # Some long bones need to be renamed. 
            # The adjusted bone names get stored in self.boneNames:
            boneNameInBlender = self.boneNames[boneIndex]
            attachmentPoint.boneName = boneNameInBlender
            
            bone = self.armature.bones[boneNameInBlender]
            poseBone = self.armatureObject.pose.bones[boneNameInBlender]
            shared.updateBoneShapeOfAttachmentPoint(attachmentPoint, bone, poseBone)

            attachmentPoint.updateBlenderBone = True

    def getNameOfMaterialWithReferenceIndex(self, materialReferenceIndex):
        return self.materialReferenceIndexToNameMap[materialReferenceIndex] 

    def createMesh(self):
        model = self.model
        vertexClass = None
        if model.vFlags == 0x180007d:
            return # no vertices
        
        vertexClassName = "VertexFormat" + hex(self.model.vFlags)
        if not vertexClassName in m3.structMap:
            raise Exception("Vertex flags %s can't behandled yet" % hex(self.model.vFlags))
        vertexClass = m3.structMap[vertexClassName]

        numberOfVertices = len(self.model.vertices) // vertexClass.size
        m3Vertices = vertexClass.createInstances(rawBytes=self.model.vertices, count=numberOfVertices)

        for division in self.model.divisions:
            divisionFaceIndices = division.faces
            for m3Object in division.objects:
                region = division.regions[m3Object.regionIndex]
                bpy.ops.object.mode_set(mode='OBJECT')
                regionVertexIndices = range(region.firstVertexIndex,region.firstVertexIndex + region.numberOfVertices)
                firstVertexIndexIndex = region.firstFaceVertexIndexIndex
                lastVertexIndexIndex = firstVertexIndexIndex + region.numberOfFaceVertexIndices
                vertexIndexIndex = firstVertexIndexIndex
                firstVertexIndex = region.firstVertexIndex
                assert region.numberOfFaceVertexIndices % 3 == 0

                facesWithOldIndices = [] # old index = index of vertex in m3Vertices
                while vertexIndexIndex + 2 <= lastVertexIndexIndex:
                    i0 = firstVertexIndex + divisionFaceIndices[vertexIndexIndex]
                    i1 = firstVertexIndex + divisionFaceIndices[vertexIndexIndex + 1]
                    i2 = firstVertexIndex + divisionFaceIndices[vertexIndexIndex + 2]
                    face = (i0, i1, i2)
                    facesWithOldIndices.append(face)
                    vertexIndexIndex += 3

                mesh = bpy.data.meshes.new('Mesh')
                meshObject = bpy.data.objects.new('MeshObject', mesh)
                meshObject.location = (0,0,0)
                meshObject.show_name = True
                bpy.context.scene.objects.link(meshObject)
                
                mesh.m3_material_name = self.getNameOfMaterialWithReferenceIndex(m3Object.materialReferenceIndex)
                
                
                # merge vertices together which have always the same position and normal:
                # This way there are not only fewer vertices to edit,
                # but also the calculated normals will more likly match
                # the given ones.
                vertexPositions = []
                nextNewVertexIndex = 0
                oldVertexIndexToNewVertexIndexMap = {}
                newVertexIndexToOldVertexIndexMap = {}
                vertexIdTupleToNewIndexMap = {}
                
                for vertexIndex in regionVertexIndices:
                    m3Vertex = m3Vertices[vertexIndex]
                    v = m3Vertex
                    idTuple = (v.position.x, v.position.y, v.position.z, v.boneWeight0, v.boneWeight1, v.boneWeight2, v.boneWeight3, v.boneLookupIndex0, v.boneLookupIndex1, v.boneLookupIndex2, v.boneLookupIndex3, v.normal.x, v.normal.y, v.normal.z)
                    newIndex = vertexIdTupleToNewIndexMap.get(idTuple)
                    if newIndex == None:
                        newIndex = nextNewVertexIndex
                        nextNewVertexIndex += 1
                        position = (m3Vertex.position.x, m3Vertex.position.y, m3Vertex.position.z)
                        vertexPositions.append(position)
                        vertexIdTupleToNewIndexMap[idTuple] = newIndex
                    oldVertexIndexToNewVertexIndexMap[vertexIndex] = newIndex
                    newVertexIndexToOldVertexIndexMap[newIndex] = vertexIndex
                
                # since vertices got merged, the indices of the faces aren't correct anymore.
                # the old face indices however are still later required to figure out
                # what Uv coordinates a face has.
                facesWithNewIndices = []
                for faceWithOldIndices in facesWithOldIndices:
                    i0 = oldVertexIndexToNewVertexIndexMap[faceWithOldIndices[0]]
                    i1 = oldVertexIndexToNewVertexIndexMap[faceWithOldIndices[1]]
                    i2 = oldVertexIndexToNewVertexIndexMap[faceWithOldIndices[2]]
                    faceWithNewIndices = (i0, i1, i2)
                    facesWithNewIndices.append(faceWithNewIndices)
                
                mesh.vertices.add(len(vertexPositions))
                mesh.vertices.foreach_set("co", io_utils.unpack_list(vertexPositions))

                mesh.tessfaces.add(len(facesWithNewIndices))
                mesh.tessfaces.foreach_set("vertices_raw", io_utils.unpack_face_list(facesWithNewIndices))
                
                def getUVsFor(newVertexIndex, vertexUVAttribute):
                    oldVertexIndex = newVertexIndexToOldVertexIndexMap[newVertexIndex]
                    return toBlenderUVCoordinate(getattr(m3Vertices[oldVertexIndex],vertexUVAttribute))
                
                for vertexUVAttribute in ["uv0", "uv1", "uv2", "uv3"]:
                    if vertexUVAttribute in vertexClass.fieldToTypeInfoMap: 
                        uvLayer = mesh.tessface_uv_textures.new()
                        for faceIndex in range(len(facesWithNewIndices)):
                            tessFace = mesh.tessfaces[faceIndex]
                            faceUV = uvLayer.data[faceIndex]
                            # It's necessary to take vertex indices from tessface
                            # Since the vertex indices may get reordered within a triangle
                            faceUV.uv1 = getUVsFor(tessFace.vertices[0], vertexUVAttribute)
                            faceUV.uv2 = getUVsFor(tessFace.vertices[1], vertexUVAttribute)
                            faceUV.uv3 = getUVsFor(tessFace.vertices[2], vertexUVAttribute)


                mesh.update(calc_edges=True)
                
                boneIndexLookup = model.boneLookup[region.firstBoneLookupIndex:region.firstBoneLookupIndex + region.numberOfBoneLookupIndices]
                vertexGroupLookup = []
                for boneIndex in boneIndexLookup:
                    boneName = shared.toValidBoneName(self.boneNames[boneIndex])
                    if boneName in meshObject.vertex_groups:
                        vertexGroup = meshObject.vertex_groups[boneName]
                    else:
                        vertexGroup =  meshObject.vertex_groups.new(boneName)
                    vertexGroupLookup.append(vertexGroup)
                for vertexIndex in range(region.firstVertexIndex,region.firstVertexIndex + region.numberOfVertices):
                    m3Vertex = m3Vertices[vertexIndex]
                    boneWeightsAsInt = [m3Vertex.boneWeight0, m3Vertex.boneWeight1, m3Vertex.boneWeight2, m3Vertex.boneWeight3]
                    boneLookupIndices = [m3Vertex.boneLookupIndex0, m3Vertex.boneLookupIndex1,  m3Vertex.boneLookupIndex2,  m3Vertex.boneLookupIndex3]
                    boneWeights = []
                    for boneWeightAsInt, boneLookupIndex in zip(boneWeightsAsInt, boneLookupIndices):
                        if boneWeightAsInt != 0:
                            vertexGroup = vertexGroupLookup[boneLookupIndex]
                            boneWeight = boneWeightAsInt / 255.0
                            vertexGroup.add([oldVertexIndexToNewVertexIndexMap[vertexIndex]], boneWeight, 'REPLACE')

                modifier = meshObject.modifiers.new('UseArmature', 'ARMATURE')
                modifier.object = self.armatureObject
                modifier.use_bone_envelopes = False
                modifier.use_vertex_groups = True
        
    def determineRelEditBoneMatrices(self, m3Bones, editBones):
        absEditBoneMatrices = []
        relEditBoneMatrices = []
        for boneEntry, editBone in zip(m3Bones, editBones):
            absEditBoneMatrix = editBone.matrix
            absEditBoneMatrices.append(absEditBoneMatrix)
            if boneEntry.parent != -1:
                parentEditBone = editBones[boneEntry.parent]
                absParentEditBoneMatrix = parentEditBone.matrix
                relEditBoneMatrix = absParentEditBoneMatrix.inverted() * absEditBoneMatrix 
            else:
                relEditBoneMatrix = absEditBoneMatrix
            relEditBoneMatrices.append(relEditBoneMatrix)
        return relEditBoneMatrices


    def containsToLongNames(nameList):
        for name in nameList:
            if len(name) > 31:
                return True
        return false

    def determineBoneNameList(self, m3Bones):
        names = []
        nameSet = set()
        for index, m3Bone in enumerate(m3Bones):
            name = m3Bone.name
            if len(name) > 31:
                name = "Bone%06d%s" % (index, name[:21])
            if len(name) == 0:
                name = "Bone%06d" % len(names)
            if name in nameSet:
                raise Exception("Failed to generate an unique bone name for %s" % name)
            nameSet.add(name)
            names.append(name)
        return names

    def createEditBones(self, m3Bones, heads, tails, rolls, absoluteScales):
        self.boneNames = self.determineBoneNameList(m3Bones)
        editBones = []
        for index, boneEntry in enumerate(m3Bones):
            editBone = self.armature.edit_bones.new(self.boneNames[index])
            if boneEntry.parent != -1:
                parentEditBone = editBones[boneEntry.parent]
                editBone.parent = parentEditBone
            editBone.head = heads[index]
            editBone.tail = tails[index]
            editBone.roll = rolls[index]
            editBone.m3_unapplied_scale = absoluteScales[index]
            editBones.append(editBone)
        return editBones

    def createAnimIdToKeyFramesMapFor(self, stc):
        keyFramesLists = [stc.sdev, stc.sd2v, stc.sd3v, stc.sd4q, stc.sdcc, stc.sdr3, stc.unknownRef8, stc.sds6, stc.sdu6, stc.unknownRef11, stc.unknownRef12, stc.sdfg, stc.sdmb]
        animIdToTimeValueMap = {}
        for i in range(len(stc.animIds)):
            animId = stc.animIds[i]
            animRef = stc.animRefs[i]
            animType = animRef >> 16
            animIndex = animRef & 0xffff
            keyFramesList = keyFramesLists[animType]
            keyFramesEntry = keyFramesList[animIndex]
            
            timeEntries = keyFramesEntry.frames
            valueEntries = keyFramesEntry.keys
            timeValueMap = {}
            for timeEntry, valueEntry in zip(timeEntries, valueEntries):
                timeValueMap[timeEntry] = valueEntry
            
            animIdToTimeValueMap[animId] = timeValueMap
        return animIdToTimeValueMap
        
    def createOrGetDefaultAction(self, ownerType):
        action = self.ownerTypeToDefaultValuesActionMap.get(ownerType)
        if action == None:
            scene = bpy.context.scene
            ownerName = self.actionTargetNameForOwnerType(ownerType)
            actionIdRoot = self.actionIdRootFromOwnerType(ownerType)
            action = shared.createDefaulValuesAction(scene, ownerName, actionIdRoot)
            self.ownerTypeToDefaultValuesActionMap[ownerType] = action
        return action
        
    def createOrGetActionFor(self, animationData, ownerType):
        ownerTypesToActionMap = animationData.ownerTypeToActionMap
        scene = bpy.context.scene
        animation = scene.m3_animations[animationData.animationIndex]
        action = ownerTypesToActionMap.get(ownerType)
        if action == None:
            action = bpy.data.actions.new(animation.name + ownerType)
            action.id_root = self.actionIdRootFromOwnerType(ownerType)
            ownerTypesToActionMap[ownerType] = action
            actionAssignment = animation.assignedActions.add()
            actionAssignment.actionName = action.name
            actionAssignment.targetName = self.actionTargetNameForOwnerType(ownerType)
        return action
        
        
    def actionIdRootFromOwnerType(self,ownerType):
        if ownerType == ownerTypeArmature:
            return "OBJECT"
        elif ownerType == ownerTypeScene:
            return "SCENE"
        else:
            raise Exception("Unhandled case")

    def actionTargetNameForOwnerType(self, ownerType):
        if ownerType == ownerTypeArmature:
            return self.armatureObject.name
        elif ownerType == ownerTypeScene:
            return bpy.context.scene.name
        else:
            raise Exception("Unhandled case")
    
    def findSimulateFrame(self, animIdToTimeValueMap):
        # Hack:
        # So far only seen models where Evt_Simulate and Evt_End are in the same animId element.
        # Check through all stc.sdev entries directly instead?
        timeValueMap = animIdToTimeValueMap[0x65bd3215]
        
        for frame, key, in frameValuePairs(timeValueMap):
            if key.name == "Evt_Simulate":
                return True, frame
        
        return False, 0
    
    def createAnimations(self):
        print ("Creating actions(animation sequences)")
        scene = bpy.context.scene
        ownerTypeToIdleActionMap = {}
        model = self.model
        numberOfSequences = len(model.sequences)
        if len(model.sequenceTransformationGroups) != numberOfSequences:
            raise Exception("The model has not the same amounth of stg elements as it has sequences")


        self.sequenceNameAndSTCIndexToAnimIdSet = {}
        for sequenceIndex in range(numberOfSequences):
            sequence = model.sequences[sequenceIndex]
            stg = model.sequenceTransformationGroups[sequenceIndex]
            if (sequence.name != stg.name):
                raise Exception("Name of sequence and it's transformation group does not match")
            animation = scene.m3_animations.add()
            animation.startFrame = msToFrame(sequence.animStartInMS)
            animation.exlusiveEndFrame = msToFrame(sequence.animEndInMS)
            transferer = M3ToBlenderDataTransferer(self, None, blenderObject=animation, m3Object=sequence)
            shared.transferAnimation(transferer)
            
            animIdToTimeValueMap = {}
            ownerTypeToActionMap = {}
            for m3STCIndex in stg.stcIndices:
                stc = model.sequenceTransformationCollections[m3STCIndex]
                animationSTCIndex = transformationCollection = len(animation.transformationCollections)
                transformationCollection = animation.transformationCollections.add()
                transformationCollectionName = stc.name
                stcPrefix = sequence.name + "_"
                if transformationCollectionName.startswith(stcPrefix):
                    transformationCollectionName = transformationCollectionName[len(stcPrefix):]
                
                transformationCollection.name = transformationCollectionName
                
                transferer = M3ToBlenderDataTransferer(self, None, blenderObject=transformationCollection, m3Object=stc)
                shared.transferSTC(transferer)
                animIdsOfSTC = set()     
                animIdToTimeValueMapForSTC = self.createAnimIdToKeyFramesMapFor(stc)
                for animId, timeValueMap in animIdToTimeValueMapForSTC.items():
                    if animId in animIdToTimeValueMap:
                        raise Exception("Same animid %s got animated by different STC" % animId)
                    animIdToTimeValueMap[animId] = timeValueMap
                    animIdsOfSTC.add(animId)
                
                self.sequenceNameAndSTCIndexToAnimIdSet[sequence.name, animationSTCIndex] = animIdsOfSTC
                
                # stc.seqIndex seems to be wrong:
                #sequence = model.sequences[stc.seqIndex]
                if len(stc.animIds) != len(stc.animRefs):
                    raise Exception("len(stc.animids) != len(stc.animrefs)")
            
            animation.useSimulateFrame, animation.simulateFrame = self.findSimulateFrame(animIdToTimeValueMap)
            
            self.animations.append(AnimationData(animIdToTimeValueMap, ownerTypeToActionMap, sequenceIndex))


    def initSTCsOfAnimations(self):
        unsupportedAnimIds = set()
        for sequenceNameAndSTCIndex, animIds in self.sequenceNameAndSTCIndexToAnimIdSet.items():
            sequenceName, stcIndex = sequenceNameAndSTCIndex
            stc = self.scene.m3_animations[sequenceName].transformationCollections[stcIndex]
            for animId in animIds:
                longAnimId = self.animIdToLongAnimIdMap.get(animId)
                if longAnimId != None:
                    animatedProperty = stc.animatedProperties.add()
                    animatedProperty.longAnimId = longAnimId
                else:
                    unsupportedAnimIds.add(animId)
        animationEndEventAnimId = 0x65bd3215
        if animationEndEventAnimId in unsupportedAnimIds:
            unsupportedAnimIds.remove(animationEndEventAnimId)
        else:
            print("Warning: Model contained no animation with animId %d which are usually used for marking the end of an animation" % animationEndEventAnimId )

        if len(unsupportedAnimIds) > 0:
            animIdToPathMap = {}
            self.addAnimIdPathToMap("model", self.model, animIdToPathMap)
            for unsupportedAnimId in unsupportedAnimIds:
                path = animIdToPathMap.get(unsupportedAnimId, "<unknown path>")
                print("Warning: Ignoring unsupported animated property with animId %s and path %s" %(hex(unsupportedAnimId), path))
                
    def addAnimIdPathToMap(self, path, m3Object, animIdToPathMap):
        if hasattr(m3Object, "header") and type(m3Object.header) == m3.AnimationReferenceHeader: 
            header = m3Object.header
            if header.animFlags == shared.animFlagsForAnimatedProperty:
                animIdToPathMap[header.animId] = path
        if hasattr(type(m3Object),"fields"):
            for fieldName in m3Object.fields:
                fieldValue = getattr(m3Object,fieldName)
                if fieldValue == None:
                    pass
                elif fieldValue.__class__ == list:
                    for entryIndex, entry in enumerate(fieldValue):
                        entryPath = "%s.%s[%d]" % (path, fieldName, entryIndex )
                        self.addAnimIdPathToMap(entryPath, entry, animIdToPathMap)
                else:
                    fieldPath = path + "." + fieldName
                    self.addAnimIdPathToMap(fieldPath, fieldValue, animIdToPathMap)

    def actionAndTimeValueMapPairsFor(self, ownerType, animId):
        for animationData in self.animations:
            timeValueMap = animationData.animIdToTimeValueMap.get(animId)
            if timeValueMap != None:
                action = self.createOrGetActionFor(animationData, ownerType)
                yield (action, timeValueMap)
        

    def animateFloat(self, ownerType, path, animId, defaultValue):
        #TODO let animateFloat take objectId as argument
        defaultAction = self.createOrGetDefaultAction(ownerType)
        curve = defaultAction.fcurves.new(path, 0)
        insertConstantKeyFrame(curve, 0, defaultValue)
        
        self.addAnimIdData(animId, objectId=shared.animObjectIdScene, animPath=path)
        for action, timeValueMap in self.actionAndTimeValueMapPairsFor(ownerType, animId):
            curve = action.fcurves.new(path, 0)
            for frame, value in frameValuePairs(timeValueMap):
                insertLinearKeyFrame(curve, frame, value)
    
    def animateInteger(self, ownerType, path, animId, defaultValue):
        defaultAction = self.createOrGetDefaultAction(ownerType)
        curve = defaultAction.fcurves.new(path, 0)
        insertConstantKeyFrame(curve, 0, defaultValue)
        
        self.addAnimIdData(animId, objectId=shared.animObjectIdScene, animPath=path)
        for action, timeValueMap in self.actionAndTimeValueMapPairsFor(ownerType, animId):
            curve = action.fcurves.new(path, 0)
            for frame, value in frameValuePairs(timeValueMap):
                insertConstantKeyFrame(curve, frame, value)

    def animateVector3(self, ownerType, path, animId, defaultValue):
        defaultAction = self.createOrGetDefaultAction(ownerType)
        xCurve = defaultAction.fcurves.new(path, 0)
        yCurve = defaultAction.fcurves.new(path, 1)
        zCurve = defaultAction.fcurves.new(path, 2)
        insertConstantKeyFrame(xCurve, 0, defaultValue.x) 
        insertConstantKeyFrame(yCurve, 0, defaultValue.y) 
        insertConstantKeyFrame(zCurve, 0, defaultValue.z) 
        
        self.addAnimIdData(animId, objectId=shared.animObjectIdScene, animPath=path)
        for action, timeValueMap in self.actionAndTimeValueMapPairsFor(ownerType, animId):
            xCurve = action.fcurves.new(path, 0)
            yCurve = action.fcurves.new(path, 1)
            zCurve = action.fcurves.new(path, 2)
            
            for frame, value in frameValuePairs(timeValueMap):
                insertLinearKeyFrame(xCurve, frame, value.x)
                insertLinearKeyFrame(yCurve, frame, value.y)
                insertLinearKeyFrame(zCurve, frame, value.z)




    def animateVector2(self, ownerType, path, animId, defaultValue):
        defaultAction = self.createOrGetDefaultAction(ownerType)
        xCurve = defaultAction.fcurves.new(path, 0)
        yCurve = defaultAction.fcurves.new(path, 1)
        insertConstantKeyFrame(xCurve, 0, defaultValue.x) 
        insertConstantKeyFrame(yCurve, 0, defaultValue.y) 
        
        self.addAnimIdData(animId, objectId=shared.animObjectIdScene, animPath=path)
        for action, timeValueMap in self.actionAndTimeValueMapPairsFor(ownerType, animId):
            xCurve = action.fcurves.new(path, 0)
            yCurve = action.fcurves.new(path, 1)
            
            for frame, value in frameValuePairs(timeValueMap):
                insertLinearKeyFrame(xCurve, frame, value.x)
                insertLinearKeyFrame(yCurve, frame, value.y)

    def animateColor(self, ownerType, path, animId, m3DefaultValue):
        defaultAction = self.createOrGetDefaultAction(ownerType)
        defaultValue = toBlenderColorVector(m3DefaultValue)
        for i in range(4):
            curve = defaultAction.fcurves.new(path, i)
            insertConstantKeyFrame(curve, 0, defaultValue[i])
        
        self.addAnimIdData(animId, objectId=shared.animObjectIdScene, animPath=path)
        for action, timeValueMap in self.actionAndTimeValueMapPairsFor(ownerType, animId):
            redCurve = action.fcurves.new(path, 0)
            greenCurve = action.fcurves.new(path, 1)
            blueCurve = action.fcurves.new(path, 2)
            alphaCurve = action.fcurves.new(path, 3)

            for frame, value in frameValuePairs(timeValueMap):
                v = toBlenderColorVector(value)
                insertLinearKeyFrame(redCurve, frame, v[0])
                insertLinearKeyFrame(greenCurve, frame, v[1])
                insertLinearKeyFrame(blueCurve, frame, v[2])
                insertLinearKeyFrame(alphaCurve, frame, v[3])
                
    def animateBoundings(self, ownerType, animPathMinBorder, animPathMaxBorder, animPathRadius, animId, minBorderDefault, maxBorderDefault, radiusDefault):
        #Store default values in an action:
        defaultAction = self.createOrGetDefaultAction(ownerType)
        for i in range(3):
            curve = defaultAction.fcurves.new(animPathMinBorder, i)
            insertConstantKeyFrame(curve, 0, minBorderDefault[i])
        for i in range(3):
            curve = defaultAction.fcurves.new(animPathMaxBorder, i)
            insertConstantKeyFrame(curve, 0, maxBorderDefault[i])
        curve = defaultAction.fcurves.new(animPathRadius, 0)
        insertConstantKeyFrame(curve, 0, radiusDefault)

        #Which path we pass to addAnimIdData does not matter,
        # since they all would result in the same longAnimId (see getLongAnimIdOf):
        self.addAnimIdData(animId, objectId=shared.animObjectIdScene, animPath=animPathMinBorder)
        for action, timeValueMap in self.actionAndTimeValueMapPairsFor(ownerType, animId):
            minXCurve = action.fcurves.new(animPathMinBorder, 0)
            minYCurve = action.fcurves.new(animPathMinBorder, 1)
            minZCurve = action.fcurves.new(animPathMinBorder, 2)
            maxXCurve = action.fcurves.new(animPathMaxBorder, 0)
            maxYCurve = action.fcurves.new(animPathMaxBorder, 1)
            maxZCurve = action.fcurves.new(animPathMaxBorder, 2)
            radiusCurve = action.fcurves.new(animPathRadius, 0)
            
            for frame, value in frameValuePairs(timeValueMap):
                insertLinearKeyFrame(minXCurve, frame, value.minBorder.x)
                insertLinearKeyFrame(minYCurve, frame, value.minBorder.y)
                insertLinearKeyFrame(minZCurve, frame, value.minBorder.z)
                insertLinearKeyFrame(maxXCurve, frame, value.maxBorder.x)
                insertLinearKeyFrame(maxYCurve, frame, value.maxBorder.y)
                insertLinearKeyFrame(maxZCurve, frame, value.maxBorder.z)
                insertLinearKeyFrame(radiusCurve, frame, value.radius)
                
   
def boneRotMatrix(head, tail, roll):
    """unused: python port of the Blender C Function vec_roll_to_mat3 """
    v = tail - head
    v.normalize()
    target = mathutils.Vector((0,1,0))
    axis = target.cross(v)
    if axis.dot(axis) > 0.000001:
        axis.normalize()
        theta = target.angle(v)
        bMatrix = mathutils.Matrix.Rotation(theta, 3, axis)
    else:
        if target.dot(v) > 0:
            updown = 1.0
        else:
            updown = -1.0
        
        bMatrix = mathutils.Matrix((
            (updown, 0, 0),
            (0, updown, 0), 
            (0, 0, 1)))
    
    rMatrix = mathutils.Matrix.Rotation(roll, 3, v)
    return rMatrix *bMatrix

def boneMatrix(head, tail, roll):
    """unused: how blender calculates the matrix of a bone """
    rotMatrix = boneRotMatrix(head, tail, roll)
    matrix = rotMatrix.to_4x4()
    matrix.translation = head
    return matrix

def importFile(filename):
    importer = Importer()
    importer.importFile(filename)
