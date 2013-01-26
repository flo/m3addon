#!/usr/bin/python3
# -*- coding: utf-8 -*-

from . import m3
import sys
import argparse
import math

def normalize(x, y, z):
    length = math.sqrt(x*x + y*y + z*z)
    if length == 0:
        return 0.0, 0.0, 0.0
    return (x / length, y / length, z / length)

def uvIntToFloat(m3UVCoordinate):
    return (m3UVCoordinate.x / 2048.0, 1 - m3UVCoordinate.y / 2048.0)


def recalculateTangentsOfFaces(m3VerticesToUpdate, faces):
    for face in faces:
        vertex0 = m3VerticesToUpdate[face[0]]
        vertex1 = m3VerticesToUpdate[face[1]]
        vertex2 = m3VerticesToUpdate[face[2]]
        
        uv0 = uvIntToFloat(vertex0.uv0)
        uv1 = uvIntToFloat(vertex1.uv0)
        uv2 = uvIntToFloat(vertex2.uv0)
        
        u0 = uv0[0]
        u1 = uv1[0]
        u2 = uv2[0]
        v0 = uv0[1]
        v1 = uv1[1]
        v2 = uv2[1]
        
        deltaU1 = u1 - u0
        deltaU2 = u2 - u0
        deltaV1 = v1 - v0
        deltaV2 = v2 - v0
        
        e1x = vertex1.position.x - vertex0.position.x
        e1y = vertex1.position.y - vertex0.position.y
        e1z = vertex1.position.z - vertex0.position.z
        
        e2x = vertex2.position.x - vertex0.position.x
        e2y = vertex2.position.y - vertex0.position.y
        e2z = vertex2.position.z - vertex0.position.z
        
        factor = 1.0 / (deltaU1*deltaV2 - deltaU2*deltaV1) 
        tx = (deltaV2 * e1x - deltaV1 * e2x)
        ty = (deltaV2 * e1y - deltaV1 * e2y)
        tz = (deltaV2 * e1z - deltaV1 * e2z)
        tx, ty, tz = normalize(tx, ty, tz)

        bx = (- deltaU2 * e1x + deltaU1 * e2x)
        by = (- deltaU2 * e1y + deltaU1 * e2y)
        bz = (- deltaU2 * e1z + deltaU1 * e2z)
        bx, by, bz = normalize(bx, by, bz)

        print(" deltaU1 %s" % deltaU1)
        print(" deltaU2 %s" % deltaU2)
        print(" deltaV1 %s" % deltaV1)
        print(" deltaV2 %s" % deltaV2)
        print(" v0 stored t = (%.2f %.2f %.2f)" % (vertex0.tangent.x, vertex0.tangent.y, vertex0.tangent.z))
        print(" v1 stored t = (%.2f %.2f %.2f)" % (vertex1.tangent.x, vertex1.tangent.y, vertex1.tangent.z))
        print(" v2 stored t = (%.2f %.2f %.2f)" % (vertex2.tangent.x, vertex2.tangent.y, vertex2.tangent.z))
        print("calculated t = (%.2f %.2f %.2f)" % (tx, ty, tz))
        print("calculated b = (%.2f %.2f %.2f)" % (bx, by, bz))
        print()
        
        vertex0.tangent.x = tx
        vertex0.tangent.y = ty
        vertex0.tangent.z = tz
        vertex1.tangent.x = tx
        vertex1.tangent.y = ty
        vertex1.tangent.z = tz
        vertex2.tangent.x = tx
        vertex2.tangent.y = ty
        vertex2.tangent.z = tz
        
    #for vertexIndex, m3Vertex in enumerate(m3VerticesToUpdate):
        #m3ToXml.printObject(out=sys.stdout, level=0, name="v%d" %vertexIndex, value=m3Vertex)

def recalculateTangentsOfDivisions(m3VerticesToUpdate, divisions):
    faces = []
    for division in divisions:
        divisionFaceIndices = division.faces
        for m3Object in division.objects:
            region = division.regions[m3Object.regionIndex]
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
    recalculateTangentsOfFaces(m3VerticesToUpdate, faces)

def recalculateTangentsOfModel(model):
    vertexClassName = "VertexFormat" + hex(model.vFlags)
    vertexStructureDescription = m3.structures[vertexClassName].getVersion(0)
    numberOfVertices = round(len(model.vertices) / vertexStructureDescription.size)
    m3VerticesToUpdate = vertexStructureDescription.createInstances(buffer=model.vertices, count=numberOfVertices)

    recalculateTangentsOfDivisions(m3VerticesToUpdate, model.divisions)

def convert(inputPath, outputPath):
    model = m3.loadModel(inputPath)
    recalculateTangentsOfModel(model)
    m3.saveAndInvalidateModel(model, outputPath)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert Starcraft II m3 models to xml format.')
    parser.add_argument('inputPath',  help="A *.m3 file")
    parser.add_argument('outputPath', help="A *.m3 file")
    args = parser.parse_args()
    
    convert(args.inputPath, args.outputPath)