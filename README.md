Features
--------

The python scripts can be used as a blender addon.

Currently the following content can be exported:

  * Up to one animated mesh made out of triangles with 1 UV layer
  * Animated M3 standard materials
  * Animated M3 particle systems
  * Animated M3 attachment points and volumes

The following content can be imported:

  * Animated meshes with 1 UV layer
  * Animated M3 standard materials
  * Animated M3 particle systems
  * Animated M3 attachment points and volumes

The script printXml.py can also be used to convert a m3 file into a XML file. It
takes a m3 file as argument and prints the XML on the command line.

The script xmlToM3.py should not be used, but could theoretically convert a
XML file exported by printXml.py back into a m3 file.

The file structures.xml gets used by the script generateM3Library.py to create
a blender independent python library for loading and saving m3 files.
Modifying this XML file will have impact of the above scripts and the blender addon.

Installation
------------
1. Clone the git repository of this addon
2. Move the created directory into addons folder of your blender settings:
   * Example for Linux and Blender 2.62: 
      * /home/$user/.blender/2.62/scripts/addons/m3addon
   * Example for Windows XP and Blender 2.62:
      * C:\Documents and Settings\%username%\Application Data\Blender Foundation\Blender\2.62\scripts\addons
   * Example for Windows 7 and Blender 2.62:
      * C:\Users\%username%\AppData\Roaming\Blender Foundation\Blender\2.62\scripts\addons
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