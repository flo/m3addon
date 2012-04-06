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

def toBlenderQuaternion(m3Quaternion):
    return mathutils.Quaternion((m3Quaternion.w, m3Quaternion.x, m3Quaternion.y, m3Quaternion.z))

def toBlenderVector3(m3Vector3):
    return mathutils.Vector((m3Vector3.x, m3Vector3.y, m3Vector3.z))

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
                timeToVectorMap[wantedTime] = interpolationFunc(leftFactor, leftInterpolationValue, rightFactor, rightInterpolationValue)
            wantedTimesIndex += 1
            if wantedTimesIndex == len(wantedTimes):
                return
            wantedTime = wantedTimes[wantedTimesIndex]
        leftInterpolationTime = rightInterpolationTime
        leftInterpolationValue = rightInterpolationValue

    for wantedTime in wantedTimes[wantedTimesIndex:]:
        timeToVectorMap[wantedTime] = leftInterpolationValue

def vectorInterpolationFunction(leftFactor, leftInterpolationValue, rightFactor, rightInterpolationValue):
    return leftInterpolationValue.lerp(rightInterpolationValue, rightFactor)

def quaternionInterpolationFunction(leftFactor, leftInterpolationValue, rightFactor, rightInterpolationValue):
    return leftInterpolationValue.slerp(rightInterpolationValue, rightFactor)

def extendTimeToVectorMapByInterpolation(timeToVectorMap, wantedTimes):
    return extendTimeToValueMapByInterpolation(timeToVectorMap, wantedTimes, vectorInterpolationFunction)

def extendTimeToQuaternionMapByInterpolation(timeToVectorMap, wantedTimes):
    return extendTimeToValueMapByInterpolation(timeToVectorMap, wantedTimes, quaternionInterpolationFunction)

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

def determineHeads(absolutBoneMatrices):
    heads = []
    for matrix in absolutBoneMatrices:
        head = matrix.translation
        heads.append(head)
    return heads

def determineTails(boneEntries, heads):
    possibleTailsLists = []
    index = 0
    for boneEntry in boneEntries:
        possibleTailsLists.append([])
        if boneEntry.parent != -1:
            possibleTailsOfParent = possibleTailsLists[boneEntry.parent]
            possibleTailsOfParent.append(heads[index])
        index += 1
    tails = []
    index = 0
    for possibleTailList in possibleTailsLists:
        if len(possibleTailList) >= 1 and possibleTailList[0].length > 0.05:
            tail = possibleTailList[0]
        else:
            tail = heads[index] + mathutils.Vector((0,0.1,0))
        tails.append(tail)
        index += 1
    return tails


def determineAbsoluteBoneRestPositions(model):
    matrices = []
    for inverseBoneRestPosition in model.absoluteInverseBoneRestPositions:
        matrices.append(toBlenderMatrix(inverseBoneRestPosition.matrix).inverted())
    return matrices

def toValidBoneName(name):
    maxLength = 31
    return name[:maxLength]    

ownerTypeScene = "Scene"
ownerTypeArmature = "Armature"


def visitFieldPropertyPairs(blenderObject, m3Object, fieldVisitor):
    blenderClass = blenderObject.__class__
    m3Class = m3Object.__class__
    for fieldName in m3Class.fields:
        if hasattr(blenderClass, fieldName):
            propertyTypeAndArgs = getattr(blenderClass, fieldName)
            if (type(propertyTypeAndArgs) == tuple) and (len(propertyTypeAndArgs) == 2):
                propertyType = propertyTypeAndArgs[0]
                propertyArgs = propertyTypeAndArgs[1]
                fieldTypeInfo = m3Class.getFieldTypeInfo(fieldName)
                fieldTypeName = fieldTypeInfo.typeName
                fieldIsList =  fieldTypeInfo.isList
                
                if fieldTypeName == "FloatAnimationReference":
                    if not (propertyType == bpy.props.FloatProperty and "ANIMATABLE" in propertyArgs["options"]):
                        raise Exception("The property %(fieldName)s of %(blenderClass)s should be an animatable float" % {"fieldName":fieldName, "blenderClass":blenderClass })
                    fieldVisitor.visitAnimatableFloat(blenderObject, m3Object, fieldName)
                elif fieldTypeName == "float":
                    if not (propertyType == bpy.props.FloatProperty and (not ("ANIMATABLE" in propertyArgs["options"]))):
                        raise Exception("The property %(fieldName)s of %(blenderClass)s should be an float which isn't animatable" % {"fieldName":fieldName, "blenderClass":blenderClass })
                    fieldVisitor.visitFloat(blenderObject, m3Object, fieldName)
                elif fieldTypeName == "uint32":
                    if (propertyType == bpy.props.BoolProperty):
                        fieldVisitor.visitBoolean(blenderObject, m3Object, fieldName)
                    elif propertyType == bpy.props.IntProperty:
                        fieldVisitor.visitInt(blenderObject, m3Object, fieldName)
                elif fieldTypeName == "int32":
                    if propertyType == bpy.props.IntProperty:
                        fieldVisitor.visitInt(blenderObject, m3Object, fieldName)
                elif fieldTypeName == "Vector3AnimationReference":
                    if not (propertyType == bpy.props.FloatVectorProperty and (propertyArgs["size"] == 3) and ("ANIMATABLE" in propertyArgs["options"])):
                        raise Exception("The property %(fieldName)s of %(blenderClass)s should be an animated float vector of size 3" % {"fieldName":fieldName, "blenderClass":blenderClass })
                    fieldVisitor.visitAnimatableVector3(blenderObject, m3Object, fieldName)
                elif fieldTypeName == "ColorAnimationReference":
                    if not (propertyType == bpy.props.FloatVectorProperty and (propertyArgs["size"] == 4) and ("ANIMATABLE" in propertyArgs["options"])):
                        raise Exception("The property %(fieldName)s of %(blenderClass)s should be an animated float vector of size 4" % {"fieldName":fieldName, "blenderClass":blenderClass })
                    fieldVisitor.visitAnimatableColor(blenderObject, m3Object, fieldName)
                elif fieldTypeName == "Int16AnimationReference":
                    if not (propertyType == bpy.props.IntProperty and "ANIMATABLE" in propertyArgs["options"]):
                        raise Exception("The property %(fieldName)s of %(blenderClass)s should be an animatable integer" % {"fieldName":fieldName, "blenderClass":blenderClass })
                    fieldVisitor.visitAnimatableInteger(blenderObject, m3Object, fieldName)
                elif fieldTypeName == "CHARV0":
                    if not (propertyType == bpy.props.StringProperty and not "ANIMATABLE" in propertyArgs["options"]):
                        raise Exception("The property %(fieldName)s of %(blenderClass)s should be a non animatable string" % {"fieldName":fieldName, "blenderClass":blenderClass })
                    fieldVisitor.visitString(blenderObject, m3Object, fieldName)
                
                

def scaleAndRotationOf(matrix4x4):
    scale = mathutils.Vector((1,1,1))
    matrix3x3 = matrix4x4.to_3x3()
    scale.x = matrix3x3.col[0].length
    scale.y = matrix3x3.col[1].length
    scale.z = matrix3x3.col[2].length
    matrix3x3.col[0] = matrix3x3.col[0] / scale.x
    matrix3x3.col[1] = matrix3x3.col[1] / scale.y
    matrix3x3.col[2] = matrix3x3.col[2] / scale.z
    #TODO handle negative scales
    rotation = matrix3x3.to_quaternion()
    return (scale, rotation)

class BlenderPropertiesSettingFieldVisitor:
    def __init__(self, importer, animPathPrefix):
        self.importer = importer
        self.animPathPrefix = animPathPrefix
    
    def visitAnimatableFloat(self, blenderObject, m3Object, fieldName):
        animationReference = getattr(m3Object, fieldName)
        setattr(blenderObject, fieldName, animationReference.initValue)
        animationHeader = animationReference.header
        animId = animationHeader.animId
        animPath = self.animPathPrefix +  fieldName
        self.importer.animateFloat(ownerTypeScene, animPath, animId)
        
    def visitAnimatableInteger(self, blenderObject, m3Object, fieldName):
        animationReference = getattr(m3Object, fieldName)
        setattr(blenderObject, fieldName, animationReference.initValue)
        animationHeader = animationReference.header
        animId = animationHeader.animId
        animPath = self.animPathPrefix + fieldName
        self.importer.animateInteger(ownerTypeScene, animPath, animId)
        
    def visitFloat(self, blenderObject, m3Object, fieldName):
        setattr(blenderObject, fieldName, getattr(m3Object, fieldName))
        
    def visitInt(self, blenderObject, m3Object, fieldName):
        setattr(blenderObject, fieldName, getattr(m3Object, fieldName))
        
    def visitString(self, blenderObject, m3Object, fieldName):
        value = getattr(m3Object, fieldName)
        if value == None:
            value = ""
        setattr(blenderObject, fieldName, value)

    def visitBoolean(self, blenderObject, m3Object, fieldName):
        integerValue = getattr(m3Object, fieldName)
        if integerValue == 0:
            setattr(blenderObject, fieldName, False)
        elif integerValue == 1:
            setattr(blenderObject, fieldName, True)
        else:
            print("WARNING: %s was neither 0 nor 1" % fieldName)
    
    def visitAnimatableVector3(self, blenderObject, m3Object, fieldName):
        animationReference = getattr(m3Object, fieldName)
        setattr(blenderObject, fieldName, toBlenderVector3(animationReference.initValue))
        animationHeader = animationReference.header
        animId = animationHeader.animId
        animPath = self.animPathPrefix + fieldName
        self.importer.animateVector3(ownerTypeScene, animPath, animId)

        
    def visitAnimatableColor(self, blenderObject, m3Object, fieldName):
        animationReference = getattr(m3Object, fieldName)
        setattr(blenderObject, fieldName, toBlenderColorVector(animationReference.initValue))
        animationHeader = animationReference.header
        animId = animationHeader.animId
        animPath = self.animPathPrefix + fieldName
        self.importer.animateColor(ownerTypeScene, animPath, animId)

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
        self.model = m3.loadModel(filename)
        self.armature = bpy.data.armatures.new(name="Armature")
        scene.render.fps = FRAME_RATE
        self.animations = []
        self.createAnimations()
        self.createArmatureObject()
        self.createBones()
        self.createMaterials()
        self.createParticleSystems()
        #self.createAttachmentPoints()
        self.createMesh()

        if len(scene.m3_animations) >= 1:
            scene.m3_animation_old_index = -1
            scene.m3_animation_index = 0
            

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
        rotFixMatrix = mathutils.Matrix((( 0, 1, 0, 0,),
                                         (-1, 0, 0, 0),
                                         ( 0, 0, 1, 0),
                                         ( 0, 0, 0, 1)))

        absoluteBoneRestPositions = determineAbsoluteBoneRestPositions(model)
        
        bpy.ops.object.mode_set(mode='EDIT')
        checkOrder(model.bones)
        #TODO Make better use of bone rest positions
        #(currently only the location gets used but not the rotation)
        heads = []
        boneDirectionVectors = []
        rolls = []
        for absBoneRestMatrix in absoluteBoneRestPositions:
            head = absBoneRestMatrix.translation
            heads.append(head)
            wantedAbsBoneRestMatrix = absBoneRestMatrix * rotFixMatrix
            # In blender the edit bone with the vector (0,1,0) stands for a idenity matrix
            # So the second column of a edit bone matrix represents the bone vector
            boneDirectionVector = wantedAbsBoneRestMatrix.col[1].to_3d()
            boneDirectionVector.normalize()
            boneDirectionVectors.append(boneDirectionVector)

            simpleTail = head + boneDirectionVector
            editBoneMatrix = boneMatrix(head=head, tail=simpleTail, roll=0)
            boneMatrix3x3 = editBoneMatrix.to_3x3()
            
            angleZToZ = boneMatrix3x3.col[2].angle(wantedAbsBoneRestMatrix.col[2].to_3d())
            angleZToX = boneMatrix3x3.col[0].angle(wantedAbsBoneRestMatrix.col[0].to_3d())

            if angleZToZ < 90:
                if angleZToX < 90:
                    rollAngle = angleZToZ
                else:
                    rollAngle = -angleZToZ
            else:
                if angleZToX > 90:
                    rollAngle = angleZToZ
                else:
                    rollAngle = -angleZToZ

            rolls.append(rollAngle)
        
        childBoneIndexLists = []
        for boneIndex, boneEntry in enumerate(model.bones):
            childBoneIndexLists.append([])
            if boneEntry.parent != -1:
                childBoneIndexLists[boneEntry.parent].append(boneIndex)
        
        tails = []
        for head, childIndices, boneDirectionVector in zip(heads, childBoneIndexLists, boneDirectionVectors):
            length = 0.1
            for childIndex in childIndices:
                headToChildHead = heads[childIndex] - head
                if abs(headToChildHead.angle(boneDirectionVector)) < 0.1:
                   length = headToChildHead.length 
            
            tail = head + length * boneDirectionVector
            tails.append(tail)

        editBones = []
        absEditBoneMatrices = []
        relEditBoneMatrices = []
        index = 0
        for boneEntry in model.bones:
            editBone = self.armature.edit_bones.new(toValidBoneName(boneEntry.name))
            if boneEntry.parent != -1:
                parentEditBone = editBones[boneEntry.parent]
                editBone.parent = parentEditBone
            editBone.head = heads[index]
            editBone.tail = tails[index]
            editBone.roll = rolls[index]
            editBones.append(editBone)
            
            absEditBoneMatrix = editBone.matrix
            absEditBoneMatrices.append(absEditBoneMatrix)
            if boneEntry.parent != -1:
                parentEditBone = editBones[boneEntry.parent]
                absParentEditBoneMatrix = parentEditBone.matrix
                relEditBoneMatrix = absParentEditBoneMatrix.inverted() * absEditBoneMatrix 
            else:
                relEditBoneMatrix = absEditBoneMatrix
            relEditBoneMatrices.append(relEditBoneMatrix)
            index +=1

        bpy.ops.object.mode_set(mode='POSE')
        print("Loading initial bone positions")
        index = 0
        rotFixMatrixInverted = rotFixMatrix.transposed()
        for bone in model.bones:
            poseBone = self.armatureObject.pose.bones[toValidBoneName(bone.name)]
            scale = toBlenderVector3(bone.scale.initValue)
            rotation = toBlenderQuaternion(bone.rotation.initValue)
            location = toBlenderVector3(bone.location.initValue)
            
            if bone.parent != -1:
                leftCorrectionMatrix = relEditBoneMatrices[index].inverted() * rotFixMatrixInverted
                rightCorrectionMatrix = rotFixMatrix
            else:
                leftCorrectionMatrix = relEditBoneMatrices[index].inverted()
                rightCorrectionMatrix = rotFixMatrix
            
            leftScaleCorrection, leftRotCorrection = scaleAndRotationOf(leftCorrectionMatrix)
            rightScaleCorrection, rightRotCorrection = scaleAndRotationOf(rightCorrectionMatrix)
            
            location = leftCorrectionMatrix * location
            rotation = leftRotCorrection * rotation * rightRotCorrection
            #TODO scale (negative scale?)

            poseBone.scale = scale
            poseBone.rotation_quaternion = rotation
            poseBone.location = location
            
            self.animateBone(bone, leftCorrectionMatrix, rightCorrectionMatrix)
            index+=1
    
    def fix180DegreeRotationsInMapWithKeys(self, timeToRotationMap, timeEntries):
        def sqr(x):
            return x*x
        lastRotation = None
        for timeInMS in timeEntries:
            rotation = timeToRotationMap.get(timeInMS)
            if lastRotation != None:
                sumOfSquares =  sqr(rotation.x - lastRotation.x) + sqr(rotation.y - lastRotation.y) + sqr(rotation.z - lastRotation.z) + sqr(rotation.w - lastRotation.w)
                sumOfSquaresMinus =  sqr(-rotation.x - lastRotation.x) + sqr(-rotation.y - lastRotation.y) + sqr(-rotation.z - lastRotation.z) + sqr(-rotation.w - lastRotation.w)
                if sumOfSquaresMinus < sumOfSquares:
                    rotation = mathutils.Quaternion((-rotation.w, -rotation.x, -rotation.y, -rotation.z))
                    timeToRotationMap[timeInMS] = rotation
            
            lastRotation = rotation
            
    def applyCorrectionToLocRotScaleMaps(self, leftCorrectionMatrix, rightCorrectionMatrix, timeToLocationMap, timeToRotationMap, timeToScaleMap, timeEntries):
        for timeInMS in timeEntries:
            location = timeToLocationMap.get(timeInMS)
            rotation = timeToRotationMap.get(timeInMS)
            scale = timeToScaleMap.get(timeInMS)

            location = toBlenderVector3(location)
            rotation = toBlenderQuaternion(rotation)
            scale = toBlenderVector3(scale)
            relSpecifiedMatrix = rotation.to_matrix().to_4x4()
            relSpecifiedMatrix.col[0] *= scale.x
            relSpecifiedMatrix.col[1] *= scale.y
            relSpecifiedMatrix.col[2] *= scale.z
            relSpecifiedMatrix.translation = location
                                
            newMatrix = leftCorrectionMatrix * relSpecifiedMatrix * rightCorrectionMatrix
            scale, rotation = scaleAndRotationOf(newMatrix)
            location = newMatrix.translation 
            timeToLocationMap[timeInMS] = location
            timeToRotationMap[timeInMS] = rotation
            timeToScaleMap[timeInMS] = scale
        
    def animateBone(self, m3Bone, leftCorrectionMatrix, rightCorrectionMatrix):
        for animationData in self.animations:
            scene = bpy.context.scene
            animation =  scene.m3_animations[animationData.animationIndex]
            animIdToTimeValueMap = animationData.animIdToTimeValueMap
            action = self.createOrGetActionFor(animationData, ownerTypeArmature)
            boneName = toValidBoneName(m3Bone.name)
            locationAnimPath = 'pose.bones["%s"].location' % boneName
            timeToLocationMap = animIdToTimeValueMap.get(m3Bone.location.header.animId,{0:m3Bone.location.initValue})
            timeToLocationMap = convertToBlenderVector3Map(timeToLocationMap)
            
            rotationAnimPath = 'pose.bones["%s"].rotation_quaternion' % boneName
            timeToRotationMap = animIdToTimeValueMap.get(m3Bone.rotation.header.animId,{0:m3Bone.rotation.initValue})
            timeToRotationMap = convertToBlenderQuaternionMap(timeToRotationMap)

            scaleAnimPath = 'pose.bones["%s"].scale' % boneName
            timeToScaleMap = animIdToTimeValueMap.get(m3Bone.scale.header.animId,{0:m3Bone.scale.initValue})
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


            group = boneName
            locXCurve = action.fcurves.new(locationAnimPath, 0, group)
            locYCurve = action.fcurves.new(locationAnimPath, 1, group)
            locZCurve = action.fcurves.new(locationAnimPath, 2, group)
            rotWCurve = action.fcurves.new(rotationAnimPath, 0, group)
            rotXCurve = action.fcurves.new(rotationAnimPath, 1, group)
            rotYCurve = action.fcurves.new(rotationAnimPath, 2, group)
            rotZCurve = action.fcurves.new(rotationAnimPath, 3, group)
            scaXCurve = action.fcurves.new(scaleAnimPath, 0, group)
            scaYCurve = action.fcurves.new(scaleAnimPath, 1, group)
            scaZCurve = action.fcurves.new(scaleAnimPath, 2, group)
            
            
            for timeInMS in timeEntries:
                location = timeToLocationMap.get(timeInMS)
                rotation = timeToRotationMap.get(timeInMS)
                scale = timeToScaleMap.get(timeInMS)
                frame = msToFrame(timeInMS)
                insertLinearKeyFrame(locXCurve, frame, location.x)
                insertLinearKeyFrame(locYCurve, frame, location.y)
                insertLinearKeyFrame(locZCurve, frame, location.z)
                insertLinearKeyFrame(rotWCurve, frame, rotation.w)
                insertLinearKeyFrame(rotXCurve, frame, rotation.x)
                insertLinearKeyFrame(rotYCurve, frame, rotation.y)
                insertLinearKeyFrame(rotZCurve, frame, rotation.z)
                insertLinearKeyFrame(scaXCurve, frame, scale.x)
                insertLinearKeyFrame(scaYCurve, frame, scale.y)
                insertLinearKeyFrame(scaZCurve, frame, scale.z)
    
    def createMaterials(self):
        currentScene = bpy.context.scene
        index = 0
        for materialsEntry in self.model.standardMaterials:
            material = currentScene.m3_materials.add()
            animPathPrefix = "m3_materials[%s]." % index
            fieldVisitor = BlenderPropertiesSettingFieldVisitor(self, animPathPrefix)
            visitFieldPropertyPairs(blenderObject=material, m3Object=materialsEntry, fieldVisitor=fieldVisitor)
            layerIndex = 0
            for (layerName, layerFieldName) in zip(shared.materialLayerNames, shared.materialLayerFieldNames):
                materialLayersEntry = getattr(materialsEntry,layerFieldName)[0]
                materialLayer = material.layers.add()
                materialLayer.name = layerName
                animPathPrefix = "m3_materials[%s].layers[%s]." % (index, layerIndex)
                fieldVisitor = BlenderPropertiesSettingFieldVisitor(self, animPathPrefix)
                visitFieldPropertyPairs(blenderObject=materialLayer, m3Object=materialLayersEntry, fieldVisitor=fieldVisitor)
                materialLayer.textureWrapX = materialLayersEntry.getNamedBit("flags", "textureWrapX")
                materialLayer.textureWrapY = materialLayersEntry.getNamedBit("flags", "textureWrapY")
                materialLayer.colorEnabled = materialLayersEntry.getNamedBit("flags", "colorEnabled")
                materialLayer.alphaAsTeamColor = materialLayersEntry.getNamedBit("alphaFlags", "alphaAsTeamColor")
                materialLayer.alphaOnly = materialLayersEntry.getNamedBit("alphaFlags", "alphaOnly")
                materialLayer.alphaBasedShading = materialLayersEntry.getNamedBit("alphaFlags", "alphaBasedShading")
                layerIndex += 1
            index += 1
            material.blendMode = str(materialsEntry.blendMode)
            material.layerBlendType = str(materialsEntry.layerBlendType)
            material.emisBlendType = str(materialsEntry.emisBlendType)
            material.specType = str(materialsEntry.specType)
            material.unfogged = materialsEntry.getNamedBit("flags", "unfogged")
            material.twoSided = materialsEntry.getNamedBit("flags", "twoSided")
            material.unshaded = materialsEntry.getNamedBit("flags", "unshaded")
            material.noShadowsCast = materialsEntry.getNamedBit("flags", "noShadowsCast")
            material.noHitTest = materialsEntry.getNamedBit("flags", "noHitTest")
            material.noShadowsReceived = materialsEntry.getNamedBit("flags", "noShadowsReceived")
            material.depthPrepass = materialsEntry.getNamedBit("flags", "depthPrepass")
            material.useTerrainHDR = materialsEntry.getNamedBit("flags", "useTerrainHDR")
            material.splatUVfix = materialsEntry.getNamedBit("flags", "splatUVfix")
            material.softBlending = materialsEntry.getNamedBit("flags", "softBlending")
            material.forParticles = materialsEntry.getNamedBit("flags", "forParticles")
            material.unknownFlag0x1 = materialsEntry.getNamedBit("unknownFlags", "unknownFlag0x1")
            material.unknownFlag0x4 = materialsEntry.getNamedBit("unknownFlags", "unknownFlag0x4")
            material.unknownFlag0x8 = materialsEntry.getNamedBit("unknownFlags", "unknownFlag0x8")
            material.unknownFlag0x200 = materialsEntry.getNamedBit("unknownFlags", "unknownFlag0x200")


    def createParticleSystems(self):
        currentScene = bpy.context.scene
        print("Loading particle systems")
        index = 0
        for particlesEntry in self.model.particles:
            particle_system = currentScene.m3_particle_systems.add()
            animPathPrefix = "m3_particle_systems[%s]." % index
            fieldVisitor = BlenderPropertiesSettingFieldVisitor(self, animPathPrefix)
            visitFieldPropertyPairs(blenderObject=particle_system, m3Object=particlesEntry, fieldVisitor=fieldVisitor)
            boneEntry = self.model.bones[particlesEntry.bone]
            fullBoneName = boneEntry.name
            star2ParticlePrefix = "Star2Part"
            if fullBoneName.startswith(star2ParticlePrefix):
                particle_system.boneSuffix = fullBoneName[len(star2ParticlePrefix):]
            else:
                print("Warning: A particle system was bound to bone %s which does not start with %s" %(fullBoneName, star2ParticlePrefix))
                particle_system.boneSuffix = fullBoneName
            particle_system.type = str(particlesEntry.type)
            particle_system.materialName = self.model.standardMaterials[particlesEntry.matmIndex].name
            particle_system.sort = particlesEntry.getNamedBit("flags", "sort")
            particle_system.collideTerrain = particlesEntry.getNamedBit("flags", "collideTerrain")
            particle_system.collideObjects = particlesEntry.getNamedBit("flags", "collideObjects")
            particle_system.spawnOnBounce = particlesEntry.getNamedBit("flags", "spawnOnBounce")
            particle_system.useInnerShape = particlesEntry.getNamedBit("flags", "useInnerShape")
            particle_system.inheritEmissionParams = particlesEntry.getNamedBit("flags", "inheritEmissionParams")
            particle_system.inheritParentVel = particlesEntry.getNamedBit("flags", "inheritParentVel")
            particle_system.sortByZHeight = particlesEntry.getNamedBit("flags", "sortByZHeight")
            particle_system.reverseIteration = particlesEntry.getNamedBit("flags", "reverseIteration")
            particle_system.smoothRotation = particlesEntry.getNamedBit("flags", "smoothRotation")
            particle_system.bezSmoothRotation = particlesEntry.getNamedBit("flags", "bezSmoothRotation")
            particle_system.smoothSize = particlesEntry.getNamedBit("flags", "smoothSize")
            particle_system.bezSmoothSize = particlesEntry.getNamedBit("flags", "bezSmoothSize")
            particle_system.smoothColor = particlesEntry.getNamedBit("flags", "smoothColor")
            particle_system.bezSmoothColor = particlesEntry.getNamedBit("flags", "bezSmoothColor")
            particle_system.litParts = particlesEntry.getNamedBit("flags", "litParts")
            particle_system.randFlipBookStart = particlesEntry.getNamedBit("flags", "randFlipBookStart")
            particle_system.multiplyByGravity = particlesEntry.getNamedBit("flags", "multiplyByGravity")
            particle_system.clampTailParts = particlesEntry.getNamedBit("flags", "clampTailParts")
            particle_system.spawnTrailingParts = particlesEntry.getNamedBit("flags", "spawnTrailingParts")
            particle_system.fixLengthTailParts = particlesEntry.getNamedBit("flags", "fixLengthTailParts")
            particle_system.useVertexAlpha = particlesEntry.getNamedBit("flags", "useVertexAlpha")
            particle_system.modelParts = particlesEntry.getNamedBit("flags", "modelParts")
            particle_system.swapYZonModelParts = particlesEntry.getNamedBit("flags", "swapYZonModelParts")
            particle_system.scaleTimeByParent = particlesEntry.getNamedBit("flags", "scaleTimeByParent")
            particle_system.useLocalTime = particlesEntry.getNamedBit("flags", "useLocalTime")
            particle_system.simulateOnInit = particlesEntry.getNamedBit("flags", "simulateOnInit")
            particle_system.copy = particlesEntry.getNamedBit("flags", "copy")
            
            index += 1


    def createAttachmentPoints(self):
        print("Loading attachment points")
        currentScene = bpy.context.scene
        for attachmentPointEntry in self.model.attachments:
            attachment_point = currentScene.m3_attachment_points.add()
            attachment_point.name = attachmentPointEntry.name
            boneEntry = self.model.bones[attachmentPointEntry.bone]
            attachment_point.boneName = toValidBoneName(boneEntry.name)

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
        vertexPositions = []
        for m3Vertex in m3Vertices:
            # todo use toBlenderVector3( and allocate somehow list in advance
            position = (m3Vertex.position.x, m3Vertex.position.y, m3Vertex.position.z)
            vertexPositions.append(position)
        
        bpy.ops.object.mode_set(mode='OBJECT')

        # create faces
        faces = []
        for division in self.model.divisions:
            divisionFaceIndices = division.faces
            for region in division.regions:
                firstVertexIndexIndex = region.firstFaceVertexIndexIndex
                lastVertexIndexIndex = firstVertexIndexIndex + region.numberOfFaceVertexIndices
                vertexIndexIndex = firstVertexIndexIndex
                firstVertexIndex = region.firstVertexIndex
                assert region.numberOfFaceVertexIndices % 3 == 0
                while vertexIndexIndex + 2 <= lastVertexIndexIndex:
                    i0 = firstVertexIndex + divisionFaceIndices[vertexIndexIndex]
                    i1 = firstVertexIndex + divisionFaceIndices[vertexIndexIndex + 1]
                    i2 = firstVertexIndex + divisionFaceIndices[vertexIndexIndex + 2]
                    face = (i0, i1, i2)
                    faces.append(face)
                    vertexIndexIndex += 3
                    

        mesh = bpy.data.meshes.new('Mesh')
        meshObject = bpy.data.objects.new('MeshObject', mesh)
        meshObject.location = (0,0,0)
        meshObject.show_name = True
        bpy.context.scene.objects.link(meshObject)
        mesh.from_pydata(vertexPositions, [], faces)
        mesh.update(calc_edges=True)
        
        
        uvLayer = mesh.uv_textures.new()
        for faceIndex, face in enumerate(faces):
            faceUV = uvLayer.data[faceIndex]
            faceUV.uv1 = toBlenderUVCoordinate(m3Vertices[face[0]].uv0)
            faceUV.uv2 = toBlenderUVCoordinate(m3Vertices[face[1]].uv0)
            faceUV.uv3 = toBlenderUVCoordinate(m3Vertices[face[2]].uv0)

        for division in self.model.divisions:
            for region in division.regions:
                boneIndexLookup = model.boneLookup[region.firstBoneLookupIndex:region.firstBoneLookupIndex + region.numberOfBoneLookupIndices]
                vertexGroupLookup = []
                for boneIndex in boneIndexLookup:
                    boneName = toValidBoneName(model.bones[boneIndex].name)
                    if boneName in meshObject.vertex_groups:
                        vertexGroup = meshObject.vertex_groups[boneName]
                    else:
                        vertexGroup =  meshObject.vertex_groups.new(boneName)
                    vertexGroupLookup.append(vertexGroup)
                
                for vertexIndex in range(region.firstVertexIndex,region.numberOfVertices):
                    m3Vertex = m3Vertices[vertexIndex]
                    boneWeightsAsInt = [m3Vertex.boneWeight0, m3Vertex.boneWeight1, m3Vertex.boneWeight2, m3Vertex.boneWeight3]
                    boneLookupIndices = [m3Vertex.boneLookupIndex0, m3Vertex.boneLookupIndex1,  m3Vertex.boneLookupIndex2,  m3Vertex.boneLookupIndex3]
                    boneWeights = []
                    for boneWeightAsInt, boneLookupIndex in zip(boneWeightsAsInt, boneLookupIndices):
                        if boneWeightAsInt != 0:
                            vertexGroup = vertexGroupLookup[boneLookupIndex]
                            boneWeight = boneWeightAsInt / 255.0
                            vertexGroup.add([vertexIndex], boneWeight, 'REPLACE')
        
        modifier = meshObject.modifiers.new('UseArmature', 'ARMATURE')
        modifier.object = self.armatureObject
        modifier.use_bone_envelopes = False
        modifier.use_vertex_groups = True            

    def createAnimIdToKeyFramesMapFor(self, stc):
        keyFramesLists = [stc.sdev, stc.sd2v, stc.sd3v, stc.sd4q, stc.sdcc, stc.sdr3, stc.unknownRef8, stc.sds6, stc.unknownRef10, stc.unknownRef11, stc.unknownRef12, stc.sdfg, stc.sdmb]
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



    def createOrGetActionFor(self, animationData, ownerType):
        ownerTypesToActionMap = animationData.ownerTypeToActionMap
        scene = bpy.context.scene
        animation = scene.m3_animations[animationData.animationIndex]
        action = ownerTypesToActionMap.get(ownerType)
        if action == None:
            action = bpy.data.actions.new(animation.name + ownerType)
            ownerTypesToActionMap[ownerType] = action
            actionAssignment = animation.assignedActions.add()
            actionAssignment.actionName = action.name
            if ownerType == ownerTypeArmature:
                action.id_root = "OBJECT"
                actionAssignment.targetName = self.armatureObject.name
            elif ownerType == ownerTypeScene:
                action.id_root = "SCENE"
                actionAssignment.targetName = bpy.context.scene.name
            else:
                raise Exception("Unhandled case")
        return action

    def createAnimations(self):
        print ("Creating actions(animation sequences)")
        scene = bpy.context.scene
        ownerTypeToIdleActionMap = {}
        model = self.model
        numberOfSequences = len(model.sequences)
        if len(model.sequenceTransformationGroups) != numberOfSequences:
            raise Exception("The model has not the same amounth of stg elements as it has sequences")

        for sequenceIndex in range(numberOfSequences):
            sequence = model.sequences[sequenceIndex]
            stg = model.sequenceTransformationGroups[sequenceIndex]
            if (sequence.name != stg.name):
                raise Exception("Name of sequence and it's transformation group does not match")
            animation = scene.m3_animations.add()
            animation.name = sequence.name
            animation.startFrame = msToFrame(sequence.animStartInMS)
            animation.endFrame = msToFrame(sequence.animEndInMS)
            animation.notLooping =  sequence.getNamedBit("flags", "notLooping")
            animation.alwaysGlobal =  sequence.getNamedBit("flags", "alwaysGlobal")
            animation.globalInPreviewer =  sequence.getNamedBit("flags", "globalInPreviewer")
            
            fieldVisitor = BlenderPropertiesSettingFieldVisitor(self, None)
            visitFieldPropertyPairs(blenderObject=animation, m3Object=sequence, fieldVisitor=fieldVisitor)

            animIdToTimeValueMap = {}
            ownerTypeToActionMap = {}
            for stcIndex in stg.stcIndices:
                stc = model.sequenceTransformationCollections[stcIndex]

                animIdToTimeValueMapForSTC = self.createAnimIdToKeyFramesMapFor(stc)
                for animId, timeValueMap in animIdToTimeValueMapForSTC.items():
                    if animId in animIdToTimeValueMap:
                        raise Exception("Same animid %s got animated by different STC" % animId)
                    animIdToTimeValueMap[animId] = timeValueMap
                    
                # stc.seqIndex seems to be wrong:
                #sequence = model.sequences[stc.seqIndex]
                if len(stc.animIds) != len(stc.animRefs):
                    raise Exception("len(stc.animids) != len(stc.animrefs)")
                
            self.animations.append(AnimationData(animIdToTimeValueMap, ownerTypeToActionMap, sequenceIndex))




    def actionAndTimeValueMapPairsFor(self, ownerType, animId):
        for animationData in self.animations:
            timeValueMap = animationData.animIdToTimeValueMap.get(animId)
            if timeValueMap != None:
                action = self.createOrGetActionFor(animationData, ownerType)
                yield (action, timeValueMap)

    def animateFloat(self, ownerType, path, animId):
        for action, timeValueMap in self.actionAndTimeValueMapPairsFor(ownerType, animId):
            curve = action.fcurves.new(path, 0)
            for frame, value in frameValuePairs(timeValueMap):
                insertLinearKeyFrame(curve, frame, value)
    
    def animateInteger(self, ownerType, path, animId):
        for action, timeValueMap in self.actionAndTimeValueMapPairsFor(ownerType, animId):
            curve = action.fcurves.new(path, 0)
            for frame, value in frameValuePairs(timeValueMap):
                insertConstantKeyFrame(curve, frame, value)

    def animateVector3(self, ownerType, path, animId):
        for action, timeValueMap in self.actionAndTimeValueMapPairsFor(ownerType, animId):
            xCurve = action.fcurves.new(path, 0)
            yCurve = action.fcurves.new(path, 1)
            zCurve = action.fcurves.new(path, 2)
            
            for frame, value in frameValuePairs(timeValueMap):
                insertLinearKeyFrame(xCurve, frame, value.x)
                insertLinearKeyFrame(yCurve, frame, value.y)
                insertLinearKeyFrame(zCurve, frame, value.z)

    def animateColor(self, ownerType, path, animId):
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
