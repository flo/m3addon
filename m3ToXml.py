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
import argparse
import os.path
import os
import io
import time
import traceback

def byteDataToHex(byteData):
    return '0x' + ''.join(["%02x" % x for x in byteData])

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

def printModel(model, outputFilePath):
    outputStream = io.StringIO()
    
    outputFile = open(outputFilePath, "w")
    printObject(outputStream, 0, "model", model)
    
    outputFile.write(outputStream.getvalue())
    outputFile.close()
    
    outputStream.close()

def convertFile(inputFilePath, outputFilePath, errorFile):
    t0 = time.time()
    
    model = None
    try:
        model = loadModel(inputFilePath)
    except Exception as e:
        print("Error: %s" % e)
        if errorFile != None:
            errorFile.write("\nFile: %s\n" % inputFilePath)
            errorFile.write("Trace: %s\n" % traceback.format_exc())
        return False
    
    printModel(model, outputFilePath)
    
    t1 = time.time()
    print("Success: %.3f s" % (t1 - t0))
    
    return True

def processFile(inputPath, outputPath, inputFilePath, errorFile):
    relativeInputPath = os.path.relpath(inputFilePath, inputPath)
    relativeOutputPath = relativeInputPath + ".xml"
    
    print("In:\t%s" % relativeInputPath)
    print("Out:\t%s" % relativeOutputPath)
    
    outputFilePath = os.path.join(outputPath, relativeOutputPath)
    
    outputDirectory = os.path.dirname(outputFilePath)
    if outputDirectory and not os.path.exists(outputDirectory):
        os.makedirs(outputDirectory)
    
    return convertFile(inputFilePath, outputFilePath, errorFile)

def processDirectory(inputPath, outputPath, recurse, errorFile):
    
    count, succeeded, failed = 0, 0, 0
    
    for path, dirs, files in os.walk(inputPath):
        
        for file in files:
            if file.endswith(".m3"):
                
                print("\nFile %d:" % count)
                inputFilePath = os.path.join(path, file)
                success = processFile(inputPath, outputPath, inputFilePath, errorFile)
                
                succeeded += success
                failed += not success
                count += 1
        
        if not recurse:
            break
    
    return count, succeeded, failed
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert Starcraft II m3 models to xml format.')
    parser.add_argument('input_path', 
        help='M3 file or directory containing m3 files to convert.')
    parser.add_argument('output_path',
        nargs='?',
        help='Directory for xml file output.')
    parser.add_argument('-r', '--recurse',
        action='store_true', default=False,
        help='Recurse input directory and convert all m3 files found.')
    parser.add_argument('-l', '--error_log',
        help='File to output errors encountered during conversion.')
    
    args = parser.parse_args()
    
    inputPath = args.input_path
    if not os.path.isdir(inputPath) and not os.path.isfile(inputPath):
        sys.stderr.write("input_path %s is not a valid directory or file" % inputPath)
        sys.exit(2)
    
    outputPath = args.output_path
    if outputPath == None:
        if not os.path.isdir(inputPath):
            outputPath = os.path.dirname(inputPath)
        else:
            outputPath = inputPath
    
    recurse = args.recurse
    
    errorFile = None
    errorLog = args.error_log
    if errorLog != None:
        errorFile = open(errorLog, "w")
    
    t0 = time.time()
    print("Started!")
    
    if os.path.isfile(inputPath):
        inputFilePath = inputPath
        inputPath = os.path.dirname(inputPath)
        success = processFile(inputPath, outputPath, inputFilePath, errorFile)
        total, succeeded, failed = 1, success, not success
    else:
        total, succeeded, failed = processDirectory(inputPath, outputPath, recurse, errorFile)
    
    if errorLog != None:
        errorFile.close()
    
    t1 = time.time()
    print("\nFinished!")
    print("%d files found, %d succeeded, %d failed in %.2f s" % (total, succeeded, failed, (t1 - t0)))
