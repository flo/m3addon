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

import xml.dom.minidom
from xml.dom.minidom import Node
import re

class Visitor:
    def visitStart(self, generalDataMap):
        pass
    def visitClassStart(self, generalDataMap, classDataMap):
        pass
    def visitFieldStart(self, generalDataMap, classDataMap, fieldDataMap):
        pass
    def visitFieldBit(self, generalDataMap, classDataMap, fieldDataMap, bitDataMap):
        pass
    def visitFieldEnd(self, generalDataMap, classDataMap, fieldDataMap):
        pass
    def visitClassEnd(self, generalDataMap, classDataMap):
        pass
    def visitEnd(self, generalDataMap):
        pass

class HeaderAdder(Visitor):
    text= """\
#!/usr/bin/python3
# -*- coding: utf-8 -*-
\"\"\" 
IMPORTANT: This is a automatically generated file. 
IMPORTANT: Do not modify!
\"\"\"
import struct
from sys import stderr

class NoSuchAttributeException(Exception):
    def __init__(self, attribute):
        self.msg = "%s is not a known attribute." % attribute
        
class UnexpectedTagException(Exception):
    def __init__(self, tagName):
        pass

def unpackTag(s):
    if s[3] == 0:
        return chr(s[2]) + chr(s[1]) + chr(s[0])
    else:
        return chr(s[3]) + chr(s[2]) + chr(s[1]) + chr(s[0])

def packTag(s):
    if len(s) == 4:
        return (s[3] + s[2] + s[1] + s[0]).encode("ascii")
    else:
        return (s[2] + s[1] + s[0]).encode("ascii") + b"\\x00"

def increaseToValidSectionSize(size):
    blockSize = 16
    incompleteBlockBytes = (size % blockSize)
    if incompleteBlockBytes != 0:
        missingBytesToCompleteBlock = blockSize - incompleteBlockBytes
        return size + missingBytesToCompleteBlock
    else:
        return size
            
def rawBytesToHex(rawBytes):
    \"\"\" for debug purposes\"\"\"
    s = ""
    for i in range(0, len(rawBytes)):
        rawByte = rawBytes[i]
        s += hex(rawByte)
    return s
    
class Section:
    \"\"\"Has fields indexEntry and contentClass and sometimes also the fields rawBytes and content \"\"\"
    
    def __init__(self):
        self.timesReferenced = 0
    
    def determineContentField(self):
        indexEntry = self.indexEntry
        self.content = self.contentClass.createInstances(rawBytes=self.rawBytes, count=indexEntry.repetitions)

    def determineFieldRawBytes(self):
        minRawBytes = self.contentClass.rawBytesForOneOrMore(oneOrMore=self.content)
        sectionSize = increaseToValidSectionSize(len(minRawBytes))
        if len(minRawBytes) == sectionSize:
            self.rawBytes = minRawBytes
        else:
            rawBytes = bytearray(sectionSize)
            rawBytes[0:len(minRawBytes)] = minRawBytes
            for i in range(len(minRawBytes),sectionSize):
                rawBytes[i] = 0xaa
            self.rawBytes = rawBytes
    def resolveReferences(self, sections):
        self.contentClass.resolveReferencesOfOneOrMore(self.content, sections)

class FieldTypeInfo:
    \"\"\" Stores information of the type of a field:\"\"\"
    def __init__(self, typeName, typeClass, isList):
        self.typeName = typeName
        self.typeClass = typeClass
        self.isList = isList

def resolveRef(ref, sections, expectedType, variable):
    if ref.entries == 0:
        if expectedType == None:
            return []
        else:
            return expectedType.createEmptyArray()
    
    referencedSection = sections[ref.index]
    referencedSection.timesReferenced += 1
    indexEntry = referencedSection.indexEntry
    
    if indexEntry.repetitions < ref.entries:
        raise Exception("%s references more elements then there actually are" % variable)

    referencedObject = referencedSection.content
    if expectedType != None:
        expectedTagName = expectedType.tagName
        actualTagName = indexEntry.tag
        if actualTagName != expectedTagName:
            raise Exception("Expected ref %s point to %s, but it points to %s" % (variable, expectedTagName, actualTagName))
        expectedTagVersion = expectedType.tagVersion
        actualTagVersion = indexEntry.version
        if actualTagName != expectedTagName:
            raise Exception("Expected ref %s point to %s in version %s, but it points version %s" % (variable, expectedTagName,expectedTagVersion, actualTagVersion))

    else:
        raise Exception("Field %s can be marked as a reference pointing to %sV%s" % (variable, indexEntry.tag,indexEntry.version))
    return referencedObject

"""
    def visitStart(self, generalDataMap):
        generalDataMap["out"].write(HeaderAdder.text)

class StructureAttributesReader(Visitor):
    def visitClassStart(self, generalDataMap, classDataMap):
        xmlNode = classDataMap["xmlNode"]
        if xmlNode.hasAttribute("name"):
            classDataMap["tagName"] = xmlNode.getAttribute("name")
        else:
            raise Exception("There is a structure without a name attribute")
        if xmlNode.hasAttribute("version"):
            classDataMap["tagVersion"] = xmlNode.getAttribute("version")
        else:
            classDataMap["tagVersion"] = None
            
        if xmlNode.hasAttribute("size"):
            classDataMap["specifiedSize"] = int(xmlNode.getAttribute("size"))
        else:
            classDataMap["specifiedSize"] = None

class StructureDescriptionReader(Visitor):
    def visitClassStart(self, generalDataMap, classDataMap):
        xmlNode = classDataMap["xmlNode"]
        tagDescriptionNodes = xmlNode.getElementsByTagName("description")
        if len(tagDescriptionNodes) != 1:
            raise Exception("Tag %s has not exactly one description node",fullName)
        tagDescriptionNode = tagDescriptionNodes[0]
        tagDescription = ""
        for descriptionChild in tagDescriptionNode.childNodes:
            if descriptionChild.nodeType == Node.TEXT_NODE:
                tagDescription += descriptionChild.data
        classDataMap["description"] = tagDescription


class FullNameDeterminer(Visitor):
    def visitClassStart(self, generalDataMap, classDataMap):
        tagName = classDataMap["tagName"]
        tagVersion = classDataMap["tagVersion"]
        if tagVersion != None:
            classDataMap["fullName"] = "%sV%s" % (tagName, tagVersion)
        else:
            classDataMap["fullName"] = tagName

class KnownStructuresListDeterminer(Visitor):
    def visitStart(self, generalDataMap):
        generalDataMap["knownStructs"] = set()
    def visitClassEnd(self, generalDataMap, classDataMap):
        fullName = classDataMap["fullName"]
        generalDataMap["knownStructs"].add(fullName)

class PrimitiveStructureDetector(Visitor):
    def visitClassStart(self, generalDataMap, classDataMap):
        fullName = classDataMap["fullName"]
        classDataMap["primitive"] = (fullName in ["CHARV0", "U8__V0", "REALV0", "I16_V0", "U16_V0", "I32_V0", "U32_V0"])


class FieldAttributesReader(Visitor):
    def visitFieldStart(self, generalDataMap, classDataMap, fieldDataMap):
        xmlNode = fieldDataMap["xmlNode"]
        if xmlNode.hasAttribute("name"):
             fieldDataMap["fieldName"] = xmlNode.getAttribute("name")
        else:
            fullName = classDataMap["fullName"]
            raise Exception("There is a field in %s without a name attribute" % fullName)
        
        if xmlNode.hasAttribute("type"):
            fieldDataMap["typeString"] = xmlNode.getAttribute("type")
        else:
            fieldDataMap["typeString"] = None
        
        if xmlNode.hasAttribute("refTo"):
            fieldDataMap["refTo"] = xmlNode.getAttribute("refTo")
        else:
            fieldDataMap["refTo"] = None

        if xmlNode.hasAttribute("offset"):
            fieldDataMap["specifiedOffsetString"] = xmlNode.getAttribute("offset")
        else:
            fieldDataMap["specifiedOffsetString"] = None

        if xmlNode.hasAttribute("size"):
            fieldDataMap["specifiedFieldSize"] = int(xmlNode.getAttribute("size"))
        else:
            fieldDataMap["specifiedFieldSize"] = None

        if xmlNode.hasAttribute("expected-value"):
            fieldDataMap["expectedValueString"] = xmlNode.getAttribute("expected-value")
        else:
            fieldDataMap["expectedValueString"] = None
            
        if xmlNode.hasAttribute("default-value"):
            fieldDataMap["defaultValueString"] = xmlNode.getAttribute("default-value")
        else:
            fieldDataMap["defaultValueString"] = None
            
class FieldOffsetChecker(Visitor):
    def visitClassStart(self, generalDataMap, classDataMap):
        self.nextFieldOffset = 0
    
    def visitFieldStart(self, generalDataMap, classDataMap, fieldDataMap):
        offset = self.nextFieldOffset
        specifiedOffsetString = fieldDataMap["specifiedOffsetString"]
        if specifiedOffsetString != None:
            if specifiedOffsetString == "":
                stderr.write("Field %s of %s has an empty offset. The calculated offset is %d." % (fieldName, fullName, offset));
            else:
                specifiedOffset = int(specifiedOffsetString)
                if specifiedOffset != offset:
                    fieldName = fieldDataMap["fieldName"]
                    fullName = classDataMap["fullName"]
                    raise Exception("Field %s of %s has been defined to start at '%d' but starts at '%d'" % (fieldName, fullName, specifiedOffset, offset));
        self.nextFieldOffset += fieldDataMap["fieldSize"]

class DuplicateFieldNameChecker(Visitor):
    def visitClassStart(self, generalDataMap, classDataMap):
        self.usedFieldNames = set()
    
    def visitFieldStart(self, generalDataMap, classDataMap, fieldDataMap):
        fieldName = fieldDataMap["fieldName"]
        fullName = classDataMap["fullName"]
        if fieldName in self.usedFieldNames:
            raise Exception("The structure %s contains multiple fields with the name %s" % (fullName, fieldName))
        self.usedFieldNames.add(fieldName)

class FieldIndexDeterminer(Visitor):
    def visitClassStart(self, generalDataMap, classDataMap):
        self.nextFieldIndex = 0
    
    def visitFieldStart(self, generalDataMap, classDataMap, fieldDataMap):
        fieldDataMap["fieldIndex"] = self.nextFieldIndex
        self.nextFieldIndex += 1

class BitAttributesReader(Visitor):

    def visitFieldBit(self, generalDataMap, classDataMap, fieldDataMap, bitDataMap):
        xmlNode = bitDataMap["xmlNode"]
        if xmlNode.hasAttribute("name"):
             bitDataMap["name"] = xmlNode.getAttribute("name")
        else:
            structureName = classDataMap["fullName"]
            fieldName = fieldDataMap["fieldName"]
            raise Exception("There is bit xml node in field %(fieldName)s of structure %(structureName)s without a name attribute" % {"fieldName": fieldName,"structureName":structureName})
        
        if xmlNode.hasAttribute("mask"):
            maskString = xmlNode.getAttribute("mask")
            if not re.match("0x[0-9]+", maskString):
                structureName = classDataMap["fullName"]
                fieldName = fieldDataMap["fieldName"]
                bitName = bitDataMap["name"]
                raise Exception("The bit %(bitName)s of %(structureName)s.%(fieldName)s has an invalid mask attribute" % {"fieldName": fieldName,"structureName":structureName,"bitName":bitName})

            bitDataMap["mask"] = int(maskString,0)
        else:
            structureName = classDataMap["fullName"]
            fieldName = fieldDataMap["fieldName"]
            raise Exception("There is bit xml node in field %(fieldName)s of structure %(structureName)s without a mask attribute" % {"fieldName": fieldName,"structureName":structureName})

class QuotedFieldsDeterminer(Visitor):
    def visitClassStart(self, generalDataMap, classDataMap):
        self.quotedFields = ""
    
    def visitFieldStart(self, generalDataMap, classDataMap, fieldDataMap):
        fieldIndex = fieldDataMap["fieldIndex"]
        fieldName = fieldDataMap["fieldName"]
        if fieldIndex > 0:
            self.quotedFields += ", "
        self.quotedFields += '"%s"' % fieldName

    def visitClassEnd(self, generalDataMap, classDataMap):
        classDataMap["quotedFields"] = self.quotedFields

class ClassHeaderAdder(Visitor):
    template = """
class %(fullName)s:
    \"\"\"%(description)s\"\"\"
"""
    def visitClassEnd(self, generalDataMap, classDataMap):
        fullName = classDataMap["fullName"]
        description = classDataMap["description"]
        text = ClassHeaderAdder.template % {"fullName": fullName, "description":description}
        generalDataMap["out"].write(text)
        
class FullNameConstantAdder(Visitor):
    def visitClassEnd(self, generalDataMap, classDataMap):
        version = classDataMap["tagVersion"]
        if version != None:
            fullName = classDataMap["fullName"]
            text = '    fullName = "%(fullName)s"\n' % {"fullName": fullName}
            generalDataMap["out"].write(text)
            
class TagNameConstantAdder(Visitor):
    def visitClassEnd(self, generalDataMap, classDataMap):
        tagName = classDataMap["tagName"]
        text = '    tagName = "%(tagName)s"\n' % {"tagName": tagName}
        generalDataMap["out"].write(text)

class VersionConstantAdder(Visitor):
    def visitClassEnd(self, generalDataMap, classDataMap):
        version = classDataMap["tagVersion"]
        if version != None:
            text = "    tagVersion = %(version)s\n" % {"version": version}
            generalDataMap["out"].write(text)

class FieldsConstantAdder(Visitor):
    def visitClassEnd(self, generalDataMap, classDataMap):
        quotedFields = classDataMap["quotedFields"]
        text = "    fields = [%(quotedFields)s]\n" % {"quotedFields": quotedFields}
        generalDataMap["out"].write(text)

class SetAttributesMethodAdder(Visitor):
    template = """
    def __setattr__(self, name, value):
        if name in [%(quotedFields)s]:
            object.__setattr__(self, name, value)
        else:
            raise NoSuchAttributeException(name)
    """
    def visitClassEnd(self, generalDataMap, classDataMap):
        quotedFields = classDataMap["quotedFields"]
        primitive = classDataMap["primitive"]
        if not primitive:
            text = SetAttributesMethodAdder.template % {"quotedFields": quotedFields}
            generalDataMap["out"].write(text)

class ToStringMethodAdder(Visitor):
    template = """
    def __str__(self):
        s = "{"
        first = True
        for key in [%(quotedFields)s]:
            if first:
                first = False
            else:
                s += ","
            s += key + ":" + str(self.__dict__[key])
        s += "}"
        return s
    """
    def visitClassEnd(self, generalDataMap, classDataMap):
        quotedFields = classDataMap["quotedFields"]
        primitive = classDataMap["primitive"]
        if not primitive:
            text = ToStringMethodAdder.template % {"quotedFields": quotedFields}
            generalDataMap["out"].write(text)


class ReferenceFeatureAdder(Visitor):
    completeFuctionsTemplate="""
    def resolveReferences(self, sections):
%(resolveAssigments)s

    @staticmethod
    def resolveReferencesOfOneOrMore(oneOrMore, sections):
        if oneOrMore.__class__ == [].__class__:
            for object in oneOrMore:
                object.resolveReferences(sections) 
        else:
            oneOrMore.resolveReferences(sections)

    def introduceIndexReferences(self, indexMaker):
%(introduceReferencesAssigments)s

    @staticmethod
    def introduceIndexReferencesForOneOrMore(object, indexMaker):
        if object.__class__ == MD34IndexEntry:
            return # nothing to do (object was reachable trough 2 paths)
        if object.__class__ == [].__class__:
            for o in object:
                o.introduceIndexReferences(indexMaker) 
        else:
            object.introduceIndexReferences(indexMaker)
"""
    simpleFuctionsTemplate = """
    @staticmethod
    def introduceIndexReferencesForOneOrMore(object, indexMaker):
        pass #nothing to do
    
    @staticmethod
    def resolveReferencesOfOneOrMore(oneOrMore, sections):
        pass #nothing to do
"""
    introduceReferencesTemplate = """\
        indexReference = indexMaker.getIndexReferenceTo(self.%(fieldName)s, %(refTo)s)
        %(refTo)s.introduceIndexReferencesForOneOrMore(self.%(fieldName)s, indexMaker)
        self.%(fieldName)s = indexReference
"""

    introduceReferencesForNoneTemplate = """\
        self.%(fieldName)s = indexMaker.getIndexReferenceTo(self.%(fieldName)s, None)
"""

    def visitClassStart(self, generalDataMap, classDataMap):
        self.resolveAssigments = ""
        self.introduceReferencesAssigments = ""

    def visitFieldStart(self, generalDataMap, classDataMap, fieldDataMap):
        fullName = classDataMap["fullName"]
        fieldName = fieldDataMap["fieldName"]
        fieldType = fieldDataMap["typeString"]
        knownStructs = generalDataMap["knownStructs"]
        if fieldType == "Reference":
            refTo = fieldDataMap["refTo"]
            if (refTo != None) and (not (refTo in knownStructs)):
                raise Exception("Structure %s referenced by %s.%s is not defined" % (refTo,fullName,fieldName))

            if refTo == None:
                template = ReferenceFeatureAdder.introduceReferencesForNoneTemplate
            else:
                template = ReferenceFeatureAdder.introduceReferencesTemplate
            self.introduceReferencesAssigments += template % {"fieldName": fieldName, "refTo":refTo}
            self.resolveAssigments += "        self.%(fieldName)s = resolveRef(self.%(fieldName)s,sections,%(refTo)s,\"%(fullName)s.%(fieldName)s\")\n" % {"fieldName": fieldName, "fullName":fullName, "refTo": refTo}
            
    def visitClassEnd(self, generalDataMap, classDataMap):
        if (self.introduceReferencesAssigments) == "" and (self.resolveAssigments == ""):
            text = ReferenceFeatureAdder.simpleFuctionsTemplate
        else:
            fullName = classDataMap.get("fullName")
            text = ReferenceFeatureAdder.completeFuctionsTemplate % {"fullName":fullName, 
            "introduceReferencesAssigments":self.introduceReferencesAssigments, "resolveAssigments":self.resolveAssigments}
        generalDataMap["out"].write(text)
        
        

class ExpectedAndDefaultConstantsDeterminer(Visitor):
    def visitFieldStart(self, generalDataMap, classDataMap, fieldDataMap):
        fieldName = fieldDataMap["fieldName"]
        fieldType = fieldDataMap["typeString"]
        fieldIndex = fieldDataMap["fieldIndex"]
        refTo = fieldDataMap["refTo"]
        knownStructs = generalDataMap["knownStructs"]
        fullName = classDataMap["fullName"]
        expectedValueString = fieldDataMap["expectedValueString"]
        defaultValueString = fieldDataMap["defaultValueString"]
        expectedValueConstant = None
        defaultValueConstant = None
        if fieldType in ("int32", "int16", "int8", "uint8","uint16", "uint32"):
            if expectedValueString != None:
                try:
                    expectedValue = int(expectedValueString, 0)
                except ValueError:
                    raise Exception("The specified expected value for %(fullName)s.%(fieldName)s is not an integer" % {"fullName":fullName,"fieldName":fieldName})
                expectedValueConstant = "int(%s)" %expectedValueString
            
            if defaultValueString != None:
                try:
                    defaultValue = int(defaultValueString, 0)
                except ValueError:
                    raise Exception("The specified default value for %(fullName)s.%(fieldName)s is not an integer" % {"fullName":fullName,"fieldName":fieldName})
                defaultValueConstant = defaultValueString
                
        elif fieldType == "float":
            if expectedValueString != None:
                try:
                    expectedValue = float(expectedValueString)
                except ValueError:
                    raise Exception("The specified expected value for %(fullName)s.%(fieldName)s is not a float" % {"fullName":fullName,"fieldName":fieldName})
                if expectedValueString == "inf":
                    expectedValueConstant = 'float("inf")'
                else:
                    expectedValueConstant = expectedValueString

            if defaultValueString != None:
                try:
                    defaultValue = float(defaultValueString)
                except ValueError:
                    raise Exception("The specified default value for %(fullName)s.%(fieldName)s is not a a float" % {"fullName":fullName,"fieldName":fieldName})
                if defaultValueString == "inf":
                    defaultValueConstant = 'float("inf")'
                else:
                    defaultValueConstant = defaultValueString
        elif fieldType == "Reference":
            if refTo in knownStructs:
                defaultValueConstant = '%s.createEmptyArray()' % (refTo)
            else:
                defaultValueConstant = '[]'
        elif fieldType == None:
            fieldSize = fieldDataMap["fieldSize"]
            defaultValueConstant = "bytes(%d)" % fieldSize

        fieldDataMap["expectedValueConstant"] = expectedValueConstant
        fieldDataMap["defaultValueConstant"] = defaultValueConstant


class CreateInstancesFeatureAdder(Visitor):
    charTypeTemplate = """
    @staticmethod
    def createInstances(rawBytes, count):
        return rawBytes[:count-1].decode("ASCII")
    """
    
    u8TypeTemplate = """
    @staticmethod
    def createInstances(rawBytes, count):
        return bytearray(rawBytes)
    """
    
    primitiveTypeTemplate = """
    @staticmethod
    def createInstances(rawBytes, count):
        list = []
        for offset in range(0, count*%(fullName)s.size, %(fullName)s.size):
            bytesOfOneEntry = rawBytes[offset:(offset+%(fullName)s.size)]
            intValue = %(fullName)s.structFormat.unpack(bytesOfOneEntry)[0]
            list.append(intValue)
        return list
    """
    
    defaultTemplate = """
    def __init__(self, readable = None, rawBytes = None):
        if readable != None:
            assert %(fullName)s.size == %(fullName)s.structFormat.size
            rawBytes = readable.read(%(fullName)s.size)
        if rawBytes != None:
            l = %(fullName)s.structFormat.unpack(rawBytes)
%(assignments)s\
        if (readable == None) and (rawBytes == None):
%(defaultValueAssignments)s\
            pass
    @staticmethod
    def createInstances(rawBytes, count):
        list = []
        startOffset = 0
        stopOffset = startOffset + %(fullName)s.size
        for i in range(count):
            list.append(%(fullName)s(rawBytes=rawBytes[startOffset:stopOffset]));
            startOffset = stopOffset
            stopOffset += %(fullName)s.size
        return list
    """

    def visitClassStart(self, generalDataMap, classDataMap):
        self.assignments = ""
        self.packedAttributes = ""
        self.defaultValueAssignments = ""

    def visitFieldStart(self, generalDataMap, classDataMap, fieldDataMap):
        fieldName = fieldDataMap["fieldName"]
        fieldType = fieldDataMap["typeString"]
        fieldIndex = fieldDataMap["fieldIndex"]
        refTo = fieldDataMap["refTo"]
        knownStructs = generalDataMap["knownStructs"]
        expectedValueConstant = fieldDataMap["expectedValueConstant"]
        defaultValueConstant = fieldDataMap["defaultValueConstant"]
        self.assignments += "            "
        if fieldType == "tag":
            self.assignments += "self.%s = unpackTag(l[%d])\n"  % (fieldName, fieldIndex)
        elif fieldType in knownStructs:
            self.assignments += "self.%s = %s(rawBytes=l[%d])\n"  % (fieldName, fieldType, fieldIndex)
        else:
            self.assignments += "self.%s = l[%d]\n" % (fieldName, fieldIndex)

        if expectedValueConstant != None:
            fullName = classDataMap["fullName"]
            self.assignments += ('            if self.%(fieldName)s != %(expectedValue)s:\n             raise Exception("%(fullName)s.%(fieldName)s has value %%s instead of the expected value %(expectedValue)s" %% self.%(fieldName)s)\n' % {"fullName":fullName, "fieldName":fieldName, "expectedValue":expectedValueConstant })

        if (defaultValueConstant != None) or (expectedValueConstant != None):
            if defaultValueConstant == None:
                defaultValueConstant = expectedValueConstant
            self.defaultValueAssignments += ('            self.%(fieldName)s = %(defaultValueConstant)s\n' % {"fieldName":fieldName, "defaultValueConstant":defaultValueConstant })

    def visitClassEnd(self, generalDataMap, classDataMap):
        fullName = classDataMap.get("fullName")
        primitive = classDataMap["primitive"]
        
        if fullName ==  "CHARV0":
            template = CreateInstancesFeatureAdder.charTypeTemplate
        elif fullName == "U8__V0":
            template = CreateInstancesFeatureAdder.u8TypeTemplate
        elif primitive:
            template = CreateInstancesFeatureAdder.primitiveTypeTemplate
        else:
            template = CreateInstancesFeatureAdder.defaultTemplate
        text = template % {"fullName":fullName,"assignments":self.assignments, "defaultValueAssignments": self.defaultValueAssignments}
        generalDataMap["out"].write(text)

class ToBytesFeatureAdder(Visitor):
    template = """
    def toBytes(self):
        return %(fullName)s.structFormat.pack(%(packedAttributes)s)
    """
    def visitClassStart(self, generalDataMap, classDataMap):
        self.packedAttributes = ""


    def visitFieldStart(self, generalDataMap, classDataMap, fieldDataMap):
        fieldName = fieldDataMap["fieldName"]
        fieldType = fieldDataMap["typeString"]
        fieldIndex = fieldDataMap["fieldIndex"]
        knownStructs = generalDataMap["knownStructs"]
        if fieldIndex > 0:
            self.packedAttributes += ", "
        if fieldType == "tag":
            self.packedAttributes += "packTag(self.%s)" % fieldName
        elif fieldType in knownStructs:
            self.packedAttributes += "self.%s.toBytes()" % fieldName
        else:
            self.packedAttributes += "self.%s" % fieldName

    def visitClassEnd(self, generalDataMap, classDataMap):
        knownStructs = generalDataMap["knownStructs"]
        fullName = classDataMap.get("fullName")
        primitive = classDataMap["primitive"]
        
        if fullName ==  "CHARV0":
            return # unsupported for that type
        elif fullName == "U8__V0":
            return # unsupported for that type
        if primitive:
            return # unsupported for that type
        elif fullName in knownStructs:
            text = ToBytesFeatureAdder.template % {"fullName":fullName,"packedAttributes":self.packedAttributes}
            generalDataMap["out"].write(text)

class SizeDeterminer(Visitor):
    primitiveFieldTypeSizes = {"uint32":4,"int32":4,"uint16":2,"int16":2, "uint8":1, "float":4, "tag":4}

    def visitStart(self, generalDataMap):
        generalDataMap["knownStructSizes"] = {}

    def visitClassStart(self, generalDataMap, classDataMap):
        self.structSize = 0
    
    def visitFieldStart(self, generalDataMap, classDataMap, fieldDataMap):
        fieldType = fieldDataMap["typeString"]
        primitiveFieldTypeSizes = SizeDeterminer.primitiveFieldTypeSizes
        if fieldType in primitiveFieldTypeSizes:
            fieldSize = primitiveFieldTypeSizes[fieldType]
        else:
            knownStructSizes = generalDataMap["knownStructSizes"]
            if fieldType in knownStructSizes:
                fieldSize = knownStructSizes[fieldType]
            else:
                if (fieldType != None):
                    fullName = classDataMap["fullName"]
                    fieldName = fieldDataMap["fieldName"]
                    raise Exception("Field %(fullName)s.%(fieldName)s has unknown type %(fieldType)s" % {"fullName":fullName,"fieldName":fieldName,"fieldType":fieldType})
                else:
                    specifiedFieldSize = fieldDataMap["specifiedFieldSize"]
                    if specifiedFieldSize == None:
                        fieldName = fieldDataMap["fieldName"]
                        raise Exception("Field %s has neither type nor size attribute" % fieldName)
                    fieldSize = specifiedFieldSize

    
        fieldDataMap["fieldSize"] = fieldSize
        self.structSize += fieldSize
    
    def visitClassEnd(self, generalDataMap, classDataMap):
        fullName = classDataMap.get("fullName")
        knownStructSizes = generalDataMap["knownStructSizes"]
        xmlNode = classDataMap["xmlNode"]
        specifiedSize = classDataMap["specifiedSize"]
        if specifiedSize == None:
            raise Exception("%s lacks a size definition, calculated size is %s" % ( fullName, currentSize));

        currentSize = self.structSize;
        if currentSize > specifiedSize : 
            raise Exception("%s has %s bytes more fields then it should have according to it's size definition" % (fullName, currentSize - specifiedSize ));

        missingBytes = specifiedSize - currentSize
        if missingBytes > 0 :
            raise Exception("%s needs %s bytes more fields to match it's size definition" % (fullName, specifiedSize - currentSize));
        
        knownStructSizes[fullName] = specifiedSize;
        classDataMap["size"] = specifiedSize


class StructSizeConstantAdder(Visitor):
    def visitClassEnd(self, generalDataMap, classDataMap):
        size = classDataMap["size"]
        text = "    size = %s\n" % size
        generalDataMap["out"].write(text)


class StructFormatConstantAdder(Visitor):
    template = """    structFormat = struct.Struct("%(formatString)s")\n"""
    primitiveFieldTypeFormats = {"uint32":"I","int32":"i","uint16":"H","int16":"h", "uint8":"B", "float":"f", "tag":"4s"}
    def visitClassStart(self, generalDataMap, classDataMap):
        self.structureFormatString = "<"

    def visitFieldStart(self, generalDataMap, classDataMap, fieldDataMap):
        fieldType = fieldDataMap["typeString"]
        primitiveFieldTypeFormats = StructFormatConstantAdder.primitiveFieldTypeFormats
        if fieldType in primitiveFieldTypeFormats:
            self.structureFormatString += primitiveFieldTypeFormats[fieldType]
        else:
            fieldSize = fieldDataMap["fieldSize"]
            self.structureFormatString += "%ss" % fieldSize

    def visitClassEnd(self, generalDataMap, classDataMap):
        text = StructFormatConstantAdder.template % {"formatString":self.structureFormatString}
        generalDataMap["out"].write(text)

class CountOneOrMoreMethodAdder(Visitor):
    charTypeTemplate = """
    @staticmethod
    def countOneOrMore(object):
        if object == None:
            return 0
        return len(object)+1 # +1 terminating null character
    """

    u8TypeTemplate = """
    @staticmethod
    def countOneOrMore(object):
        return len(object)
    """

    defaultTemplate = """
    @staticmethod
    def countOneOrMore(object):
        if object.__class__ == [].__class__:
            return len(object)
        else:
            return 1
    """
    
    def visitClassEnd(self, generalDataMap, classDataMap):
        knownStructs = generalDataMap["knownStructs"]
        fullName = classDataMap.get("fullName")
        primitive = classDataMap["primitive"]
        
        if fullName ==  "CHARV0":
            template = CountOneOrMoreMethodAdder.charTypeTemplate
        elif fullName == "U8__V0":
            template = CountOneOrMoreMethodAdder.u8TypeTemplate
        else:
            template = CountOneOrMoreMethodAdder.defaultTemplate

        text = template % {}
        generalDataMap["out"].write(text)

class RawBytesForOneOrMoreMethodAdder(Visitor):
    charTypeTemplate = """
    def rawBytesForOneOrMore(oneOrMore):
        return oneOrMore.encode("ASCII") + b"\\x00"
    """
    
    u8TypeTemplate = """
    def rawBytesForOneOrMore(oneOrMore):
        return oneOrMore
    """

    primitiveTypeTemplate = """
    @staticmethod
    def rawBytesForOneOrMore(oneOrMore):
        if oneOrMore.__class__ == [].__class__:
            list = oneOrMore
        else:
            list = [oneOrMore]
        rawBytes = bytearray(%(fullName)s.bytesRequiredForOneOrMore(oneOrMore))
        offset = 0
        nextOffset = %(fullName)s.size
        for object in list:
            rawBytes[offset:nextOffset] = %(fullName)s.structFormat.pack(object)
            offset = nextOffset
            nextOffset += %(fullName)s.size
        return rawBytes
    """

    defaultTemplate = """
    @staticmethod
    def rawBytesForOneOrMore(oneOrMore):
        if oneOrMore.__class__ == [].__class__:
            list = oneOrMore
        else:
            list = [oneOrMore]
        rawBytes = bytearray(%(fullName)s.bytesRequiredForOneOrMore(oneOrMore))
        offset = 0
        nextOffset = %(fullName)s.size
        for object in list:
            rawBytes[offset:nextOffset] = object.toBytes()
            offset = nextOffset
            nextOffset += %(fullName)s.size
        return rawBytes
    """
    
    def visitClassEnd(self, generalDataMap, classDataMap):
        fullName = classDataMap.get("fullName")
        primitive = classDataMap["primitive"]
        if fullName ==  "CHARV0":
            template = RawBytesForOneOrMoreMethodAdder.charTypeTemplate
        elif fullName == "U8__V0":
            template = RawBytesForOneOrMoreMethodAdder.u8TypeTemplate
        elif primitive:
            template = RawBytesForOneOrMoreMethodAdder.primitiveTypeTemplate
        else:
            template = RawBytesForOneOrMoreMethodAdder.defaultTemplate
        text = template % {"fullName":fullName}
        generalDataMap["out"].write(text)
        
class BytesRequiredForOneOrMoreMethodAdder(Visitor):
    template = """
    @staticmethod
    def bytesRequiredForOneOrMore(object):
        return %(fullName)s.countOneOrMore(object) * %(fullName)s.size
    """

    def visitClassEnd(self, generalDataMap, classDataMap):
        fullName = classDataMap.get("fullName")
        template = BytesRequiredForOneOrMoreMethodAdder.template
        text = template % {"fullName":fullName}
        generalDataMap["out"].write(text)
        
class CreateEmptyArrayMethodAdder(Visitor):
    charTemplate = """
    @staticmethod
    def createEmptyArray():
        return None # even no terminating character
    """
    
    u8Template = """
    @staticmethod
    def createEmptyArray():
        return bytearray(0)
    """
    
    defaultTemplate = """
    @staticmethod
    def createEmptyArray():
        return []
    """
    
    def visitClassEnd(self, generalDataMap, classDataMap):
        fullName = classDataMap.get("fullName")
        if fullName ==  "CHARV0":
            template = CreateEmptyArrayMethodAdder.charTemplate
        elif fullName == "U8__V0":
            template = CreateEmptyArrayMethodAdder.u8Template
        else:
            template = CreateEmptyArrayMethodAdder.defaultTemplate
        text = template % {}
        generalDataMap["out"].write(text)

class BitMethodsAdder(Visitor):
    template = """
    fieldToBitMaskMapMap = %(fieldToBitMaskMapMap)s
    
    def getNamedBit(self, field, bitName):
        mask = %(fullName)s.fieldToBitMaskMapMap[field][bitName]
        return ((getattr(self, field) & mask) != 0)
    
    def setNamedBit(self, field, bitName, value):
        mask = %(fullName)s.fieldToBitMaskMapMap[field][bitName]
        fieldValue = getattr(self, field)
        if value:
            setattr(self, field, fieldValue | mask)
        else:
            if (fieldValue & mask) != 0:
                setattr(self, field,  fieldValue ^ mask)
    
    def getBitNameMaskPairs(self, field):
        return %(fullName)s.fieldToBitMaskMapMap[field].items()
    """
    def visitClassStart(self, generalDataMap, classDataMap):
        self.fieldToBitMaskMapMap = {}
        
    def visitFieldStart(self, generalDataMap, classDataMap, fieldDataMap):
        self.bitMaskMap = {}
        
    def visitFieldBit(self, generalDataMap, classDataMap, fieldDataMap, bitDataMap):
        bitName = bitDataMap["name"]
        bitMask = bitDataMap["mask"]
        self.bitMaskMap[bitName] = bitMask
        
    def visitFieldEnd(self,generalDataMap, classDataMap, fieldDataMap):
        #TODO call
        fieldName = fieldDataMap["fieldName"]
        self.fieldToBitMaskMapMap[fieldName] = self.bitMaskMap
        
    def visitClassEnd(self, generalDataMap, classDataMap):
        fullName = classDataMap["fullName"]
        mapString = "{"
        firstField = True
        for field, bitMaskMap in self.fieldToBitMaskMapMap.items():
            if firstField:
                firstField = False
            else:
                mapString += ", "
            mapString += ('"%s": {' % field)
            firstBit = True
            for bitName, bitMask in bitMaskMap.items():
                if firstBit:
                    firstBit = False
                else:
                    mapString += ", "
                mapString += '"%(bitName)s":%(bitMask)s' % {"bitName":bitName, "bitMask":hex(bitMask)}
            mapString += "}"
        mapString += "}"
        text = BitMethodsAdder.template % {"fullName":fullName,"fieldToBitMaskMapMap":mapString}
        generalDataMap["out"].write(text)

class GetFieldTypeInfoMethodAdder(Visitor):
    methodTemplate="""
    @staticmethod
    def getFieldTypeInfo(fieldName):
        return %(typeName)s.fieldToTypeInfoMap[fieldName]
    """
    
    def visitClassStart(self, generalDataMap, classDataMap):
        self.fieldToTypeInfoMapStr = "\n    fieldToTypeInfoMap = {"


    def visitFieldEnd(self,generalDataMap, classDataMap, fieldDataMap):
        #TODO call
        fieldName = fieldDataMap["fieldName"]
        fieldType = fieldDataMap["typeString"]
        fieldIndex = fieldDataMap["fieldIndex"]
        knownStructs = generalDataMap["knownStructs"]
        if (fieldType == 'Reference'):
            fieldType = fieldDataMap["refTo"]
            fieldIsList = True
        else:
            fieldIsList = False
        
        if fieldType in knownStructs:
            typeClass = fieldType
        else:
            typeClass = "None"
        
        fieldTypeStr = ('"%s"' % fieldType) if fieldType != None else  None
        
        if fieldIndex != 0:
            self.fieldToTypeInfoMapStr += ", "
        self.fieldToTypeInfoMapStr += ('"%(fieldName)s":FieldTypeInfo(%(fieldTypeStr)s,%(typeClass)s, %(isList)s)' % 
            {"fieldName":fieldName, "fieldTypeStr":fieldTypeStr, "typeClass": typeClass ,"isList":fieldIsList})
        
    def visitClassEnd(self, generalDataMap, classDataMap):
        fullName = classDataMap["fullName"]
        self.fieldToTypeInfoMapStr += "}"
        methodText = GetFieldTypeInfoMethodAdder.methodTemplate % {"typeName":fullName}
        generalDataMap["out"].write(self.fieldToTypeInfoMapStr)
        generalDataMap["out"].write(methodText)

class ValidateMethodAdder(Visitor):
    defaultTemplate="""
    @staticmethod
    def validateInstance(instance, id):
        if type(instance) != %(fullName)s:
            raise Exception("%%s is not of type %%s but %%s" %% (id, "%(fullName)s", type(instance)))
%(statements)s
"""
    
    validateTagTemplate = """\
        if (type(instance.%(fieldName)s) != str) or (len(instance.%(fieldName)s) != 4):
            raise Exception("%%s is not a string with 4 characters" %% (fieldId))
"""

    validateIntTemplate = """
        if (type(instance.%(fieldName)s) != int):
            raise Exception("%%s is not an int" %% (fieldId))
"""
    validateFloatTemplate = """
        if (type(instance.%(fieldName)s) != float):
            raise Exception("%%s is not a float" %% (fieldId))
"""
    validateList = """
        if (type(instance.%(fieldName)s) != list):
            raise Exception("%%s is not a list of %%s but a %%s" %% (fieldId, "%(refTo)s", type(instance.%(fieldName)s)))
        for itemIndex, item in enumerate(instance.%(fieldName)s):
            %(refTo)s.validateInstance(item, "%%s[%%d]" %% (fieldId, itemIndex))
"""
    validateEmptyList = """
        if (type(instance.%(fieldName)s) != list) or (len(instance.%(fieldName)s) != 0):
            raise Exception("%%s is not an empty list" %% (fieldId))
"""
    validateKnownStruct = """
        %(fieldType)s.validateInstance(instance.%(fieldName)s, fieldId)
"""
    validateUnknownBytes = """
        if (type(instance.%(fieldName)s) != bytes) or (len(instance.%(fieldName)s) != %(fieldSize)s):
            raise Exception("%%s is not an bytes object of size %%s" %% (fieldId, "%(fieldSize)s"))
"""
    validateCHARV0Reference = """
        if (instance.%(fieldName)s != None) and (type(instance.%(fieldName)s) != str):
            raise Exception("%%s is not a string but a %%s" %% (fieldId, type(instance.%(fieldName)s) ))
"""
    validateU8__V0Reference = """
        if (type(instance.%(fieldName)s) != bytearray):
            raise Exception("%%s is not a bytearray but a %%s" %% (fieldId, type(instance.%(fieldName)s)))
"""
    validateREALV0Reference = """
        if (type(instance.%(fieldName)s) != list):\
            raise Exception("%%s is not a list of float" %% (fieldId))
        for itemIndex, item in enumerate(instance.%(fieldName)s):
            if type(item) != float: 
                itemId = "%%s[%%d]" %% (fieldId, itemIndex)
                raise Exception("%%s is not an float" %% (itemId))
"""
    validateIntReference = """\
        if (type(instance.%(fieldName)s) != list):
            raise Exception("%%s is not a list of integers" %% (fieldId))
        for itemIndex, item in enumerate(instance.%(fieldName)s):
            if type(item) != int: 
                itemId = "%%s[%%d]" %% (fieldId, itemIndex)
                raise Exception("%%s is not an integer" %% (itemId))
"""

    def visitClassStart(self, generalDataMap, classDataMap):
        self.statements = ""

    def visitFieldStart(self, generalDataMap, classDataMap, fieldDataMap):
        fieldName = fieldDataMap["fieldName"]
        fieldType = fieldDataMap["typeString"]
        fieldIndex = fieldDataMap["fieldIndex"]
        refTo = fieldDataMap["refTo"]
        knownStructs = generalDataMap["knownStructs"]
        self.statements += '        fieldId = id + ".%(fieldName)s"\n'  % {"fieldName":fieldName}
        if fieldType == "tag":
            self.statements += ValidateMethodAdder.validateTagTemplate % {"fieldName":fieldName}
        elif fieldType in ("int32", "int16", "int8", "uint8","uint16", "uint32"):
            # TODO check integer size
            self.statements += ValidateMethodAdder.validateIntTemplate % {"fieldName":fieldName}
        elif fieldType == "float":
            self.statements += ValidateMethodAdder.validateFloatTemplate % {"fieldName":fieldName}
        elif fieldType == "Reference":
            if refTo in knownStructs:
                if refTo == "CHARV0":
                    self.statements +=  ValidateMethodAdder.validateCHARV0Reference % {"fieldName":fieldName}
                elif refTo == "U8__V0":
                    self.statements +=  ValidateMethodAdder.validateU8__V0Reference % {"fieldName":fieldName}
                elif refTo == "REALV0":
                    self.statements +=  ValidateMethodAdder.validateREALV0Reference % {"fieldName":fieldName}
                elif refTo in  ["I16_V0", "U16_V0", "I32_V0", "U32_V0"]:
                    self.statements +=  ValidateMethodAdder.validateIntReference % {"fieldName":fieldName}
                else:
                    self.statements +=  ValidateMethodAdder.validateList % {"fieldName":fieldName, "refTo":refTo}
            else:
                self.statements +=  ValidateMethodAdder.validateEmptyList % {"fieldName":fieldName}
        elif fieldType in knownStructs:
            self.statements +=  ValidateMethodAdder.validateKnownStruct % {"fieldName":fieldName, "fieldType":fieldType}
        elif fieldType == None:
            fieldSize = fieldDataMap["fieldSize"]
            self.statements +=  ValidateMethodAdder.validateUnknownBytes % {"fieldName":fieldName, "fieldSize":fieldSize}

    def visitClassEnd(self, generalDataMap, classDataMap):
        fullName = classDataMap.get("fullName")
        primitive = classDataMap["primitive"]
        template = ValidateMethodAdder.defaultTemplate
        if not primitive:
            text = template % {"fullName":fullName,"statements":self.statements}
            generalDataMap["out"].write(text)
    
class StructureMapAdder(Visitor):
    def visitStart(self, generalDataMap):
        self.structMapText = "\nstructMap = {"
        self.firstStruct = True

    def visitClassEnd(self, generalDataMap, classDataMap):
        fullName = classDataMap["fullName"]
        if self.firstStruct:
            self.firstStruct = False
        else:
            self.structMapText +=","
        self.structMapText += '"%(fullName)s":%(fullName)s' % {"fullName":fullName}

    def visitEnd(self, generalDataMap):
        self.structMapText += "}\n"
        generalDataMap["out"].write(self.structMapText)
        
class FooterAdder(Visitor):
    text = """

def resolveAllReferences(list, sections):
    ListType = type([])
    for sublist in list:
        if type(sublist) == ListType:
            for entry in sublist:
                entry.resolveReferences(sections)
    
def loadSections(filename):
    source = open(filename, "rb")
    try:
        header = MD34V11(source);
        source.seek(header.indexOffset)
        sections = []
        for i in range(header.indexSize):
            section = Section()
            section.indexEntry = MD34IndexEntry(source)
            sections.append(section)
        
        offsets = []
        for section in sections:
            indexEntry = section.indexEntry
            offsets.append(indexEntry.offset)
        offsets.append(header.indexOffset)
        offsets.sort()
        previousOffset = offsets[0]
        offsetToSizeMap = {}
        for offset in offsets[1:]:
            offsetToSizeMap[previousOffset] = offset - previousOffset
            previousOffset = offset
        
        unknownSections = 0
        for section in sections:
            indexEntry = section.indexEntry
            className = indexEntry.tag + "V" + str(indexEntry.version)
            source.seek(indexEntry.offset)
            numberOfBytes = offsetToSizeMap[indexEntry.offset]
            section.rawBytes = source.read(numberOfBytes)
            if className in structMap:
                section.contentClass = structMap[className]
                section.determineContentField()
            else:
                guessedUnusedSectionBytes = 0
                for i in range (1,16):
                    if section.rawBytes[len(section.rawBytes)-i] == 0xaa:
                        guessedUnusedSectionBytes += 1
                    else:
                        break
                guessedBytesPerEntry = float(len(section.rawBytes) - guessedUnusedSectionBytes) / indexEntry.repetitions
                message = "ERROR: Unknown section at offset %s with tag=%s version=%s repetitions=%s sectionLengthInBytes=%s guessedUnusedSectionBytes=%s guessedBytesPerEntry=%s\\n" % (indexEntry.offset, indexEntry.tag, indexEntry.version, indexEntry.repetitions, len(section.rawBytes),guessedUnusedSectionBytes,guessedBytesPerEntry )
                stderr.write(message)
                unknownSections += 1
        if unknownSections != 0:
            raise Exception("There were %s unknown sections" % unknownSections)
    finally:
        source.close()
    return sections

def resolveReferencesOfSections(sections):
    for section in sections:
        section.resolveReferences(sections)

def checkThatAllSectionsGotReferenced(sections):
    numberOfUnreferencedSections = 0
    for sectionIndex, section in enumerate(sections):

        if (section.timesReferenced == 0) and (sectionIndex != 0):
            numberOfUnreferencedSections += 1
            stderr.write("WARNING: %sV%s (%d repetitions) got %d times referenced\\n" % (section.indexEntry.tag, section.indexEntry.version, section.indexEntry.repetitions , section.timesReferenced))
            reference = Reference()
            reference.entries = section.indexEntry.repetitions
            reference.index = sectionIndex
            reference.flags = 0
            bytesToSearch = reference.toBytes()
            for sectionToCheck in sections:
                positionInSection = sectionToCheck.rawBytes.find(bytesToSearch)
                if positionInSection != -1:
                    stderr.write("  -> Found a reference at offset %d in a section of type %sV%s\\n" % (positionInSection, sectionToCheck.indexEntry.tag,sectionToCheck.indexEntry.version)) 

    if numberOfUnreferencedSections > 0:
        raise Exception("Unable to load all data: There were %d unreferenced sections. View log for details" % numberOfUnreferencedSections)

def loadModel(filename):
    sections = loadSections(filename)
    resolveReferencesOfSections(sections)
    checkThatAllSectionsGotReferenced(sections)
    header = sections[0].content[0]
    model = header.model[0]
    MODLV23.validateInstance(model,"model")
    return model

class IndexReferenceSourceAndSectionListMaker:
    \"\"\" Creates a list of sections which are needed to store the objects for which index references are requested\"\"\"
    def __init__(self):
        self.objectsIdToIndexReferenceMap = {}
        self.offset = 0
        self.nextFreeIndexPosition = 0
        self.sections = []
    
    def getIndexReferenceTo(self, objectToSave, objectClass):
        if id(objectToSave) in self.objectsIdToIndexReferenceMap.keys():
            return self.objectsIdToIndexReferenceMap[id(objectToSave)]
        
        if objectClass == None:
            repetitions = 0
        else:
            repetitions = objectClass.countOneOrMore(objectToSave)
        
        indexReference = Reference()
        indexReference.entries = repetitions
        indexReference.index = self.nextFreeIndexPosition
        indexReference.flags = 0
        
        if (repetitions > 0):
            indexEntry = MD34IndexEntry()
            indexEntry.tag = objectClass.tagName
            indexEntry.offset = self.offset
            indexEntry.repetitions = repetitions
            indexEntry.version = objectClass.tagVersion
            
            section = Section()
            section.indexEntry = indexEntry
            section.content = objectToSave
            section.contentClass = structMap[("%sV%s" % (indexEntry.tag, indexEntry.version))]
            self.sections.append(section)
            self.objectsIdToIndexReferenceMap[id(objectToSave)] = indexReference
            totalBytes = objectClass.bytesRequiredForOneOrMore(objectToSave)
            totalBytes = increaseToValidSectionSize(totalBytes)
            self.offset += totalBytes
            self.nextFreeIndexPosition += 1
        return indexReference
    
    
def modelToSections(model):
    header = MD34V11()
    header.tag = "MD34"
    header.model = model
    
    indexMaker = IndexReferenceSourceAndSectionListMaker()
    indexMaker.getIndexReferenceTo([header], MD34V11)
    header.introduceIndexReferences(indexMaker)
    sections = indexMaker.sections
    header.indexOffset = indexMaker.offset
    header.indexSize = len(sections)

    for section in sections:
        section.determineFieldRawBytes()
    return sections

def saveSections(sections, filename):
    fileObject = open(filename, "w+b")
    try:
        previousSection = None
        for section in sections:
            if section.indexEntry.offset != fileObject.tell():
                raise Exception("Section length problem: Section with index entry %(previousIndexEntry)s has length %(previousLength)s and gets followed by section with index entry %(currentIndexEntry)s" % {"previousIndexEntry":previousSection.indexEntry,"previousLength":len(previousSection.rawBytes),"currentIndexEntry":section.indexEntry} )
            fileObject.write(section.rawBytes)
            previousSection = section
        header = sections[0].content[0]
        if fileObject.tell() != header.indexOffset:
            raise Exception("Not at expected write position %s after writing sections, but %s"%(header.indexOffset, fileObject.tell()))
        for section in sections:
            fileObject.write(section.indexEntry.toBytes())
    finally:
        fileObject.close()
        
def saveAndInvalidateModel(model, filename):
    '''Do not use the model object after calling this method since it gets modified'''
    MODLV23.validateInstance(model,"model")
    sections = modelToSections(model)
    saveSections(sections, filename)


"""
    def visitEnd(self, generalDataMap):
        generalDataMap["out"].write(FooterAdder.text)


def visitStructresDomWith(structuresDom, visitors, generalDataMap):
    for visitor in visitors:
        visitor.visitStart(generalDataMap)

    for tagNode in structuresDom.getElementsByTagName("structure"):
        classDataMap = {}
        classDataMap["xmlNode"] = tagNode

        for visitor in visitors:
            visitor.visitClassStart(generalDataMap, classDataMap)
        
        fieldNodes = tagNode.getElementsByTagName("field")
        for fieldNode in fieldNodes:
            fieldDataMap = {}
            fieldDataMap["xmlNode"] = fieldNode
            for visitor in visitors:
                visitor.visitFieldStart(generalDataMap, classDataMap, fieldDataMap)
            
            bitNodes = tagNode.getElementsByTagName("bit")
            for bitNode in bitNodes:
                bitDataMap = {}
                bitDataMap["xmlNode"] = bitNode
                
                for visitor in visitors:
                    visitor.visitFieldBit(generalDataMap, classDataMap, fieldDataMap, bitDataMap)

            for visitor in visitors:
                visitor.visitFieldEnd(generalDataMap, classDataMap, fieldDataMap)

        for visitor in visitors:
            visitor. visitClassEnd(generalDataMap, classDataMap)

    for visitor in visitors:
        visitor.visitEnd(generalDataMap)

def writeM3PythonTo(structuresXmlFile, out):
    doc = xml.dom.minidom.parse(structuresXmlFile)
    generalDataMap = {}

    # first run is only for determing the complete list of known structures
    firstRunVisitors = [
        StructureAttributesReader(),
        FullNameDeterminer(),
        KnownStructuresListDeterminer()]
    visitStructresDomWith(doc, firstRunVisitors, generalDataMap)

    generalDataMap["out"] = out

    secondRunVisitors = [
        HeaderAdder(),
        StructureAttributesReader(),
        StructureDescriptionReader(),
        FullNameDeterminer(),
        PrimitiveStructureDetector(),
        FieldAttributesReader(), 
        FieldIndexDeterminer(),
        BitAttributesReader(),
        DuplicateFieldNameChecker(), 
        SizeDeterminer(),
        FieldOffsetChecker(), 
        QuotedFieldsDeterminer(), 
        ClassHeaderAdder(),
        FullNameConstantAdder(),
        TagNameConstantAdder(),
        VersionConstantAdder(),
        StructSizeConstantAdder(),
        StructFormatConstantAdder(),
        FieldsConstantAdder(), 
        SetAttributesMethodAdder(), 
        ToStringMethodAdder(), 
        ReferenceFeatureAdder(),
        ExpectedAndDefaultConstantsDeterminer(),
        CreateInstancesFeatureAdder(),
        ToBytesFeatureAdder(),
        RawBytesForOneOrMoreMethodAdder(),
        CountOneOrMoreMethodAdder(),
        BytesRequiredForOneOrMoreMethodAdder(),
        CreateEmptyArrayMethodAdder(),
        BitMethodsAdder(),
        GetFieldTypeInfoMethodAdder(),
        ValidateMethodAdder(),
        StructureMapAdder(),
        FooterAdder()]
    visitStructresDomWith(doc, secondRunVisitors, generalDataMap)




def generateM3Library():
    from os import path
    directory = path.dirname(__file__)
    structuresXmlPath = path.join(directory, "structures.xml")
    m3PyPath = path.join(directory, "m3.py")
    out = open(m3PyPath,"w")
    try:
        writeM3PythonTo(structuresXmlPath, out);
    finally:
        out.close()

if __name__ == "__main__":
    generateM3Library()