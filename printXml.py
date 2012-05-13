#!/usr/bin/python3
# -*- coding: utf-8 -*-

import struct
import sys
from generateM3Library import generateM3Library
generateM3Library()
from m3 import *

def byteDataToHex(byteData):
    s = "0x"
    for i in range(len(byteData)):
        hexValue = hex(byteData[i])[2:]
        if len(hexValue) <= 1:
            hexValue = "0"+hexValue
        s +=hexValue
    return s

def printXmlElement(out, indent, name, stringValue):
    out.write(("\t"*indent) + ("<%s>" % name) + stringValue + ("</%s>\n" % name))


def printObject(out, indent, name, objectToPrint):
    if type(objectToPrint) == int:
        printXmlElement(out, indent, name, hex(objectToPrint))
    elif type(objectToPrint) == bytearray or type(objectToPrint) == bytes:
        s = byteDataToHex(objectToPrint)
        printXmlElement(out, indent, name, s)
    elif hasattr(type(objectToPrint),"fields"):
        out.write(("\t"*indent) + "<%s>\n" % name)
        for fieldName in objectToPrint.fields:
            fieldValue = getattr(objectToPrint,fieldName)
            if fieldValue == None:
                out.write(("\t"*(indent+1)) + "<%s />\n" % fieldName)
            elif fieldValue.__class__ == list:
                out.write(("\t"*(indent+1)) + "<%s>\n" % fieldName)
                for entry in fieldValue:
                    printObject(out, indent+2,fieldName+"-element", entry)
                out.write(("\t"*(indent+1)) + "</%s>\m" % fieldName)
            else:
                printObject(out, indent+1,fieldName, fieldValue)
        out.write(("\t"*indent) + "</%s>\n" % name)
    else:
        printXmlElement(out, indent, name, str(objectToPrint))

def printFile(out, inputFile):
    model = loadModel(inputFile)
    printObject(out, 0, "model", model)

if __name__ == "__main__":
    argumentCount = (len(sys.argv) -1)
    
    if argumentCount == 1: 
        printFile(sys.stdout, sys.argv[1])
    elif argumentCount == 2:
        outputFile = open(sys.argv[2], "w")
        try:
            printFile(outputFile, sys.argv[1])
        finally:
            outputFile.close()
    else:
        sys.stderr.write("""\
Require one or two arguments!
Useage:
    printXml.py /path/to/m3/file.m3
Or:
    printXml.py /path/to/m3/file.m3 /path/to/xml/file/to/create.xml
""")
        sys.exit(2)

