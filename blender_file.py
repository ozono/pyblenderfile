#!/usr/bin/python
# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
# Purpose:       Blender file reading
# Version:       1.0b
# Author:        Ozono Multimedia S.L.L.
# Created:       26/06/2010
# Copyright:     (c) 2010
# License:       GNU GPLv3 (read license.txt)
# Comments:      Thanks to Jeroen Bakker (http://www.atmind.nl/blender) for his
#                good blender file format description.
#-------------------------------------------------------------------------------

# TODO: Implement cached access to objects (for large .blend files)

import re
import struct

class B_f_header:

    def __init__(self):

        '''File identifier (always 'BLENDER')'''
        self.identifier = None
        '''Size of a pointer; all pointers in the file are stored in this
        format. '_' means 4 bytes or 32 bit and '-' means 8 bytes or 64 bits.'''
        self.pointer_size = None
        '''Type of byte ordering used; 'v' means little endian and 'V' means big
        endian.'''
        self.endiandness = None
        '''Used internally to hold struct endiandness equivalent (< or >)'''
        self.__end = None
        '''Version of Blender the file was created in; '248' means version
        2.48'''
        self.version_number = None

    def __str__(self):

        buffer = ""
        for elem in ["identifier", "pointer_size", "endiandness",
            "version_number"]:
            buffer += elem + ": " + str(self.__dict__[elem]) + "\n"
        return buffer

class B_f_file_block:

    def __init__(self):

        '''Identifier of the file-block'''
        self.code = None
        '''Total length of the data after the file-block-header'''
        self.size = None
        '''Memory address the structure was located when written to disk'''
        self.old_memory_address = None
        '''Index of the SDNA structure'''
        self.sdna_index = None
        '''Number of structure located in this file-block'''
        self.count = None
        '''Where this block data is stored on file'''
        self.data_idx = None
        '''Data refenrences (once parsed)'''
        self.lst_data = []

    def __str__(self):

        buffer = ""
        for elem in ["code", "size", "old_memory_address",
            "sdna_index", "count"]:
            buffer += elem + ": " + str(self.__dict__[elem]) + "\n"
        return buffer

class B_f_sdna_data:

    def __init__(self):

        '''SDNA'''
        self.identifier = None

        self.names = []
        self.types = []
        self.types_len = []
        self.structures = []

    def get_structure_idx_by_type(self, type):

        lst_types = [self.types[s[0]] for s in self.structures]
        return lst_types.index(type)

    def __str__(self):

        buffer = ""
        for elem in ["identifier"]:
            buffer += elem + ": " + str(self.__dict__[elem]) + "\n"
        return buffer

class Blender_file:

    def __init__(self, pth_file):

        self.__lst_blocks = []

        self.__dict_dynamic_classes_by_name = {}

        '''To store objects extracted from file'''
        self.__lst_obs = []

        self.__fh = open(pth_file, "r")

        data = self.__fh.read(12)

        idx = 12

        self.header = self.__B_f_header_from_data(data)

        data = self.__fh.read(16 + self.header.pointer_size)
        idx += 16 + self.header.pointer_size

        while data:

            file_block_header = self.__B_f_file_block_from_data(data)
            file_block_header.data_idx = idx
            self.__lst_blocks.append(file_block_header)
            self.__fh.seek(file_block_header.size, 1)
            idx += file_block_header.size
            data = self.__fh.read(16 + self.header.pointer_size)
            idx += 16 + self.header.pointer_size

        sdna_file_block_header = \
            [b for b in self.__lst_blocks if b.code == "DNA1"][0]

        '''TF'''
        self.__fh.seek(sdna_file_block_header.data_idx, 0)
        data = self.__fh.read(sdna_file_block_header.size)

        self.sdna = self.__B_f_sdna_from_data(data)

        self.__build_classes()
        self.__build_objects()

        self.__fh.close()

    def __B_f_header_from_data(self, data):

        header = B_f_header()
        header.identifier = data[:7]

        header.pointer_size = 4
        pointer_size = data[7:8]
        if pointer_size == "-": header.pointer_size = 8

        header.endiandness = data[8:9]

        if header.endiandness == "v": header.__end = "<"
        else: header.__end = ">"

        header.version_number = data[9:]

        return header

    def __B_f_file_block_from_data(self, data):

        file_block = B_f_file_block()

        file_block.code = data[:4].strip("\0")
        file_block.size = self.__to_integer(data[4:8])
        file_block.old_memory_address = self.__to_integer(
            data[8:8 + self.header.pointer_size])
        file_block.sdna_index = self.__to_integer(
            data[8 + self.header.pointer_size:12 + self.header.pointer_size])
        file_block.count = self.__to_integer(
            data[12 + self.header.pointer_size:])

        return file_block

    def __B_f_sdna_from_data(self, data):

        sdna = B_f_sdna_data()

        idx = 0
        sdna.identifier = data[:idx + 4]
        idx += 4
        '''jump NAME'''
        idx += 4
        number = self.__to_integer(data[idx:idx + 4])
        idx += 4
        sdna.names, idx = self.__string_to_list(data, number, idx)
        '''jump TYPE'''
        idx += data[idx:].find("TYPE") + 4
        number = self.__to_integer(data[idx:idx + 4])
        idx += 4
        sdna.types, idx = self.__string_to_list(data, number, idx)
        '''jump TLEN'''
        idx += data[idx:].find("TLEN") + 4
        for i in range(number):
            sdna.types_len.append(self.__to_integer(data[idx:idx + 2]))
            idx += 2
        '''jump STRC'''
        idx += data[idx:].find("STRC") + 4
        number = self.__to_integer(data[idx:idx + 4])
        idx += 4

        for i in range(number):
            struct_type = self.__to_integer(data[idx:idx + 2])
            idx += 2
            num_fields = self.__to_integer(data[idx:idx + 2])
            idx += 2
            lst_fields = []
            for j in range(num_fields):
                field_type = self.__to_integer(data[idx:idx + 2])
                idx += 2
                field_name = self.__to_integer(data[idx:idx + 2])
                idx += 2
                lst_fields.append([field_type, field_name])
            sdna.structures.append([struct_type, lst_fields])

        return sdna

    def __link_object(self, pointer_id):

        if pointer_id != 0:
            for fb in self.__lst_blocks:
                if fb.old_memory_address == pointer_id:
                    if len(fb.lst_data) > 1: return fb.lst_data
                    else: return fb.lst_data[0]
        if pointer_id != 0:
            '''Maybe residual data ???'''
            #TODO: check
            return "????? (%s)" % pointer_id
        return None

    def __build_classes(self):

        for i, lst_dat in enumerate(self.sdna.structures):
            st_ty, lst_fi = lst_dat
            classname = self.sdna.types[st_ty]
            cls = type(classname, (object,), {})
            self.__dict_dynamic_classes_by_name[classname] = cls

    def __build_objects(self):

        for fb in self.__lst_blocks:

            if fb.code in ["DNA1"]: continue
            elif fb.count < 1: continue

            '''First, we create empty obs, so we can link together while 
            filling'''
            for i in range(fb.count):
                classname = self.sdna.types[
                    self.sdna.structures[fb.sdna_index][0]]
                ob = self.__dict_dynamic_classes_by_name[classname]()
                fb.lst_data.append(ob)
        
        for fb in self.__lst_blocks:

            self.__fh.seek(fb.data_idx, 0)
            data = self.__fh.read(fb.size)
            data_idx = 0

            for ob in fb.lst_data:

                '''Assign data'''
                st_ty, lst_fi = self.sdna.structures[fb.sdna_index]
                for fi_ty, fi_na in lst_fi:
                    type = self.sdna.types[fi_ty]
                    type_len = self.sdna.types_len[fi_ty]
                    name = self.sdna.names[fi_na]
                    val, data_idx = self.__get_field(name, fi_ty,
                        data_idx, data)
                    setattr(ob, self.__to_python_name(name), val)
#                    print "%10s %18s %4s S %4s V %s" % (type,
#                        name, data_idx, type_len, val)
                self.__lst_obs.append(ob)

    def __to_python_name(self, name):

        name = name.replace("*", "")
        if name.find("[") != -1: name = name[:name.find("[")]
        return name

    def __get_field(self, name, idx_type, data_idx, data):

        ma = re.match("^.*\[([0-9]*)\]$", name)
        if ma != None:

            lst_sizes = []
            for val in ma.groups():
                lst_sizes.append(int(val))

            return self.__get_array(name, idx_type, data_idx, data, lst_sizes)

        type_name = self.sdna.types[idx_type]
        type_size = self.sdna.types_len[idx_type]
        if name.startswith("*"): type_size = self.header.pointer_size

        ret_val = None
        if name.startswith("*"):
            ret_val = self.__to_integer(data[data_idx: data_idx + type_size])
            data_idx += type_size
            ret_val = self.__link_object(ret_val)
        elif type_name == "void":
            '''Type is void and not starting with *: we got a method pointer.
            Blender use thin internally. We dismiss this info.'''
            pass
        elif type_name in ["int", "short"]:
            ret_val = self.__to_integer(data[data_idx: data_idx + type_size])
            data_idx += type_size
        elif type_name == "char":
            ret_val = data[data_idx: data_idx + type_size]
            data_idx += type_size
        elif type_name == "float":
            ret_val = struct.unpack(
                self.header.__end + "f",
                data[data_idx: data_idx + type_size])[0]
            data_idx += type_size
        elif type_name == "double":
            ret_val = struct.unpack(
                self.header.__end + "d",
                data[data_idx: data_idx + type_size])[0]
            data_idx += type_size
        else:
            try: struct_idx = self.sdna.get_structure_idx_by_type(type_name)
            except ValueError:
                print "%s of type %s y tam. %s is not a defined struct" \
                    % (name, type_name, type_size)
                data_idx += type_size
                return (None, data_idx)

            ob = self.__dict_dynamic_classes_by_name[type_name]()
            st_ty, lst_fi = self.sdna.structures[struct_idx]
            for fi_ty, fi_na in lst_fi:
                field_type = self.sdna.types[fi_ty]
                field_type_size = self.sdna.types_len[fi_ty]
                field_name = self.sdna.names[fi_na]
                val, data_idx = self.__get_field(field_name, fi_ty, data_idx,
                    data)
                setattr(ob, self.__to_python_name(field_name), val)
#                print "%10s %18s %4s S %4s V %s" % (field_type,
#                    field_name, data_idx, field_type_size,
#                    val)
            ret_val = ob

        return (ret_val, data_idx)

    def __get_array(self, name, idx_type, idx_data, data, lst_sizes,
        lst_sizes_idx=0):

        if lst_sizes_idx >= len(lst_sizes):
            if name.find("[") != -1: name = name[:name.find("[")]
            return self.__get_field(name, idx_type, idx_data, data)

        type = self.sdna.types[idx_type]

        is_char = (type == "char" and lst_sizes_idx == len(lst_sizes) - 1)

        if is_char: lst_tmp = ""
        else: lst_tmp = []

        for i in range(lst_sizes[lst_sizes_idx]):
            lst_tmp_2, idx_data = self.__get_array(name, idx_type, idx_data,
                data, lst_sizes, lst_sizes_idx + 1)
            if is_char:
                lst_tmp += lst_tmp_2
            else: lst_tmp.append(lst_tmp_2)

        if is_char and lst_tmp.find("\0") != -1:
            lst_tmp = lst_tmp[:lst_tmp.find("\0")]
        return (lst_tmp, idx_data)

    def __to_integer(self, data):

        if self.header.endiandness == "V": data = data[::-1]
        int = 0
        i = 0
        for byte in data:
            int += ord(byte) << i
            i += 8
        return int

    '''
    idx = data index
    number = expected elems number
    '''
    def __string_to_list(self, data, number, idx):

        lst_tmp = []
        name_buf = ""
        i = 0
        while len(lst_tmp) < number:
            chr = data[idx + i]
            if chr == "\0":
                lst_tmp.append(name_buf)
                name_buf = ""
            else:
                name_buf += chr
            i += 1
        idx += i
        return (lst_tmp, idx)

    '''For development purposes'''
    def __get_development_doc(self):

        buffer = "<h2>Summary</h2>\n"
        buffer += "<ul>"
        buffer += "<li><a href='#fbd'>File blocks data</a></li>"
        buffer += "<li><a href='#si'>SDNA index</a></li>"
        buffer += "<li><a href='#sm'>SDNA mapping</a></li>"
        buffer += "</ul>\n"
        buffer += "<h2><a name='fbd'>File blocks data</a></h2>\n"
        buffer += "<table>\n"
        buffer += "<thead>\n"
        buffer += "<tr><th>NAME</th><th>SDNA ID</th><th>STRUCT COUNT</th>" + \
            "<th>SIZE</th><th>IDENT</th></tr>"
        buffer += "</thead>\n"
        buffer += "<tbody>\n"
        buffer += "<tbody>\n"
        for block in self.__lst_blocks:
            buffer += ("<tr><td>%s</td><td><a href='#SDNA_ID_%s'>%s</a>" + \
                "</td><td>%s</td><td>%s" + \
                "</td><td>%s</td></tr>") % (block.code, block.sdna_index,
                block.sdna_index, block.count, block.size,
                block.old_memory_address)
        buffer += "</tbody>\n"
        buffer += "<table>\n"

        return buffer

    '''Generate readable SDNA'''
    def get_doc(self, development=False):

        buffer = self.__get_doc_header()
        buffer += ("<h1><a name='TOP'>Object types in Blender %s file </a>" + \
            "</h1>\n") % self.header.version_number
        if development: buffer += self.__get_development_doc()
        buffer += self.__get_base_doc()
        buffer += self.__get_doc_footer()
        return buffer

    def __get_doc_header(self):

        buffer = ""
        buffer += "<html>\n"
        buffer += "<head>\n"
        buffer += "<title>Blender file doc</title>\n"
        buffer += "<style>\n"
        buffer += """
        body {font-family:verdana;font-size: 14px;}
        table {font-size: 12px;border-collapse:collapse;}
        thead {background:#CCC;}
        th {padding:5px;}
        td {border-bottom:1px solid #CCC;padding:5px;}
        """
        buffer += "</style>\n"
        buffer += "</head>\n"
        buffer += " <body>\n"
        return buffer


    def __get_base_doc(self):

        buffer = "<h2><a name='si'>SDNA index</a></h2>\n"
        buffer += "<p>"
        for i, lst_dat in enumerate(self.sdna.structures):
            st_ty, lst_fi = lst_dat
            buffer += "<b>(%s)</b> <a href='#SDNA_ID_%s'>%s</a>, " \
                % (i, i, self.sdna.types[st_ty])
        buffer += "</p>\n"

        buffer += "<h2><a name='sm'>SDNA mapping</a></h2>\n"
        for i, lst_dat in enumerate(self.sdna.structures):
            st_ty, lst_fi = lst_dat
            offset = 0
            buffer += ("<h3><a name='SDNA_ID_%s'>(%s) %s</a> <a " +
                "href='#TOP'>top</a></h3> \n") % (i, self.sdna.types[st_ty], i)
            buffer += "<table>\n"
            buffer += "<thead>\n"
            buffer += "<tr><th>TYPE</th><th>NAME</th><th>SIZE</th><th>" + \
                "OFFSET</th></tr>"
            buffer += "</thead>\n"
            buffer += "<tbody>\n"
            for fi_ty, fi_na in lst_fi:
                type = self.sdna.types[fi_ty]
                type_len = self.sdna.types_len[fi_ty]
                name = self.sdna.names[fi_na]
                if name.startswith("*"): size = self.header.pointer_size
                else: size = type_len
                size_factor = 1
                ma = re.match("^.*\[([0-9]*)\]$", name)
                if ma != None:
                    for val in ma.groups():
                        size_factor *= int(val)
                try:
                    j = [a[0] for a in self.sdna.structures].index(fi_ty)
                    buffer += "<tr><td><a href='#SDNA_ID_%s'>%s</a></td>" \
                        % (j, type)
                except ValueError:
                    buffer += "<tr><td>%s</td>" % (type)
                buffer += ("<td>%s</td><td>%s</td><td>%s" + \
                    "</td></tr>") % (name, size, offset)
                offset += size * size_factor
            buffer += "</tbody>\n"
            buffer += "</table>\n"

        return buffer

    def __get_doc_footer(self):

        buffer = ""
        buffer += "</body></html>"
        return buffer

    def get_objects(self, classname=None):
        
        if classname is None: return self.__lst_obs
        
        lst_objects = []
        for ob in self.__lst_obs:
            if type(ob) == self.__dict_dynamic_classes_by_name[classname]:
                lst_objects.append(ob)
        return lst_objects
