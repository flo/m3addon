Features
--------

The Python scripts can be used as a Blender addon.

Currently the following content can be exported and imported:

  * Animations
  * Meshes with up to 4 UV layers
  * All known M3 materials:
      * standard materials
      * displacement materials
      * composite materials
      * terrain materials
      * volume materials
  * M3 particle systems
  * M3 forces
  * M3 attachment points and volumes
  * M3 cameras
  * M3 lights
  * M3 rigid bodies (simple shapes only)

The script m3ToXml.py can also be used to convert a m3 file into a XML file. It
takes a m3 file as argument and prints the XML on the command line.

The script xmlToM3.py can convert the XML files exported by m3ToXml.py
back into a m3 file.

The file structures.xml gets used by the script generateM3Library.py to create
a blender independent python library for loading and saving m3 files.
Modifying this XML file will have impact of the above scripts and the blender addon.

Installation
------------
1. Clone the git repository of this addon
2. Move the created directory into addons folder of your blender settings:
   * Example for Linux and Blender 2.63: 
      * /home/$user/.blender/2.63/scripts/addons/m3addon
   * Example for Windows XP and Blender 2.63:
      * C:\Documents and Settings\%username%\Application Data\Blender Foundation\Blender\2.63\scripts\addons
   * Example for Windows 7 and Blender 2.63:
      * C:\Users\%username%\AppData\Roaming\Blender Foundation\Blender\2.63\scripts\addons
3. Activate the addon in blender (There is another M3 addon, so watch out!)

See also: http://wiki.blender.org/index.php/Doc:2.6/Manual/Extensions/Python/Add-Ons

Usage
-----

The blender addon adds panels to the scene tab of the properties editor.

To create a particle system and preview it in the Starcraft 2 editor you can perform the following steps:

1. Add a animation sequence by clicking on "+" in the "M3 Animation Sequences" panel
2. Add a material by clicking on "+" in the "M3 Materials" panel
3. Select a diffuse image:
3.1 Select "Diffuse" in the "M3 Materials Layer" panel
3.2 Specify a image path like "Assets/Textures/Glow_Blue2.dds" in the "M3 Materials Layer" panel
4. Add a particle system by clicking on "+" in the "M3 Particle Systems" panel
5. Validate that your particle system has a valid material selected
6. Specifiy an absolute file path in the "M3 Quick Export" panel
7. Click on "Export As M3" in the "M3 Quick Export" panels
8. Open the previewer in the Starcraft 2 editor by using the menu "Window/Previewer"
9. Use the previewer menu "File/Add File" to preview the exported model in the SC2 Editor

Some Blender Tipps:
-----------
* You can right click on UI elements to view the source code which displays that element. 
* File/Save User Settings can be used to determine the default state of blender.
  * You can save your export path this way!
  * You can make yourself a default view which shows SC2 properties panels where you want them

About the Implementation
------------------------

* The file structures.xml specifies how the script should parse and export a M3 file
* The script generateM3Library.py generates the file m3.py which is a python library for loading and saving m3 files.
* The importing of m3 files works like this:
  1. The method loadModel of the m3.py file gets called to create a python data structure of the m3 file content.
  2. This data structure gets then used to create corresponding blender data structures
* The exporing works the other way round:
  1. The data structures of blender gets used to create m3.py data structures that represent a m3 file.
  2. The method saveAndInvalidateModel of the m3.py file gets used to convert the latter data structure into a m3 file.


Common Errors and how to fix them
---------------------------------
* Error message "Exception: XYZ_V4.unknown0 has value 42 instead of the expected value int(0)":
    * In the structure.xml file it's configured what structures exists, what fields those structures have,
      and what their default or expected value is. The exceptions means, that the field "unknown0" of the structure "XYZ_" has
      been configured in the structure.xml file to be 0, but it was actually 42. For each structure exists an XML
      element in the structure.xml file. Just search for the structure name ("XYZ_" in the example) to find it. In the structure
      xml element there are field elements. To fix the given error message we would search in the structure element for the field with the name attribute "unknown0"
      and would replace the attribute expected-value="0" with default-value="0".
* Error message "Exception: There were 1 unknown sections":
    * The error message means that the m3 file contained a structure that it is unknown to the script since it has not been defined in the structure.xml file.
      You can fix the error message by defining the unknown section. To do that have a look at the log, it will contain a message like this:
         * "ERROR: Unknown section at offset 436124 with tag=XYZ_ version=1 repetitions=2 sectionLengthInBytes=32 guessedUnusedSectionBytes=4 guessedBytesPerEntry=14.0"
      The error message means that it found a section in the m3 file that contains two (repetitions=2) entries of type XYZ_.
      The script guesses that 4 bytes are unused and knowns that the section is 32 bytes long. So it calculates 2*X-4=32 where X is the number of guessed bytes per entry.
      The result of this calculation is printed at the end "guessedBytesPerEntry=14.0". So the script guesses that the structure XYZ_ is 14 bytes long.
      To fix the upper example error message we would add the following xml element to the structure.xml file:
      ``<structure name="XYZ_" version="1" size="14">``
          ``<description>Unknown</description>``
          ``<field name="unknown" size="14" />``
       ``</structure>``
      Note that name, version and size attributes of need to be adjusted to what got reported in the error message.
* Error message "Field ABCDV7.xyz can be marked as a reference pointing to XYZ_V1":
    * To fix this example error message, we would search in the structure.xml file for a structure called "ABCD" with the attribute version="7".
      It will contain a xml element field with the attribute name="xyz". To this field we would add an attribute refTo="XYZ_V1".
* Error message "Exception: Unable to load all data: There were 1 unreferenced sections. View log for details"
    * When this error occurs, you will find in the log a message like this: "WARNING: XYZ_V1 (2 repetitions) got 0 times referenced"
      Every section in a m3 file gets usually referenced exactly 1 time(except for the header). The error message means
      that there is a section that contains 2 structures of type XYZ_ in version 1, but which got not referenced from anywhere.
      Most likely there is actually a reference to this section but which hasn't been configured as such in the structure.xml file.
      If you are lucky, then there will be exactly 1 line below the former warning which looks like this:
      "-> Found a reference at offset 56 in a section of type ABCDV7". To fix the error message we need to change the structure
      definition of ABCD in version 7 to contain a field definition like this:
      `<field offset="56" name="xyzData" type="Reference" refTo="XYZ_V1" />`
      The name of the field can be freely choosen. It can be that the section in which the refernce got found contains
      multiple structures. In that case it can be that the structure with the reference (ABCD in the example) is smaller
      then the found offset. In this case the found reference is not in the first element of the section, but in a later one.
      Assume the size of ABCD in version 7 would be 40. Then the offset 56 would mean that the second element of type ABCD has at
      the relative offset 16 a reference to XYZ_V1. In that case the added field xml element would have the value 16 as offset.


License (GPL 2.0 or later)
--------------------------

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software Foundation,
Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.