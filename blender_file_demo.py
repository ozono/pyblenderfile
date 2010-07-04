#!/usr/bin/python
# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
# Purpose:       Blender_file class usage
# Author:        Ozono Multimedia S.L.L.
# Created:       26/06/2010
# Copyright:     (c) 2010
# License:       GNU GPLv3 (read license.txt)
# Comments:
#-------------------------------------------------------------------------------

from blender_file import Blender_file

bf = Blender_file("test.blend")

'''File data'''
print bf.header

'''Generating and saving doc'''
data = bf.get_doc(development=True)
f = open("doc.html", "w")
f.write(data)
f.close()

'''Accessing data'''
lst_obs = bf.get_objects("Mesh")
for ob in lst_obs:
    print ob.id.name
    print ob.mvert