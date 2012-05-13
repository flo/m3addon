#!/usr/bin/python3
# -*- coding: utf-8 -*-

import struct
import sys
from generateM3Library import generateM3Library
generateM3Library()
from m3 import *
import argparse
import os.path
import os

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
                out.write(("\t"*(indent+1)) + "</%s>\n" % fieldName)
            else:
                printObject(out, indent+1,fieldName, fieldValue)
        out.write(("\t"*indent) + "</%s>\n" % name)
    else:
        printXmlElement(out, indent, name, str(objectToPrint))

def printFile(out, inputFile):
    model = loadModel(inputFile)
    printObject(out, 0, "model", model)


def convertFile(inputFilePath, outputDirectory):
    if outputDirectory != None:
        fileName = os.path.basename(inputFilePath)
        outputFilePath = os.path.join(outputDirectory, fileName+ ".xml")
    else:
        outputFilePath = inputFilePath + ".xml"
    print("Converting %s -> %s" % (inputFilePath, outputFilePath))
    outputFile = open(outputFilePath, "w")
    try:
        printFile(outputFile, inputFilePath)
    finally:
        outputFile.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('path', nargs='+', help="Either a m3 file or a directory with m3 files")
    parser.add_argument('--output-directory', '-o', help='directory in which the xml files get stored')
    args = parser.parse_args()
    outputDirectory = args.output_directory
    if outputDirectory != None and not os.path.isdir(outputDirectory):
        sys.stderr.write("%s is not a directory" % outputDirectory)
        sys.exit(2)
    counter = 0
    for filePath in args.path:
        if os.path.isdir(filePath):
            for fileName in os.listdir(filePath):
                inputFilePath = os.path.join(filePath, fileName)
                if fileName.endswith(".m3"):
                     convertFile(inputFilePath, outputDirectory)
                     counter += 1
        else:
            convertFile(filePath, outputDirectory)
            counter += 1
    if counter == 1:
        print("Converted %d file" % counter)
    else:
        print("Converted %d files" % counter)
