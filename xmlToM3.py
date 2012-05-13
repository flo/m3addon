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

import struct
import sys
from generateM3Library import generateM3Library
generateM3Library()
from m3 import *
import xml.dom.minidom
from xml.dom.minidom import Node
import argparse
import os

def createSingleStructureElement(xmlNode, typeClass):
    createdObject = typeClass()
    for child in xmlNode.childNodes:
        if type(child) == xml.dom.minidom.Text:
            if not child.wholeText.isspace():
                raise Exception("Unexpected content \"%s\" within element %s", (child.wholeText, xmlNode.nodeName))
        else:
            fieldName = child.nodeName
            fieldTypeInfo = typeClass.getFieldTypeInfo(fieldName)
            o = createFieldContent(child,fieldName,fieldTypeInfo)
            setattr(createdObject, fieldName, o)
    return createdObject
                
        
def createFieldContent(xmlNode, fieldName, fieldTypeInfo):
    typeName = fieldTypeInfo.typeName
    fieldIsList =  fieldTypeInfo.isList
    if typeName == "CHARV0":
        return stringContentOf(xmlNode)
    elif (typeName == None and not fieldIsList):
        return hexToBytes(stringContentOf(xmlNode),xmlNode)
    elif typeName == "U8__V0":
        return bytearray(hexToBytes(stringContentOf(xmlNode),xmlNode))
    elif fieldIsList:
        return createElementList(xmlNode, fieldName, fieldTypeInfo.typeName, fieldTypeInfo.typeClass)
    else:
        return createSingleElement(xmlNode, fieldTypeInfo.typeName, fieldTypeInfo.typeClass)


def removeWhitespace(s):
    return s.translate({ord(" "):None,ord("\t"):None,ord("\r"):None,ord("\n"):None})

def hexToBytes(hexString, xmlNode):
    hexString = removeWhitespace(hexString)
    if hexString == "":
        return bytearray(0)
    if not hexString.startswith("0x"):
        raise Exception('hex string "%s" of node %s does not start with 0x' % (hexString,xmlNode.nodeName) )
    hexString = hexString[2:]
    return bytes([int(hexString[x:x+2], 16) for x in range(0, len(hexString),2)])

def stringContentOf(xmlNode):
    content = ""
    for child in xmlNode.childNodes:
        if child.nodeType == Node.TEXT_NODE:
            content += child.data
        else:
            raise Exception("Element %s contained childs of xml node type %s." % (xmlNode.nodeName,type(xmlNode)))
    return content

def createSingleElement(xmlNode, typeName, typeClass):
    if typeName in ["int32","int16","int8","uint32", "uint16", "uint8", "I32_V0","I16_V0", "I8__V0", "U32_V0", "U16_V0", "U8__V0"]:
        return int(stringContentOf(xmlNode), 0)
    elif typeName in ["float","REALV0"]:
        return float(stringContentOf(xmlNode))
    elif typeClass != None:
        return createSingleStructureElement(xmlNode, typeClass)
    else:
        raise Exception("%(nodeName)s of type %(typeName)s has no class" % {"nodeName":xmlNode.nodeName,"typeName":typeName})
        
def createElementList(xmlNode, parentName, typeName, typeClass):
    expectedChildNames = parentName + "-element"
    child = xmlNode.firstChild
    createdList = []
    for child in xmlNode.childNodes:
        if type(child) == xml.dom.minidom.Text:
            if not child.data.isspace():
                raise Exception("Unexpected content \"%s\" within element %s", (child.wholeText, xmlNode.nodeName))
        else:
            if (child.nodeName != expectedChildNames):
                raise Exception("Unexpected child \"%s\" within element %s", (child.nodeName, xmlNode.nodeName))
            o = createSingleElement(child, typeName, typeClass)
            createdList.append(o)
        
    return createdList
        


def convertFile(inputFilePath, outputDirectory):
    if outputDirectory != None:
        fileName = os.path.basename(inputFilePath)
        outputFilePath = os.path.join(outputDirectory, fileName[:-4])
    else:
        outputFilePath = inputFilePath[:-4]
    print("Converting %s -> %s" % (inputFilePath, outputFilePath))
    doc = xml.dom.minidom.parse(inputFilePath)
    modelElement = doc.firstChild
    model = createSingleElement(modelElement, "MODLV23", MODLV23)
    saveAndInvalidateModel(model, outputFilePath)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('path', nargs='+', help="Either a *.m3.xml file or a directory with *.m3.xml files generated with m3ToXml.py")
    parser.add_argument('--output-directory', '-o', help='Directory in which m3 files will be placed')
    args = parser.parse_args()
    outputDirectory = args.output_directory
    if outputDirectory != None and not os.path.isdir(outputDirectory):
        sys.stderr.write("%s is not a directory" % outputDirectory)
        sys.exit(2)
    for filePath in args.path:
        if not (filePath.endswith(".m3.xml") or os.path.isdir(filePath)):
            sys.stderr.write("%s neither a directory nor does it end with '.m3.xml'\n" % filePath)
            sys.exit(2)
    counter = 0
    for filePath in args.path:
        if os.path.isdir(filePath):
            for fileName in os.listdir(filePath):
                inputFilePath = os.path.join(filePath, fileName)
                if fileName.endswith(".m3.xml"):
                     convertFile(inputFilePath, outputDirectory)
                     counter += 1
        else:
            convertFile(filePath, outputDirectory)
            counter += 1
    if counter == 1:
        print("Converted %d file from .m3.xml to .m3" % counter)
    else:
        print("Converted %d files from .m3.xml to .m3" % counter)
