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

materialLayerFieldNames = ["diffuseLayer", "decalLayer", "specularLayer", "selfIllumLayer",
    "emissiveLayer", "reflectionLayer", "evioLayer", "evioMaskLayer", "alphaMaskLayer", 
    "bumpLayer", "heightLayer", "layer12", "layer13"]

materialLayerNames = ["Diffuse", "Decal", "Specular", "Self Illumination", 
    "Emissive", "Reflection", "Evio", "Evio Mask", "Alpha Mask", "Bump", "Height", "Layer 12", "Layer 13"]


rotFixMatrix = mathutils.Matrix((( 0, 1, 0, 0,),
                                 (-1, 0, 0, 0),
                                 ( 0, 0, 1, 0),
                                 ( 0, 0, 0, 1)))
rotFixMatrixInverted = rotFixMatrix.transposed()

animFlagsForAnimatedProperty = 6

star2ParticlePrefix = "Star2Part"


def toValidBoneName(name):
    maxLength = 31
    return name[:maxLength]    

def boneNameForPartileSystem(boneSuffix):
    return toValidBoneName(star2ParticlePrefix + boneSuffix)

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

def sqr(x):
    return x*x

def smoothQuaternionTransition(previousQuaternion, quaternionToFix):
    sumOfSquares =  sqr(quaternionToFix.x - previousQuaternion.x) + sqr(quaternionToFix.y - previousQuaternion.y) + sqr(quaternionToFix.z - previousQuaternion.z) + sqr(quaternionToFix.w - previousQuaternion.w)
    sumOfSquaresMinus =  sqr(-quaternionToFix.x - previousQuaternion.x) + sqr(-quaternionToFix.y - previousQuaternion.y) + sqr(-quaternionToFix.z - previousQuaternion.z) + sqr(-quaternionToFix.w - previousQuaternion.w)
    if sumOfSquaresMinus < sumOfSquares:
        quaternionToFix.negate()

def vectorInterpolationFunction(leftInterpolationValue, rightInterpolationValue, rightFactor):
    return leftInterpolationValue.lerp(rightInterpolationValue, rightFactor)

def quaternionInterpolationFunction(leftInterpolationValue, rightInterpolationValue, rightFactor):
    return leftInterpolationValue.slerp(rightInterpolationValue, rightFactor)
    
def vectorsAlmostEqual(vectorExpected, vectorActual):
    diff = vectorExpected - vectorActual
    return diff.length < 0.00001
    
def quaternionsAlmostEqual(q0, q1):
    distanceSqr = sqr(q0.x-q1.x)+sqr(q0.y-q1.y)+sqr(q0.z-q1.z)+sqr(q0.w-q1.w)
    return distanceSqr < sqr(0.00001)

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