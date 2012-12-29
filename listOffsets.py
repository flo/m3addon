#!/usr/bin/python3
# -*- coding: utf-8 -*-

import generateM3Library
import sys
import xml.dom.minidom
from xml.dom.minidom import Node
import re

class FieldOffsetPrinter(generateM3Library.Visitor):
    def visitClassStart(self, generalDataMap, classDataMap):
        self.nextFieldOffset = 0
    
    def visitFieldStart(self, generalDataMap, classDataMap, fieldDataMap):
        offset = self.nextFieldOffset
        out = generalDataMap["out"]
        fieldName = fieldDataMap["fieldName"]
        fullName = classDataMap["fullName"]
        out.write("Structure %(fullName)s: Offset %(offset)d: %(fieldName)s \n" % {"fullName": fullName, "fieldName":fieldName, "offset": offset});
        self.nextFieldOffset += fieldDataMap["fieldSize"]


doc = xml.dom.minidom.parse("structures.xml")

generalDataMap = {}

# first run is only for determing the complete list of known structures
firstRunVisitors = [
    generateM3Library.StructureAttributesReader(),
    generateM3Library.FullNameDeterminer(),
    generateM3Library.KnownStructuresListDeterminer(),
    generateM3Library.KnownTagsListDeterminer()]
generateM3Library.visitStructresDomWith(doc, firstRunVisitors, generalDataMap)

generalDataMap["out"] = sys.stdout

secondRunVisitors = [
    generateM3Library.StructureAttributesReader(),
    generateM3Library.StructureDescriptionReader(),
    generateM3Library.FullNameDeterminer(),
    generateM3Library.PrimitiveStructureDetector(),
    generateM3Library.FieldAttributesReader(), 
    generateM3Library.FieldIndexDeterminer(),
    generateM3Library.BitAttributesReader(),
    generateM3Library.DuplicateFieldNameChecker(), 
    generateM3Library.SizeDeterminer(),
    FieldOffsetPrinter()
    ]
generateM3Library.visitStructresDomWith(doc, secondRunVisitors, generalDataMap)


