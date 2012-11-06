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


def indent(level):
    return "\t" * level

def openTag(name):
    return "<%s>" % name

def closeTag(name):
    return "</%s>\n" % name

def openCloseTag(name):
    return "<%s />\n" % name


def printXmlElement(out, level, name, value):
    out.write(indent(level) + openTag(name) + value + closeTag(name))

def printObject(out, level, name, object):
    
    otype = type(object)
    
    if otype is type(None):
        out.write(indent(level) + openCloseTag(name))
        return
    
    elif otype is int:
        value = hex(object)
        printXmlElement(out, level, name, value)
        return
    
    elif otype is bytearray or otype is bytes:
        value = byteDataToHex(object)
        printXmlElement(out, level, name, value)
        return
    
    elif otype is list:
        out.write(indent(level) + openTag(name) + "\n")
        
        for entry in object:
            printObject(out, level + 1, name + "-element", entry)
        
        out.write(indent(level) + closeTag(name))
        return
    
    elif hasattr(otype, "fields"):
        out.write(indent(level) + openTag(name) + "\n")
        
        for field in object.fields:
            value = getattr(object, field)
            printObject(out, level + 1, field, value)
        
        out.write(indent(level) + closeTag(name))
        return
    
    else:
        value = str(object)
        printXmlElement(out, level, name, value)
        return

def printModel(model, outputFilePath):
    outputStream = io.StringIO()
    
    outputFile = open(outputFilePath, "w")
    
    printObject(outputStream, 0, "model", model)
    
    outputFile.write(outputStream.getvalue())
    outputFile.close()
    
    outputStream.close()


def convertFile(inputFilePath, outputFilePath, errorFile):    
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
    return True

def processFile(inputPath, outputDirectory, inputFilePath, errorFile):
    relativeInputPath = os.path.relpath(inputFilePath, inputPath)
    relativeOutputPath = relativeInputPath + ".xml"
   
    if outputDirectory:
        if outputDirectory and not os.path.exists(outputDirectory):
            os.makedirs(outputDirectory)
        outputFilePath = os.path.join(outputDirectory, relativeOutputPath)
    else:
        outputFileName = inputFilePath + ".xml"
    
    print("%s -> %s" % (inputFilePath, outputFilePath))

    return convertFile(inputFilePath, outputFilePath, errorFile)

def processDirectory(inputPath, outputPath, recurse, errorFile):
    
    count, succeeded, failed = 0, 0, 0
    
    for path, dirs, files in os.walk(inputPath):
        
        for file in files:
            if file.endswith(".m3"):
                
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
    parser.add_argument('path', nargs='+', help="Either a *.m3 file or a directory with *.m3 files")
    parser.add_argument('--output-directory', 
        '-o', 
        help='Directory in which m3 files will be placed')
    parser.add_argument('-r', '--recurse',
        action='store_true', default=False,
        help='Recurse input directory and convert all m3 files found.')
    parser.add_argument('-l', '--error_log',
        help='File to output errors encountered during conversion.')
    
    args = parser.parse_args()
    
    outputDirectory = args.output_directory
    if outputDirectory != None and not os.path.isdir(outputDirectory):
        sys.stderr.write("%s is not a directory" % outputDirectory)
        sys.exit(2)
        
    for path in args.path:
        if not os.path.isdir(path) and not os.path.isfile(path):
            sys.stderr.write("Path %s is not a valid directory or file" % path)
            sys.exit(2)
    
    recurse = args.recurse
    
    errorFile = None
    errorLog = args.error_log
    if errorLog != None:
        errorFile = open(errorLog, "w")
    
    t0 = time.time()
    print("Converting files..")
    for path in args.path:
        total, succeeded, failed = (0, 0, 0)
        if os.path.isfile(path):
            inputFilePath = path
            path = os.path.dirname(path)
            success = processFile(path, outputDirectory, inputFilePath, errorFile)
            totalDelta, succeededDelta, failedDelta = 1, success, not success
        else:
            totalDelta, succeededDelta, failedDelta = processDirectory(path, outputDirectory, recurse, errorFile)
        total += totalDelta
        succeeded += succeededDelta
        failed += failedDelta
    if errorLog != None:
        errorFile.close()
    
    t1 = time.time()
    print("%d files found, %d converted, %d failed in %.2f s" % (total, succeeded, failed, (t1 - t0)))
    if failed > 0:
        sys.exit(1)