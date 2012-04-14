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
import os.path

actionTypeScene = "SCENE"
actionTypeArmature = "OBJECT"

class Exporter:
    def exportParticleSystems(self, scene, m3FileName):
        self.generatedAnimIdCounter = 0
        self.scene = scene
        if scene.render.fps != 30:
            print("Warning: It's recommended to export models with a frame rate of 30 (current is %s)" % scene.render.fps)
        self.nameToAnimIdToAnimDataMap = {}
        for animation in scene.m3_animations:
            self.nameToAnimIdToAnimDataMap[animation.name] = {}
        
        model = self.createModel(m3FileName)
        m3.saveAndInvalidateModel(model, m3FileName)

    def createModel(self, m3FileName):
        model = m3.MODLV23()
        model.modelName = os.path.basename(m3FileName)
        
        self.initMesh(model)
        self.initMaterials(model)
        self.initParticles(model)
        self.prepareAnimationEndEvents()
        self.initWithPreparedAnimationData(model)
        
        model.matrix = self.createIdentityMatrix()
        model.uniqueUnknownNumber = 0
        return model
    
    def initMesh(self, model):
        meshObject = self.findMeshObject()
        hasMesh = meshObject != None
        model.setNamedBit("flags", "hasMesh", hasMesh)
        model.boundings = self.createAlmostEmptyBoundingsWithRadius(2.0)

        if not hasMesh:
            model.nSkinBones = 0
            model.divisions = [self.createEmptyDivision()]
            return
            
        mesh = meshObject.data
        
        division = m3.DIV_V2()
        model.divisions.append(division)
        
        rootBoneIndex = self.addBoneWithRestPosAndReturnIndex(model, "StaticMesh", skinBone=True, realBone=True)
        
        firstBoneLookupIndex = len(model.boneLookup)
        boneLookupIndex = 0
        model.boneLookup.append(rootBoneIndex)
        numberOfBones = 1
        if len(meshObject.modifiers) == 0:
            pass
        elif len(meshObject.modifiers) == 1 and (meshObject.modifiers[0].type == "ARMATURE"):
            modifier = meshObject.modifiers[0]
            armatureObject = modifier.object
            armature = armatureObject.data #todo is that so?
            
            boneNameToBoneIndexMap = {}# map: bone name to index in model bone list
            boneNameToBoneLookupIndexMap = {}
            boneNameToAbsInvRestPoseMatrix = {}
            for blenderBoneIndex, blenderBone in enumerate(armature.bones):
                boneIndex = len(model.bones)
                bone = self.createStaticBoneAtOrigin(blenderBone.name, skinBone=True, realBone=True)
                model.bones.append(bone)
                                
                absRestPosMatrix = blenderBone.matrix_local    
                if blenderBone.parent != None:
                    bone.parent = boneNameToBoneIndexMap[blenderBone.parent.name]
                    absInvRestPoseMatrixParent = boneNameToAbsInvRestPoseMatrix[blenderBone.parent.name]
                    relRestPosMatrix = absInvRestPoseMatrixParent * absRestPosMatrix
                else:
                    bone.parent = rootBoneIndex
                    relRestPosMatrix = absRestPosMatrix
                
                poseBone = armatureObject.pose.bones[blenderBoneIndex]
                poseRotationNormalized = poseBone.rotation_quaternion.normalized()
                poseMatrix = shared.locRotScaleMatrix(poseBone.location, poseRotationNormalized, poseBone.scale)
                
                if blenderBone.parent != None:
                    leftCorrectionMatrix = shared.rotFixMatrix * relRestPosMatrix
                else:
                    leftCorrectionMatrix = relRestPosMatrix
                rightCorrectionMatrix = shared.rotFixMatrixInverted
                m3PoseMatrix = leftCorrectionMatrix * poseMatrix * rightCorrectionMatrix
                
                scale, rotation = shared.scaleAndRotationOf(m3PoseMatrix)
                location = m3PoseMatrix.translation
                bone.scale.initValue = self.createVector3FromBlenderVector(scale)
                bone.scale.nullValue = self.createVector3FromBlenderVector(scale)
                bone.rotation.initValue = self.createQuaternionFromBlenderQuaternion(rotation)
                bone.rotation.nullValue = self.createQuaternionFromBlenderQuaternion(rotation)
                bone.location.initValue = self.createVector3FromBlenderVector(location)
                bone.location.nullValue = self.createVector3FromBlenderVector(location)

                boneName = blenderBone.name
                
                locationAnimId = bone.location.header.animId
                rotationAnimId = bone.rotation.header.animId
                scaleAnimId = bone.scale.header.animId
                
                locationAnimPath = 'pose.bones["%s"].location' % boneName
                rotationAnimPath = 'pose.bones["%s"].rotation_quaternion' % boneName
                scaleAnimPath = 'pose.bones["%s"].scale' % boneName
        
                animationActionTuples = self.determineAnimationActionTuplesFor(armatureObject.name, actionTypeArmature)
                for animation, action in animationActionTuples:
                    frames = self.getAllFramesOf(animation)
                    timeValuesInMS = self.allFramesToMSValues(frames)
                    xLocValues = self.getNoneOrValuesFor(action, locationAnimPath, 0, frames)
                    yLocValues = self.getNoneOrValuesFor(action, locationAnimPath, 1, frames)
                    zLocValues = self.getNoneOrValuesFor(action, locationAnimPath, 2, frames)
                    wRotValues = self.getNoneOrValuesFor(action, rotationAnimPath, 0, frames)
                    xRotValues = self.getNoneOrValuesFor(action, rotationAnimPath, 1, frames)
                    yRotValues = self.getNoneOrValuesFor(action, rotationAnimPath, 2, frames)
                    zRotValues = self.getNoneOrValuesFor(action, rotationAnimPath, 3, frames)
                    xScaValues = self.getNoneOrValuesFor(action, scaleAnimPath, 0, frames)
                    yScaValues = self.getNoneOrValuesFor(action, scaleAnimPath, 1, frames)
                    zScaValues = self.getNoneOrValuesFor(action, scaleAnimPath, 2, frames)

                    locAnimated = (xLocValues != None) or (yLocValues != None) or (zLocValues != None)
                    rotAnimated = (wRotValues != None) or (xRotValues != None) or (yRotValues != None) or (zRotValues != None)
                    scaAnimated = (xScaValues != None) or (yScaValues != None) or (zScaValues != None)
                    if locAnimated or rotAnimated or scaAnimated:
                        if xLocValues == None:
                            xLocValues = len(timeValuesInMS) * [location.x]
                        if yLocValues == None:
                            yLocValues = len(timeValuesInMS) * [location.y]
                        if zLocValues == None:
                            zLocValues = len(timeValuesInMS) * [location.z]
                                                    
                        if wRotValues == None:
                            wRotValues = len(timeValuesInMS) * [rotation.w]
                        if xRotValues == None:
                            xRotValues = len(timeValuesInMS) * [rotation.x]
                        if yRotValues == None:
                            yRotValues = len(timeValuesInMS) * [rotation.y]
                        if zRotValues == None:
                            zRotValues = len(timeValuesInMS) * [rotation.z]
                            
                        if xScaValues == None:
                            xScaValues = len(timeValuesInMS) * [scale.x]
                        if yScaValues == None:
                            yScaValues = len(timeValuesInMS) * [scale.y]
                        if zScaValues == None:
                            zScaValues = len(timeValuesInMS) * [scale.z]
                        m3Locs = []
                        m3Rots = []
                        m3Scas = []
                        for xLoc, yLoc, zLoc, wRot, xRot, yRot, zRot, xSca, ySca, zSca in zip(xLocValues, yLocValues, zLocValues, wRotValues, xRotValues, yRotValues, zRotValues, xScaValues, yScaValues, zScaValues):
                            loc = mathutils.Vector((xLoc, yLoc, zLoc))
                            rot = mathutils.Quaternion((wRot, xRot, yRot, zRot)).normalized()
                            sca = mathutils.Vector((xSca, ySca, zSca))
                            poseMatrix = shared.locRotScaleMatrix(loc, rot, sca)
                            m3PoseMatrix = leftCorrectionMatrix * poseMatrix * rightCorrectionMatrix
                            sca, rot = shared.scaleAndRotationOf(m3PoseMatrix)
                            loc = m3PoseMatrix.translation
                            m3Locs.append(self.createVector3FromBlenderVector(loc))
                            m3Rots.append(self.createQuaternionFromBlenderQuaternion(rot))
                            m3Scas.append(self.createVector3FromBlenderVector(sca))
                        
                        animIdToAnimDataMap = self.nameToAnimIdToAnimDataMap[animation.name]

                        m3AnimBlock = m3.SD3VV0()
                        m3AnimBlock.frames = timeValuesInMS
                        m3AnimBlock.flags = 0
                        m3AnimBlock.fend = self.frameToMS(animation.endFrame)
                        m3AnimBlock.keys = m3Locs
                        animIdToAnimDataMap[locationAnimId] = m3AnimBlock
                        
                        m3AnimBlock = m3.SD4QV0()
                        m3AnimBlock.frames = timeValuesInMS
                        m3AnimBlock.flags = 0
                        m3AnimBlock.fend = self.frameToMS(animation.endFrame)
                        m3AnimBlock.keys = m3Rots
                        animIdToAnimDataMap[rotationAnimId] = m3AnimBlock
                    
                        m3AnimBlock = m3.SD3VV0()
                        m3AnimBlock.frames = timeValuesInMS
                        m3AnimBlock.flags = 0
                        m3AnimBlock.fend = self.frameToMS(animation.endFrame)
                        m3AnimBlock.keys = m3Scas
                        animIdToAnimDataMap[scaleAnimId] = m3AnimBlock
                        
                        bone.location.header.flags = 1
                        bone.location.header.animFlags = shared.animFlagsForAnimatedProperty
                        bone.rotation.header.flags = 1
                        bone.rotation.header.animFlags = shared.animFlagsForAnimatedProperty
                        bone.scale.header.flags = 1
                        bone.scale.header.animFlags = shared.animFlagsForAnimatedProperty
                        bone.setNamedBit("flags", "animated", True)
                   
                        
                absRestPosMatrixFixed = absRestPosMatrix * shared.rotFixMatrixInverted
                absoluteInverseRestPoseMatrixFixed = absRestPosMatrixFixed.inverted()

                absoluteInverseBoneRestPos = self.createRestPositionFromBlender4x4Matrix(absoluteInverseRestPoseMatrixFixed)
                model.absoluteInverseBoneRestPositions.append(absoluteInverseBoneRestPos)
                boneLookupIndex = len(model.boneLookup) - firstBoneLookupIndex
                model.boneLookup.append(boneIndex)
                boneNameToBoneIndexMap[blenderBone.name] = boneIndex
                boneNameToBoneLookupIndexMap[blenderBone.name] = boneLookupIndex
                boneNameToAbsInvRestPoseMatrix[blenderBone.name] = absRestPosMatrix.inverted()
                numberOfBones += 1
        else:
            raise Exception("Mesh must have no modifiers except single one for the armature")
            

        firstFaceVertexIndexIndex = len(division.faces)
        m3Vertices = []
        for blenderFace in mesh.faces:
            if len(blenderFace.vertices) != 3:
                raise Exception("Only the export of meshes with triangles has been implemented")
            for faceRelativeVertexIndex, blenderVertexIndex in enumerate(blenderFace.vertices):
                blenderVertex =  mesh.vertices[blenderVertexIndex]
                m3Vertex = m3.VertexFormat0x182007d()
                m3Vertex.position = self.blenderToM3Vector(blenderVertex.co)
                
                boneWeightSlot = 0
                for gIndex, g in enumerate(blenderVertex.groups):
                    vertexGroupIndex = g.group
                    vertexGroup = meshObject.vertex_groups[vertexGroupIndex]
                    boneLookupIndex = boneNameToBoneLookupIndexMap[vertexGroup.name]
                    boneWeight = round(g.weight * 255)
                    if boneWeight != 0:
                        if boneWeightSlot == 4:
                            raise Exception("The m3 format supports at maximum 4 bone weights per vertex")
                        setattr(m3Vertex, "boneWeight%d" % boneWeightSlot, boneWeight)
                        setattr(m3Vertex, "boneLookupIndex%d" % boneWeightSlot, boneLookupIndex)
                        boneWeightSlot += 1
                if boneWeightSlot == 0:
                    m3Vertex.boneWeight0 = 255
                    m3Vertex.boneLookupIndex0 = boneLookupIndex
                if len(mesh.uv_textures) >= 1:
                    uvData = mesh.uv_textures[0].data[blenderFace.index]
                    m3Vertex.uv0 = self.convertBlenderToM3UVCoordinates(getattr(uvData, "uv%d" % (faceRelativeVertexIndex + 1)))
                else:
                    raise Exception("Exporting meshes without texture coordinates isn't supported yet")
                m3Vertex.normal = self.blenderVector3AndScaleToM3Vector4As4uint8(blenderVertex.normal, 0.0)
                m3Vertex.tangent = self.createVector4As4uint8FromFloats(0.0, 0.0, 0.0, 0.0)
                m3.VertexFormat0x182007d.validateInstance(m3Vertex, "vertex")
                m3Vertices.append(m3Vertex)
        
        model.vertices = m3.VertexFormat0x182007d.rawBytesForOneOrMore(m3Vertices)
        model.vFlags = 0x182007d   
        vertexIndicesOfFaces = list(range(firstFaceVertexIndexIndex,firstFaceVertexIndexIndex + len(m3Vertices)))
        division.faces.extend(vertexIndicesOfFaces)
        
        bat = m3.BAT_V1()
        bat.subId = 0
        if len(self.scene.m3_materials) == 0:
            raise Exception("Require a m3 material to export a mesh")
        bat.matId = 0
        division.bat.append(bat)
        
        minV = mathutils.Vector((float("inf"), float("inf") ,float("inf")))
        maxV = mathutils.Vector((-float("inf"), -float("inf"), -float("inf")))
        #TODO case 0 vertices
        for blenderVertex in mesh.vertices:
            for i in range(3):  
                minV[i] = min(minV[i], blenderVertex.co[i])
                maxV[i] = max(maxV[i], blenderVertex.co[i])
        
        diffV = minV - maxV
        radius = diffV.length / 2
        division.msec.append(self.createEmptyMSec(minX=minV[0], minY=minV[1], minZ=minV[2], maxX=maxV[0], maxY=maxV[1], maxZ=maxV[2], radius=radius))
        region = m3.REGNV3()
        region.firstVertexIndex = 0
        region.numberOfVertices = len(m3Vertices)
        region.firstFaceVertexIndexIndex = firstFaceVertexIndexIndex
        region.numberOfFaceVertexIndices = len(vertexIndicesOfFaces)
        region.numberOfBones = numberOfBones
        region.firstBoneLookupIndex = firstBoneLookupIndex
        region.numberOfBoneLookupIndices = numberOfBones
        region.rootBoneIndex = rootBoneIndex
        division.regions.append(region)
        
        model.nSkinBones = numberOfBones
    
    def blenderVector3AndScaleToM3Vector4As4uint8(self, blenderVector3, scale):
        x = blenderVector3.x
        y = blenderVector3.y
        z = blenderVector3.z
        w = scale
        return self.createVector4As4uint8FromFloats(x, y, z, w)

    def createVector4As4uint8FromFloats(self, x, y, z, w):
        m3Vector = m3.Vector4As4uint8()
        def convert(f):
            return round((-f+1) / 2.0 * 255.0)
        m3Vector.x = convert(x)
        m3Vector.y = convert(y)
        m3Vector.z = convert(z)
        m3Vector.w = convert(w)
        return m3Vector
        
    def convertBlenderToM3UVCoordinates(self, blenderUV):
        m3UV = m3.Vector2As2int16()
        m3UV.x = round(blenderUV.x * 2048) 
        m3UV.y = round((1 - blenderUV.y) * 2048) 
        return m3UV
    
    def blenderToM3Vector(self, blenderVector3):
        return self.createVector3(blenderVector3.x, blenderVector3.y, blenderVector3.z)
    
    def addBoneWithRestPosAndReturnIndex(self, model, boneName, skinBone, realBone):
        boneIndex = len(model.bones)
        bone = self.createStaticBoneAtOrigin(boneName,skinBone=skinBone, realBone=realBone)
        model.bones.append(bone)
        
        boneRestPos = self.createIdentityRestPosition()
        model.absoluteInverseBoneRestPositions.append(boneRestPos)
        return boneIndex
        
    def findMeshObject(self):
        meshObject = None
        for currentObject in bpy.data.objects:
            if currentObject.type == 'MESH':
                if meshObject == None:
                    meshObject = currentObject
                else:
                    raise Exception("Multiple mesh objects can't be exported yet")
        if (meshObject == None):
            return None
    
        mesh = meshObject.data
        if len(mesh.vertices) > 0:
            return meshObject
        else:
            return None
        
    
    def frameToMS(self, frame):
        frameRate = self.scene.render.fps
        return round((frame / frameRate) * 1000.0)
    
    def prepareAnimationEndEvents(self):
        scene = self.scene
        for animation in scene.m3_animations:
            animIdToAnimDataMap = self.nameToAnimIdToAnimDataMap[animation.name]
            animEndId = 0x65bd3215
            animIdToAnimDataMap[animEndId] = self.createAnimationEndEvent(animation)
    
    def createAnimationEndEvent(self, animation):
        event = m3.SDEVV0()
        event.frames = [self.frameToMS(animation.endFrame)]
        event.flags = 1
        event.fend = self.frameToMS(animation.endFrame)
        event.keys = [self.createAnimationEndEventKey(animation)]
        return event
        
    def createAnimationEndEventKey(self, animation):
        event = m3.EVNTV1()
        event.name = "Evt_SeqEnd"
        event.matrix = self.createIdentityMatrix()
        return event
    
    def initWithPreparedAnimationData(self, model):
        scene = self.scene
        for animation in scene.m3_animations:
            animIdToAnimDataMap = self.nameToAnimIdToAnimDataMap[animation.name]
            animIds = list(animIdToAnimDataMap.keys())
            animIds.sort()
            
            m3Sequence = m3.SEQSV1()
            m3Sequence.name = animation.name
            m3Sequence.animStartInMS = self.frameToMS(animation.startFrame)
            m3Sequence.animEndInMS = self.frameToMS(animation.endFrame)
            m3Sequence.movementSpeed = animation.movementSpeed
            m3Sequence.setNamedBit("flags", "notLooping", animation.notLooping)
            m3Sequence.setNamedBit("flags", "alwaysGlobal", animation.alwaysGlobal)
            m3Sequence.setNamedBit("flags", "globalInPreviewer", animation.globalInPreviewer)
            m3Sequence.frequency = animation.frequency
            m3Sequence.boundingSphere = self.createAlmostEmptyBoundingsWithRadius(2)
            seqIndex = len(model.sequences)
            model.sequences.append(m3Sequence)
            
            m3SequenceTransformationGroup = m3.STG_V0()
            m3SequenceTransformationGroup.name = animation.name
            stcIndex = len(model.sequenceTransformationCollections)
            m3SequenceTransformationGroup.stcIndices = [stcIndex]
            stgIndex = len(model.sequenceTransformationGroups)
            model.sequenceTransformationGroups.append(m3SequenceTransformationGroup)
            
            m3SequenceTransformationCollection = m3.STC_V4()
            m3SequenceTransformationCollection.name = animation.name + "_full"
            m3SequenceTransformationCollection.seqIndex = seqIndex
            m3SequenceTransformationCollection.stgIndex = stgIndex
            m3SequenceTransformationCollection.animIds = list(animIds)
            for animId in animIds:
                animData = animIdToAnimDataMap[animId]
                self.addAnimDataToTransformCollection(animData, m3SequenceTransformationCollection)
            model.sequenceTransformationCollections.append(m3SequenceTransformationCollection)

            m3STS = m3.STS_V0()
            m3STS.animIds = list(animIds)
            model.sts.append(m3STS)
    
    def addAnimDataToTransformCollection(self, animData, m3SequenceTransformationCollection):
        animDataType = type(animData)
        if animDataType == m3.SDEVV0:
            sdevIndex = len(m3SequenceTransformationCollection.sdev)
            m3SequenceTransformationCollection.sdev.append(animData)
            #sdev's have animation type index 0, so sdevIndex = animRef
            animRef = sdevIndex
        elif animDataType == m3.SD2VV0:
            sd2vIndex = len(m3SequenceTransformationCollection.sd2v)
            m3SequenceTransformationCollection.sd2v.append(animData)
            animRef = 0x10000 + sd2vIndex
        elif animDataType == m3.SD3VV0:
            sd3vIndex = len(m3SequenceTransformationCollection.sd3v)
            m3SequenceTransformationCollection.sd3v.append(animData)
            animRef = 0x20000 + sd3vIndex
        elif animDataType == m3.SD4QV0:
            sd4qIndex = len(m3SequenceTransformationCollection.sd4q)
            m3SequenceTransformationCollection.sd4q.append(animData)
            animRef = 0x30000 + sd4qIndex
        elif animDataType == m3.SDCCV0:
            sdccIndex = len(m3SequenceTransformationCollection.sdcc)
            m3SequenceTransformationCollection.sdcc.append(animData)
            animRef = 0x40000 + sdccIndex
        elif animDataType == m3.SDR3V0:
            sdr3Index = len(m3SequenceTransformationCollection.sdr3)
            m3SequenceTransformationCollection.sdr3.append(animData)
            animRef = 0x50000 + sdr3Index
        elif animDataType == m3.SDS6V0:
            sds6Index = len(m3SequenceTransformationCollection.sds6)
            m3SequenceTransformationCollection.sds6.append(animData)
            animRef = 0x70000 + sds6Index
        else:
            raise Exception("Can't handle animation data of type %s yet" % animDataType)
        m3SequenceTransformationCollection.animRefs.append(animRef)

    def initParticles(self, model):
        scene = self.scene
        for particleSystemIndex, particleSystem in enumerate(scene.m3_particle_systems):
            boneName = "Star2Part" + particleSystem.boneSuffix
            boneIndex = self.addBoneWithRestPosAndReturnIndex(model, boneName, skinBone=False, realBone=False)
            m3ParticleSystem = m3.PAR_V12()
            m3ParticleSystem.bone = boneIndex
            animPathPrefix = "m3_particle_systems[%s]." % particleSystemIndex
            transferer = BlenderToM3DataTransferer(exporter=self, m3Object=m3ParticleSystem, blenderObject=particleSystem, animPathPrefix=animPathPrefix, actionOwnerName=self.scene.name, actionOwnerType=actionTypeScene)
            transferer.transferAnimatableFloat("initEmissSpeed")
            transferer.transferAnimatableFloat("speedVar")
            transferer.transferBoolToInt("speedVarEnabled")
            transferer.transferAnimatableFloat("angleY")
            transferer.transferAnimatableFloat("angleX")
            transferer.transferAnimatableFloat("speedX")
            transferer.transferAnimatableFloat("speedY")
            transferer.transferAnimatableFloat("lifespan")
            transferer.transferAnimatableFloat("decay")
            transferer.transferBoolToInt("decayEnabled")
            transferer.transferFloat("emissSpeed2")
            transferer.transferFloat("scaleRatio")
            transferer.transferFloat("unknownFloat1a")
            transferer.transferFloat("unknownFloat1b")
            transferer.transferFloat("unknownFloat1c")
            transferer.transferAnimatableVector3("pemitScale")
            transferer.transferAnimatableVector3("speedUnk1")
            transferer.transferAnimatableColor("color1a")
            transferer.transferAnimatableColor("color1b")
            transferer.transferAnimatableColor("color1c")
            transferer.transferFloat("emissSpeed3")
            transferer.transferFloat("unknownFloat2a")
            transferer.transferFloat("unknownFloat2b")
            transferer.transferFloat("unknownFloat2c")
            transferer.transferBoolToInt("trailingEnabled")
            m3ParticleSystem.indexPlusHighestIndex = len(scene.m3_particle_systems) -1 + particleSystemIndex
            transferer.transferInt("maxParticles")
            transferer.transferAnimatableFloat("emissRate")
            transferer.transferEnum("type")
            transferer.transferAnimatableVector3("emissArea")
            transferer.transferAnimatableVector3("tailUnk1")
            transferer.transferAnimatableFloat("pivotSpread")
            transferer.transferAnimatableFloat("spreadUnk")
            transferer.transferBoolToInt("radialEmissionEnabled")
            transferer.transferBoolToInt("pemitScale2Enabled")
            transferer.transferAnimatableVector3("pemitScale2")
            transferer.transferBoolToInt("pemitRotateEnabled")
            transferer.transferAnimatableVector3("pemitRotate")
            transferer.transferBoolToInt("color2Enabled")
            transferer.transferAnimatableColor("color2a")
            transferer.transferAnimatableColor("color2b")
            transferer.transferAnimatableColor("color2c")
            transferer.transferAnimatableInt16("partEmit")
            m3ParticleSystem.speedUnk2 = self.createNullVector4As4uint8()
            transferer.transferFloat("lifespanRatio")
            transferer.transferInt("columns")
            transferer.transferInt("rows")
            m3ParticleSystem.setNamedBit("flags", "sort", particleSystem.sort)
            m3ParticleSystem.setNamedBit("flags", "collideTerrain", particleSystem.collideTerrain)
            m3ParticleSystem.setNamedBit("flags", "collideObjects", particleSystem.collideObjects)
            m3ParticleSystem.setNamedBit("flags", "spawnOnBounce", particleSystem.spawnOnBounce)
            m3ParticleSystem.setNamedBit("flags", "useInnerShape", particleSystem.useInnerShape)
            m3ParticleSystem.setNamedBit("flags", "inheritEmissionParams", particleSystem.inheritEmissionParams)
            m3ParticleSystem.setNamedBit("flags", "inheritParentVel", particleSystem.inheritParentVel)
            m3ParticleSystem.setNamedBit("flags", "sortByZHeight", particleSystem.sortByZHeight)
            m3ParticleSystem.setNamedBit("flags", "reverseIteration", particleSystem.reverseIteration)
            m3ParticleSystem.setNamedBit("flags", "smoothRotation", particleSystem.smoothRotation)
            m3ParticleSystem.setNamedBit("flags", "bezSmoothRotation", particleSystem.bezSmoothRotation)
            m3ParticleSystem.setNamedBit("flags", "smoothSize", particleSystem.smoothSize)
            m3ParticleSystem.setNamedBit("flags", "bezSmoothSize", particleSystem.bezSmoothSize)
            m3ParticleSystem.setNamedBit("flags", "smoothColor", particleSystem.smoothColor)
            m3ParticleSystem.setNamedBit("flags", "bezSmoothColor", particleSystem.bezSmoothColor)
            m3ParticleSystem.setNamedBit("flags", "litParts", particleSystem.litParts)
            m3ParticleSystem.setNamedBit("flags", "randFlipBookStart", particleSystem.randFlipBookStart)
            m3ParticleSystem.setNamedBit("flags", "multiplyByGravity", particleSystem.multiplyByGravity)
            m3ParticleSystem.setNamedBit("flags", "clampTailParts", particleSystem.clampTailParts)
            m3ParticleSystem.setNamedBit("flags", "spawnTrailingParts", particleSystem.spawnTrailingParts)
            m3ParticleSystem.setNamedBit("flags", "useVertexAlpha", particleSystem.useVertexAlpha)
            m3ParticleSystem.setNamedBit("flags", "modelParts", particleSystem.modelParts)
            m3ParticleSystem.setNamedBit("flags", "swapYZonModelParts", particleSystem.swapYZonModelParts)
            m3ParticleSystem.setNamedBit("flags", "scaleTimeByParent", particleSystem.scaleTimeByParent)
            m3ParticleSystem.setNamedBit("flags", "useLocalTime", particleSystem.useLocalTime)
            m3ParticleSystem.setNamedBit("flags", "simulateOnInit", particleSystem.simulateOnInit)
            m3ParticleSystem.setNamedBit("flags", "copy", particleSystem.copy)
            m3ParticleSystem.ar1 = self.createNullFloatAnimationReference(initValue=1.0, nullValue=0.0)

            materialIndices = []
            for materialIndex, material in enumerate(scene.m3_materials):
                if material.name == particleSystem.materialName:
                    materialIndices.append(materialIndex)
            
            if len(materialIndices) > 1:
                raise Exception("There are multiple materials with the same name")
            elif len(materialIndices) == 0:
                raise Exception("The material %s referenced by the particle system %s does not exist" % (m3ParticleSystem.materialName, m3ParticleSystem.name))
            m3ParticleSystem.matmIndex = materialIndices[0]

            model.particles.append(m3ParticleSystem)

    def toM3ColorComponent(self, blenderColorComponent):
        v = round(blenderColorComponent * 255)
        if v > 255:
            v = 255
        if v < 0:
            v = 0
        return v
    
    def toM3Color(self, blenderColor):
        color = m3.COLV0()
        color.red = self.toM3ColorComponent(blenderColor[0])
        color.green = self.toM3ColorComponent(blenderColor[1])
        color.blue = self.toM3ColorComponent(blenderColor[2])
        color.alpha = self.toM3ColorComponent(blenderColor[3])
        return color
        

    def createNullVector4As4uint8(self):
        vec = m3.Vector4As4uint8()
        vec.x = 0
        vec.y = 0
        vec.z = 0
        vec.w = 0
        return vec

    def createRestPositionFromBlender4x4Matrix(self, blenderMatrix):
        iref = m3.IREFV0()
        matrix = m3.Matrix44()
        matrix.x = self.createVector4FromBlenderVector(blenderMatrix.col[0])
        matrix.y = self.createVector4FromBlenderVector(blenderMatrix.col[1])
        matrix.z = self.createVector4FromBlenderVector(blenderMatrix.col[2])
        matrix.w = self.createVector4FromBlenderVector(blenderMatrix.col[3])
        iref.matrix = matrix
        return iref

    def createIdentityRestPosition(self):
        iref = m3.IREFV0()
        iref.matrix = self.createIdentityMatrix()
        return iref

    def createStaticBoneAtOrigin(self, name, skinBone, realBone):
        m3Bone = m3.BONEV1()
        m3Bone.name = name
        m3Bone.flags = 0
        m3Bone.setNamedBit("flags", "skinned", skinBone)
        m3Bone.setNamedBit("flags", "real", realBone)
        m3Bone.parent = -1
        m3Bone.location = self.createNullVector3AnimationReference(0.0, 0.0, 0.0)
        m3Bone.rotation = self.createNullQuaternionAnimationReference(x=0.0, y=0.0, z=0.0, w=1.0)
        m3Bone.scale = self.createNullVector3AnimationReference(1.0, 1.0, 1.0)
        m3Bone.ar1 = self.createNullUInt32AnimationReference(1)
        return m3Bone

    def initMaterials(self, model):
        standardMaterials = []
        materialReferences = model.materialReferences
        scene = self.scene
        
        for materialIndex, material in enumerate(scene.m3_materials):
            materialType = 1 # 1 = standard material
            materialReferences.append(self.createMaterialReference(materialIndex, materialType))
            standardMaterials.append(self.createMaterial(materialIndex, material))
        model.materialReferences = materialReferences 
        model.standardMaterials = standardMaterials
        
    def createMaterial(self, materialIndex, material):
        m3Material = m3.MAT_V15()
        m3Material.name = material.name
        m3Material.setNamedBit("flags", "unfogged", material.unfogged)
        m3Material.setNamedBit("flags", "twoSided", material.twoSided)
        m3Material.setNamedBit("flags", "unshaded", material.unshaded)
        m3Material.setNamedBit("flags", "noShadowsCast", material.noShadowsCast)
        m3Material.setNamedBit("flags", "noHitTest", material.noHitTest)
        m3Material.setNamedBit("flags", "noShadowsReceived", material.noShadowsReceived)
        m3Material.setNamedBit("flags", "depthPrepass", material.depthPrepass)
        m3Material.setNamedBit("flags", "useTerrainHDR", material.useTerrainHDR)
        m3Material.setNamedBit("flags", "splatUVfix", material.splatUVfix)
        m3Material.setNamedBit("flags", "softBlending", material.softBlending)
        m3Material.setNamedBit("flags", "forParticles", material.forParticles)
        m3Material.setNamedBit("unknownFlags", "unknownFlag0x1", material.unknownFlag0x1)
        m3Material.setNamedBit("unknownFlags", "unknownFlag0x4", material.unknownFlag0x4)
        m3Material.setNamedBit("unknownFlags", "unknownFlag0x8", material.unknownFlag0x8)
        m3Material.setNamedBit("unknownFlags", "unknownFlag0x200", material.unknownFlag0x200)
        m3Material.blendMode = int(material.blendMode)
        m3Material.priority = material.priority
        m3Material.specularity = material.specularity
        m3Material.specMult = material.specMult
        m3Material.emisMult = material.emisMult
        
        layerIndex = 0
        for layer, layerFieldName in zip(material.layers, shared.materialLayerFieldNames):
            animPathPrefix = "m3_materials[%s].layers[%s]." % (materialIndex, layerIndex)
            m3Layer = self.createMaterialLayer(layer, animPathPrefix)
            setattr(m3Material, layerFieldName, [m3Layer])
            layerIndex += 1

        m3Material.layerBlendType = int(material.layerBlendType)
        m3Material.emisBlendType = int(material.emisBlendType)
        m3Material.specType = int(material.specType)
        m3Material.unknownAnimationRef1 = self.createNullUInt32AnimationReference(0)
        m3Material.unknownAnimationRef2 = self.createNullUInt32AnimationReference(0)
        return m3Material

    def createMaterialLayer(self, layer, animPathPrefix):
        m3Layer = m3.LAYRV22()
        m3Layer.imagePath = layer.imagePath
        transferer = BlenderToM3DataTransferer(exporter=self, m3Object=m3Layer, blenderObject=layer, animPathPrefix=animPathPrefix, actionOwnerName=self.scene.name, actionOwnerType=actionTypeScene)
        transferer.transferAnimatableColor("color")
        m3Layer.setNamedBit("flags", "textureWrapX", layer.textureWrapX)
        m3Layer.setNamedBit("flags", "textureWrapY", layer.textureWrapY)
        m3Layer.setNamedBit("flags", "colorEnabled", layer.colorEnabled)
        transferer.transferInt("uvChannel")
        m3Layer.setNamedBit("alphaFlags", "alphaAsTeamColor", layer.alphaAsTeamColor)
        m3Layer.setNamedBit("alphaFlags", "alphaOnly", layer.alphaOnly)
        m3Layer.setNamedBit("alphaFlags", "alphaBasedShading", layer.alphaBasedShading)
        transferer.transferAnimatableFloat("brightMult")
        transferer.transferAnimatableFloat("brightMult2")
        m3Layer.unknown6 = self.createNullUInt32AnimationReference(0)
        m3Layer.unknown7 = self.createNullVector2AnimationReference(0.0, 0.0)
        m3Layer.unknown8 = self.createNullInt16AnimationReference(0)
        m3Layer.uvOffset = self.createNullVector2AnimationReference(0.0, 0.0)
        m3Layer.uvAngle = self.createNullVector3AnimationReference(0.0, 0.0, 0.0)
        m3Layer.uvTiling = self.createNullVector2AnimationReference(1.0, 1.0)
        m3Layer.uvTiling = self.createNullVector2AnimationReference(1.0, 1.0)
        m3Layer.unknown9 = self.createNullUInt32AnimationReference(0)
        m3Layer.unknown10 = self.createNullFloatAnimationReference(1.0)
        transferer.transferAnimatableFloat("brightness")
        return m3Layer

    def createNullVector2AnimationReference(self, x, y):
        animRef = m3.Vector2AnimationReference()
        animRef.header = self.createNullAnimHeader()
        animRef.initValue = self.createVector2(x, y)
        animRef.nullValue = self.createVector2(x, y)
        return animRef
        
    def createNullVector3AnimationReference(self, x, y, z):
        animRef = m3.Vector3AnimationReference()
        animRef.header = self.createNullAnimHeader()
        animRef.initValue = self.createVector3(x, y, z)
        animRef.nullValue = self.createVector3(x, y, z)
        return animRef
    
    def createNullQuaternionAnimationReference(self, x=0.0, y=0.0, z=0.0, w=1.0):
        animRef = m3.QuaternionAnimationReference()
        animRef.header = self.createNullAnimHeader()
        animRef.initValue = self.createQuaternion(x=x, y=y, z=z, w=w)
        animRef.nullValue = self.createQuaternion(x=x, y=y, z=z, w=w)
        return animRef
        
    def createNullInt16AnimationReference(self, value):
        animRef = m3.Int16AnimationReference()
        animRef.header = self.createNullAnimHeader()
        animRef.initValue = value
        animRef.nullValue = value
        return animRef
        
    def createNullUInt32AnimationReference(self, value):
        animRef = m3.UInt32AnimationReference()
        animRef.header = self.createNullAnimHeader()
        animRef.initValue = value
        animRef.nullValue = value
        return animRef
        
    def createNullFloatAnimationReference(self, initValue, nullValue=None):
        if nullValue == None:
            nullValue = initValue
        animRef = m3.FloatAnimationReference()
        animRef.header = self.createNullAnimHeader()
        animRef.initValue = initValue
        animRef.nullValue = nullValue
        return animRef
    
    def createNullAnimHeader(self):
        animRefHeader = m3.AnimationReferenceHeader()
        animRefHeader.flags = 0
        animRefHeader.animFlags = 0
        animRefHeader.animId = self.createUniqueAnimId()
        return animRefHeader
        
    def createUniqueAnimId(self):
        self.generatedAnimIdCounter += 1 # increase first since we don't want to use 0 as animation id
        return self.generatedAnimIdCounter
    
    def createMaterialReference(self, materialIndex, materialType):
        materialReference = m3.MATMV0()
        materialReference.matType = materialType
        materialReference.matIndex = materialIndex
        return materialReference

    def createEmptyDivision(self):
        division = m3.DIV_V2()
        division.faces = []
        division.regions = []
        division.bat = []
        division.msec = [self.createEmptyMSec()]
        return division
    
    def createEmptyMSec(self, minX=0.0, minY=0.0, minZ=0.0, maxX=0.0, maxY=0.0, maxZ=0.0, radius=0.0):
        msec = m3.MSECV1()
        msec.boundingsAnimation = self.createDummyBoundingsAnimation(minX, minY, minZ, maxX, maxY, maxZ, radius)
        return msec
    
    def createDummyBoundingsAnimation(self, minX=0.0, minY=0.0, minZ=0.0, maxX=0.0, maxY=0.0, maxZ=0.0, radius=0.0):
        boundingsAnimRef = m3.BNDSV0AnimationReference()
        animHeader = m3.AnimationReferenceHeader()
        animHeader.flags = 0x0
        animHeader.animFlags = 0x0
        animHeader.animId = 0x1f9bd2 # boudings seem to have always this id
        #TODO make sure the animID is unique
        boundingsAnimRef.header = animHeader
        boundingsAnimRef.initValue = self.createBoundings(minX, minY, minZ, maxX, maxY, maxZ, radius)
        boundingsAnimRef.nullValue = self.createBoundings(minX, minY, minZ, maxX, maxY, maxZ, radius)
        return boundingsAnimRef
    
    def createBoundings(self, minX=0.0, minY=0.0, minZ=0.0, maxX=0.0, maxY=0.0, maxZ=0.0, radius=0.0):
        boundings = m3.BNDSV0()
        boundings.min = self.createVector3(minX, minY, minZ)
        boundings.max = self.createVector3(maxX, maxY, maxZ)
        boundings.radius = radius
        return boundings
        
    def createAlmostEmptyBoundingsWithRadius(self, r):
        boundings = m3.BNDSV0()
        boundings.min = self.createVector3(0.0,0.0,0.0)
        epsilon = 9.5367431640625e-07
        boundings.max = self.createVector3(epsilon, epsilon, epsilon)
        boundings.radius = float(r)
        return boundings

    def createVector4(self, x, y, z, w):
        v = m3.Vector4()
        v.x = x
        v.y = y
        v.z = z
        v.w = w
        return v
    
    def createQuaternion(self, x, y, z, w):
        q = m3.QUATV0()
        q.x = x
        q.y = y
        q.z = z
        q.w = w
        return q
    
    def createColor(self, r, g, b, a):
        color = m3.COLV0()
        color.red = self.toM3ColorComponent(r)
        color.green = self.toM3ColorComponent(g)
        color.blue = self.toM3ColorComponent(b)
        color.alpha = self.toM3ColorComponent(a)
        return color

    def createVector3(self, x, y, z):
        v = m3.VEC3V0()
        v.x = x
        v.y = y
        v.z = z
        return v
    
    def createVector2(self, x, y):
        v = m3.VEC2V0()
        v.x = x
        v.y = y
        return v
        
    def createVector3FromBlenderVector(self, blenderVector):
        return self.createVector3(blenderVector.x, blenderVector.y, blenderVector.z)
    
    def createVector4FromBlenderVector(self, blenderVector):
        return self.createVector4(blenderVector[0], blenderVector[1], blenderVector[2], blenderVector[3])

    def createQuaternionFromBlenderQuaternion(self, q):
        return self.createQuaternion(x=q.x, y=q.y, z=q.z, w=q.w)
    
    def createIdentityMatrix(self):
        matrix = m3.Matrix44()
        matrix.x = self.createVector4(1.0, 0.0, 0.0, 0.0)
        matrix.y = self.createVector4(0.0, 1.0, 0.0, 0.0)
        matrix.z = self.createVector4(0.0, 0.0, 1.0, 0.0)
        matrix.w = self.createVector4(0.0, 0.0, 0.0, 1.0)
        return matrix
        
    def determineAnimationActionTuplesFor(self, actionOwnerName, actionOwnerType):
        animationActionTuples = []
        scene = self.scene
        for animation in scene.m3_animations:
            for assignedAction in animation.assignedActions:
                if actionOwnerName == assignedAction.targetName:
                    actionName = assignedAction.actionName
                    action = bpy.data.actions.get(actionName)
                    if action == None:
                        print("Warning: The action %s was referenced by name but does no longer exist" % assignedAction.actionName)
                    else:
                        if action.id_root == actionOwnerType:
                            animationActionTuples.append((animation, action))
        return animationActionTuples

        
    def getAllFramesOf(self, animation):
        #TODO Does the end frame need to be included?
        return range(animation.startFrame, animation.endFrame)
        
    def allFramesToMSValues(self, frames):
        timeValues = []
        for frame in frames:
            timeInMS = self.frameToMS(frame)
            timeValues.append(timeInMS)
        return timeValues
    
    def getNoneOrValuesFor(self, action, animPath, curveArrayIndex, frames):
        values = []
        curve = self.findFCurveWithPathAndIndex(action, animPath, curveArrayIndex)
        if curve == None:
            return None
        for frame in frames:
            values.append(curve.evaluate(frame))
        return values
            
    def findFCurveWithPathAndIndex(self, action, animPath, curveArrayIndex):
        for curve in action.fcurves:
            if (curve.data_path == animPath) and (curve.array_index == curveArrayIndex):
                return curve
        return None

class BlenderToM3DataTransferer:
    
    def __init__(self, exporter, m3Object, blenderObject, animPathPrefix,  actionOwnerName, actionOwnerType):
        self.exporter = exporter
        self.m3Object = m3Object
        self.blenderObject = blenderObject
        self.animPathPrefix = animPathPrefix
        self.actionOwnerName = actionOwnerName
        self.actionOwnerType = actionOwnerType
        
        self.animationActionTuples = self.exporter.determineAnimationActionTuplesFor(actionOwnerName, actionOwnerType)
        
    def transferAnimatableColor(self, fieldName):
        animRef = m3.ColorAnimationReference()
        animRef.header = self.exporter.createNullAnimHeader()
        m3CurrentColor =  self.exporter.toM3Color(getattr(self.blenderObject, fieldName))
        animRef.initValue = m3CurrentColor
        animRef.nullValue = m3CurrentColor
        setattr(self.m3Object, fieldName, animRef)
        
        animId = animRef.header.animId
        animPath = self.animPathPrefix + fieldName
        
        for animation, action in self.animationActionTuples:
            frames = self.exporter.getAllFramesOf(animation)
            timeValuesInMS = self.exporter.allFramesToMSValues(frames)
            redValues = self.exporter.getNoneOrValuesFor(action, animPath, 0, frames)
            greenValues = self.exporter.getNoneOrValuesFor(action, animPath, 1, frames)
            blueValues = self.exporter.getNoneOrValuesFor(action, animPath, 2, frames)
            alphaValues = self.exporter.getNoneOrValuesFor(action, animPath, 2, frames)
            if (redValues != None) or (greenValues != None) or (blueValues != None) or (alphaValues != None):
                if redValues == None:
                    redValues = len(timeValuesInMS) * [m3CurrentColor.red]
                if greenValues == None:
                    greenValues = len(timeValuesInMS) * [m3CurrentColor.green]
                if blueValues == None:
                    blueValues = len(timeValuesInMS) * [m3CurrentColor.blue]
                if alphaValues == None:
                    alphaValues = len(timeValuesInMS) * [m3CurrentColor.alpha]
                colors = []
                for (r,g,b,a) in zip(redValues, greenValues, blueValues, alphaValues):
                    color = self.exporter.createColor(r=r, g=g, b=b, a=a)
                    colors.append(color)
                
                m3AnimBlock = m3.SDCCV0()
                m3AnimBlock.frames = timeValuesInMS
                m3AnimBlock.flags = 0
                m3AnimBlock.fend = self.exporter.frameToMS(animation.endFrame)
                m3AnimBlock.keys = colors
                
                animIdToAnimDataMap = self.exporter.nameToAnimIdToAnimDataMap[animation.name]
                animIdToAnimDataMap[animId] = m3AnimBlock
                animRef.header.flags = 1
                animRef.header.animFlags = shared.animFlagsForAnimatedProperty
        #TODO Optimization: Remove keyframes that can be calculated by interpolation   

    def transferAnimatableSingleFloatOrInt(self, fieldName, animRefClass, animRefFlags, animDataClass, convertMethod):
        animRef = animRefClass()
        animRef.header = self.exporter.createNullAnimHeader()
        currentValue =  getattr(self.blenderObject, fieldName)
        animRef.initValue = currentValue
        animRef.nullValue = currentValue
        
        animId = animRef.header.animId
        animPath = self.animPathPrefix + fieldName
        
        for animation, action in self.animationActionTuples:
            frames = self.exporter.getAllFramesOf(animation)
            timeValuesInMS = self.exporter.allFramesToMSValues(frames)
            values = self.exporter.getNoneOrValuesFor(action, animPath, 0, frames)
            if values != None:
                convertedValues = []
                for value in values:
                    convertedValues.append(convertMethod(value))
                m3AnimBlock = animDataClass()
                m3AnimBlock.frames = timeValuesInMS
                m3AnimBlock.flags = 0
                m3AnimBlock.fend = self.exporter.frameToMS(animation.endFrame)
                m3AnimBlock.keys = convertedValues
                
                animIdToAnimDataMap = self.exporter.nameToAnimIdToAnimDataMap[animation.name]
                animIdToAnimDataMap[animId] = m3AnimBlock
                animRef.header.flags = animRefFlags
                animRef.header.animFlags = shared.animFlagsForAnimatedProperty
        #TODO Optimization: Remove keyframes that can be calculated by interpolation
        setattr(self.m3Object, fieldName, animRef)
   
        
    def transferAnimatableFloat(self, fieldName):
        def identity(value):
            return value
        self.transferAnimatableSingleFloatOrInt(fieldName, animRefClass=m3.FloatAnimationReference, animRefFlags=1, animDataClass=m3.SDR3V0,convertMethod=identity)
        

    def transferAnimatableInt16(self, fieldName):
        def toInt16Value(value):
            return min((1<<16)-1,  max(0, round(value)))
        self.transferAnimatableSingleFloatOrInt(fieldName, animRefClass=m3.Int16AnimationReference, animRefFlags=0, animDataClass=m3.SDS6V0, convertMethod=toInt16Value)

    def transferAnimatableUInt32(self, fieldName):
        #TODO Test this method once the purpose of an animated int32 field is known
        def toUInt32Value(value):
            return min((1<<32)-1,  max(0, round(value)))
        self.transferAnimatableSingleFloatOrInt(fieldName, animRefClass=m3.UInt32AnimationReference, animRefFlags=0, animDataClass=m3.FLAGV0, convertMethod=toUInt32Value)

    def transferAnimatableVector3(self, fieldName):
        animRef = m3.Vector3AnimationReference()
        animRef.header = self.exporter.createNullAnimHeader()
        currentBVector =  getattr(self.blenderObject, fieldName)
        animRef.initValue = self.exporter.createVector3FromBlenderVector(currentBVector)
        animRef.nullValue = self.exporter.createVector3FromBlenderVector(currentBVector)
        setattr(self.m3Object, fieldName, animRef)
        
        
        animId = animRef.header.animId
        animPath = self.animPathPrefix + fieldName
        
        for animation, action in self.animationActionTuples:
            frames = self.exporter.getAllFramesOf(animation)
            timeValuesInMS = self.exporter.allFramesToMSValues(frames)
            xValues = self.exporter.getNoneOrValuesFor(action, animPath, 0, frames)
            yValues = self.exporter.getNoneOrValuesFor(action, animPath, 1, frames)
            zValues = self.exporter.getNoneOrValuesFor(action, animPath, 2, frames)
            if (xValues != None) or (yValues != None) or (zValues != None):
                if xValues == None:
                    xValues = len(timeValuesInMS) * [currentBVector.x]
                if yValues == None:
                    yValues = len(timeValuesInMS) * [currentBVector.y]
                if zValues == None:
                    zValues = len(timeValuesInMS) * [currentBVector.z]
                vectors = []
                for (x,y,z) in zip(xValues, yValues, zValues):
                    vec = self.exporter.createVector3(x,y,z)
                    vectors.append(vec)
                
                m3AnimBlock = m3.SD3VV0()
                m3AnimBlock.frames = timeValuesInMS
                m3AnimBlock.flags = 0
                m3AnimBlock.fend = self.exporter.frameToMS(animation.endFrame)
                m3AnimBlock.keys = vectors
                
                animIdToAnimDataMap = self.exporter.nameToAnimIdToAnimDataMap[animation.name]
                animIdToAnimDataMap[animId] = m3AnimBlock
                animRef.header.flags = 1
                animRef.header.animFlags = shared.animFlagsForAnimatedProperty
        #TODO Optimization: Remove keyframes that can be calculated by interpolation
        
    def transferInt(self, fieldName):
        value = getattr(self.blenderObject, fieldName)
        setattr(self.m3Object, fieldName , value)
        
    def transferBoolToInt(self, fieldName):
        boolValue = getattr(self.blenderObject, fieldName)
        if boolValue:
            intValue = 1
        else:
            intValue = 0
        setattr(self.m3Object, fieldName , intValue)

    def transferFloat(self, fieldName):
        value = getattr(self.blenderObject, fieldName)
        setattr(self.m3Object, fieldName , value)
        
    def transferEnum(self, fieldName):
        value = getattr(self.blenderObject, fieldName)
        setattr(self.m3Object, fieldName , int(value))

        
def exportParticleSystems(scene, filename):
    exporter = Exporter()
    shared.setAnimationWithIndexToCurrentData(scene, scene.m3_animation_index)
    exporter.exportParticleSystems(scene, filename)
