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

def setAnimationWithIndexToCurrentData(scene, animationIndex):
    if (animationIndex < 0) or (animationIndex >= len(scene.m3_animations)):
        return
    animation = scene.m3_animations[animationIndex]
    animation.startFrame = scene.frame_start
    animation.endFrame = scene.frame_end
    while len(animation.assignedActions) > 0:
        animation.assignedActions.remove(0)

    for targetObject in bpy.data.objects:
        if targetObject.animation_data != None:
            assignedAction = animation.assignedActions.add()
            assignedAction.targetName = targetObject.name
            if targetObject.animation_data.action != None:
                assignedAction.actionName = targetObject.animation_data.action.name
    if scene.animation_data != None:
        assignedAction = animation.assignedActions.add()
        assignedAction.targetName = scene.name
        assignedAction.actionName = scene.animation_data.action.name
