#!C:\Python27\python.exe

# Copyright (C) 2014 TTTech Computertechnik AG. All rights reserved
# Schoenbrunnerstrasse 7, A--1040 Wien, Austria. office@tttech.com
#
#++
# Name
#    MotionWise_ODX_Flash_Convert.py
#
# Purpose
#    Script for preparing an ODX Flash container for USB flashing
#
# Author
#    Bernhard Leiner <bernhard.leiner@tttech-automotive.com>
#
# Revision Dates
#    09-Feb-2016 (HLI) taken from zFAS
#
#--

__version__ = "2.4.2"
__doc__     = """Script for preparing an ODX Flash container for USB flashing"""

import os
import shutil
import binascii
import argparse
import textwrap
import xml.etree.ElementTree
import ConfigParser
import hashlib

class Container (object):
    idents = ("F187", "F189", "F191", "F1A3")
    short_names_mapping = { "EI_VWSparePartNumbe":       "F187"
                          , "EI_VWAppliSoftwVersiNumbe": "F189"
                          , "EI_VWECUHardwNumbe":        "F191"
                          , "EI_VWECUHardwVersiNumbe":   "F1A3"
                          }

    def __init__ (self, spare_part_number, hw_version, bootloader, expected_idents):
        self.spare_part_number = spare_part_number
        self.bootloader        = bootloader 
        self.hw_version        = hw_version
        self.expected_idents   = expected_idents
        self.blocks            = []
        self.consistency_check()

    def consistency_check (self):
        # restrict number of possible entries per ident. 
        # we only reserve one character for the number of idents
        assert not any (len(x) > 9 for x in self.expected_idents.values())

    @property
    def summary_line (self):
        # first line of the summary
        line = "".join( [ "#IDENTS:"] +
                        [ "%d%s" % (len(self.expected_idents[x]), "".join(self.expected_idents[x]))
                           for x in Container.idents
                        ]
                      )
        return line + "\r\n"

class LogicalBlock (object):
    
    def __init__ (self, ID, data_ref, data, start_address, size, crc, version, bootloader):
        self.ID                = ID
        self.data_ref          = data_ref
        self.data              = data
        self.start_address     = start_address
        self.size              = size
        self.crc               = crc
        self.bootloader        = bootloader
        if version:
            # version specified in OWN-IDENT
            self.version = version
        else:
            if not self.special_block:
                self.version = binascii.a2b_hex(self.data[-8:])
            else:
                self.version = "0000"

    @property
    def summary_line (self):
        # file format for summary file:
        # <start address>,<size>,<crc>,<name of binary file>,<version>
        #
        # for example:
        # 60,1178110,BB09202A,EMEM_SPRPRT00002_0002.FD_04FLASHDATA.bin,Z001
        # 03,246071,91312574,EMEM_SPRPRT00002_0002.FD_03FLASHDATA.bin,Z001
        # ...
        return "%s,%s,%s,%s,%s\r\n" % ( self.start_address
                                      , self.size
                                      , self.crc
                                      , self.bin_file
                                      , self.version
                                      )

    @property
    def bin_file (self):
        return "%s.bin" % self.data_ref.split('.')[1]

    @property
    def special_block (self):
        """identify special logical blocks without regular version info"""
        return any(x in self.ID for x in ("FFERASEPROGRROUTI", "SSHTFFSCLEAN"))

    def version_check (self):
        """run a version check and print a warning if something looks wrong"""
        if not self.special_block:
            if  (  ((self.version[0] not in ('X', 'Y', 'Z')) and not self.version[0].isdigit())  # X, Y, Z, or digit
                    or not self.version[1:].isdigit()                                            # digits for remaining
                ):
                print ( 'Warning: invalid version "%s" for logical block %s detected.'
                        % (self.version, self.ID)
                      )
                self.version = "0000"
                return
            bin_version_trailer = binascii.a2b_hex(self.data[-8:])
            if self.version != bin_version_trailer:
                print ( 'Warning: version info "%s" which is appended to the binary data \n'
                        '    for logical block %s \n'
                        '    does not match the ODX OWN-IDENT settings "%s".'
                        % (bin_version_trailer, self.ID, self.version)
                    )

class ZUG (object): 

    top_level_dir = "MotionWise_ZUG"
    metadata_file = os.path.join(top_level_dir, "metainfo2.txt")
    hardware_index_mapping = {"all": 0, "A03": 1, "B01": 2, "B02": 3}   # mapping of HW versions to indices
    
    def __init__ (self, name = "MotionWise"):
        self.devices = []
        self.metadata = ConfigParser.SafeConfigParser()
        self.metadata.optionxform = str  # disable conversion of options to lower case characters

    @staticmethod
    def device_dir (container):
        return "MotionWise_%s" % container.spare_part_number

    def create (self, container, tmp_dir):
        # MotionWise_SparePartNumber
        #       Log Block Name
        #               hardware index (hw version)
        #                       01 -> B02
        dev = Device (self.device_dir (container))
        self.devices.append(dev)
        for b in container.blocks:
            module = Module (b.ID.split(".")[-1], b)
            index = HardwareIndex (ZUG.hardware_index_mapping [container.hw_version], 
                                   tmp_dir, b.bin_file)
            module.indices.append (index)
            dev.modules.append (module)

    def write (self):
        self.add_global_metadata ()
        for dev in self.devices:
            var_dir = os.path.join(ZUG.top_level_dir, dev.name)
            if not os.path.exists (var_dir):
                os.makedirs (var_dir)
            for module in dev.modules:
                for index in module.indices:
                    path = os.path.join (var_dir, module.name, str(index.index), "default")
                    if not os.path.exists(path):
                        os.makedirs (path)
                    # move bin file from tmp dir into path
                    try:
                        shutil.move (os.path.join (index.tmp_dir, index.bin_file), path)
                    except:
                        # XXX error message (file already exists)
                        pass
                    self.add_module_metadata ( dev, module, index
                                             , os.path.join (path, index.bin_file)
                                             )
        self.write_metadata()

    def add_global_metadata (self):
        # XXX always delete metadata file
        if os.path.exists (ZUG.metadata_file):
            os.remove (ZUG.metadata_file)

        self.metadata.add_section("common")
        self.metadata.set("common", "vendor", "TTTech") 
        self.metadata.set("common", "vendor", "TTTech") 


    def add_module_metadata (self, dev, module, index, bin_file):
        section = "\\".join((dev.name, module.name, str(index.index), "default",
                            "Application" if not module.block.bootloader else "Bootloader"))
        self.metadata.add_section(section)

        self.metadata.set(section, "FileName", '"%s"' % index.bin_file)
        self.metadata.set(section, "FileSize", '"%d"' % os.path.getsize(bin_file))
        with open (bin_file, "rb") as f:
            sha1 = hashlib.sha1(f.read())
            self.metadata.set(section, "CheckSum", '"%s"' % sha1.hexdigest())

    def write_metadata (self):
        with open (ZUG.metadata_file, "wb") as f:
            self.metadata.write(f)


class Device (object):

    def __init__ (self, name):
        self.name = name
        self.modules = []

class Module (object):

    def __init__ (self, name, block):
        self.name = name
        self.block = block  # Block instance, corresponds to logical block in ODX
        self.indices = []

class HardwareIndex (object):

    def __init__ (self, index, tmp_dir, bin_file):
        self.index = index
        self.tmp_dir = tmp_dir
        self.bin_file = bin_file



def prepare_odx_file (subdir, odx_file):
    """extract bin data from odx file and write them into binary files. Also creates
       a temporary ODX file which contains only a small subset of the binary data. 
       This is needed to avoid out of memory errors when parsing the XML files with
       256MB logical blocks.
    """
    tmp_file = "tmp_" + os.path.basename(odx_file)
    with open (odx_file, "r") as odx_in, open (tmp_file, "w") as odx_out:
        for l in odx_in:
            if "<FLASHDATA ID=" in l:
                binary_file = l.split()[1].split(".")[-1][:-1] + ".bin"
            elif "<DATA>" in l:
                # write binary data
                with open (os.path.join(subdir, binary_file), "wb") as bin_f:
                    # write in chunks of 10 MB
                    start_offset = 20
                    end_offset   = 20
                    final_offset = len(l) - len("</DATA>\n")
                    while (end_offset < final_offset):
                        end_offset = end_offset + (10*1024*1024)
                        if end_offset > final_offset:
                            end_offset = final_offset
                        bin_f.write(binascii.a2b_hex(l[start_offset:end_offset]))
                        start_offset = end_offset
                # Attention!  The tmp odx file only contains (at most) the last
                # 100 bytes of the data. This is enough to contain the complete trailer
                if not "<DATA>" in l[-100:] :
                    l = "<DATA>" + l[-100:]
            odx_out.write(l)
    return tmp_file


def parse_odx (odx_file):
    tree = xml.etree.ElementTree.parse (odx_file)
    root = tree.getroot ()

    flash = root.find ("./FLASH")
    spare_part_number = flash.attrib["ID"].split("_")[1]
    hw_version        = flash.attrib["ID"].split("_")[3][3:6]
    bootloader        = True if flash.attrib["ID"].split("_")[3][0:3] == "FBL" else False

    mem = root.findall ("./FLASH/ECU-MEMS/ECU-MEM")[0]

    expected_idents = {x: [] for x in Container.idents}
    for session in mem.findall ("./MEM/SESSIONS/SESSION"):
        for ei in session.findall ("./EXPECTED-IDENTS/EXPECTED-IDENT"):
            rdid = Container.short_names_mapping[ei.find ('SHORT-NAME').text]
            for ident in ei.findall ("./IDENT-VALUES/IDENT-VALUE"):
                expected_idents[rdid].append(ident.text)
    container = Container (spare_part_number, hw_version, bootloader, expected_idents)

    flashdatas = { flashdata.attrib['ID']: flashdata.findall ("./DATA")[0].text 
                   for flashdata in mem.findall ("./MEM/FLASHDATAS/FLASHDATA")
                 }
    for datablock in mem.findall ("./MEM/DATABLOCKS/DATABLOCK"):
        ID = datablock.attrib["ID"]
        # find referenced flashdata
        data_ref = datablock.findall ("./FLASHDATA-REF")[0].attrib["ID-REF"] 
        # extract segment info (there is only a single segment allowed)
        segment       = datablock.findall ("./SEGMENTS/SEGMENT")[0]
        start_address = segment.find ('SOURCE-START-ADDRESS').text
        size          = segment.find ('UNCOMPRESSED-SIZE').text
        # get CRC for data
        short_name = datablock.find ('SHORT-NAME').text
        for session in mem.findall ("./MEM/SESSIONS/SESSION"):
            for security_data in session.findall ("./SECURITYS/SECURITY"):
                if security_data.find ('VALIDITY-FOR') is not None :
                    if ( short_name == security_data.find ('VALIDITY-FOR').text ):
                        crc = security_data.find ('FW-CHECKSUM').text
                        break
                    else:
                        crc = None
        # get OWN-IDENTS (actually just the logical block version)
        version = None
        for own_ident in datablock.findall ("./OWN-IDENTS/OWN-IDENT"):
            if "VWLogicSoftwBlockVersi" in own_ident.attrib["ID"]:
                version = own_ident.find ("IDENT-VALUE").text
                break

        container.blocks.append ( LogicalBlock( ID, data_ref, flashdatas[data_ref]
                                              , start_address, size, crc, version
                                              , bootloader
                                              )
                                )
    return container


def USB_summary_convert (subdir, config, container, tmp_dir, summary):
    # write all collected metadata into a config file which is very easy to parse
    with open (os.path.join(subdir, config), "wb") as f:
        if summary:
            f.write(container.summary_line)
        for block in container.blocks:  # don't sort, use the same order as in the ODX container
            print "Processing logical block %s" % block.ID
            block.version_check()
            # add line to ODX_summary
            f.write (block.summary_line)
            # move bin file from tmp dir into subdir
            shutil.move (os.path.join (tmp_dir, block.bin_file), subdir)

def ZUG_convert (zug, container, tmp_dir):
    zug.create (container)
    zug.write (tmp_dir)


def main ():
    description = """\
    This script can be used to convert an ODX flash container into separate binary
    files and a summary file. These files can be used as input files for the MotionWise
    Altera bootloader update application.
    """

    parser = argparse.ArgumentParser \
            ( formatter_class = argparse.RawDescriptionHelpFormatter
            , description = textwrap.dedent (description)
            )

    parser.add_argument \
            ( "-v", "--version"
            , action = "version"
            , version="MotionWise_ODX_Flash_Convert %s" % (__version__, )
            )

    parser.add_argument \
            ( "-s", "--subdir"
            , action = "store_true"
            , help = "create subdirectory for generated files"
            )

    parser.add_argument \
            ( "-e", "--expected_idents"
            , action = "store_true"
            , help = "create expected idents line in ODX_summary.txt"
            )

    parser.add_argument \
            ( "-z", "--zug"
            , action = "store_true"
            , help = "(experimental) convert into ZUG structure"
            )

    parser.add_argument \
            ( "odx"
            , metavar = "ODX_CONTAINER"
            , nargs= "+"
            , help = "ODX flash container with embedded binaries"
            )

    args = parser.parse_args ()


    containers = [] # XXX named tupple!!
    for odx in args.odx:
        tmp_dir = "tmp_bin" + os.path.basename(odx[:-4])
        if os.path.exists (tmp_dir):
            shutil.rmtree (tmp_dir)
        os.mkdir (tmp_dir)

        tmp_odx = prepare_odx_file(tmp_dir, odx)
        containers.append((odx, parse_odx(tmp_odx), tmp_dir))
        os.remove (tmp_odx)

    if not args.zug:
        for container in containers:
            if args.subdir:
                subdir, _ = os.path.splitext(os.path.basename(container[0]))
                if os.path.exists (subdir):
                    print "Deleting existing %s directory..." % (subdir, )
                    shutil.rmtree(subdir)
                os.mkdir(subdir)
            else:
                subdir = ""
            USB_summary_convert( subdir, "ODX_summary.txt"
                            , container[1]
                            , container[2]
                            , args.expected_idents
                            )
    else:
        zug = ZUG()
        for container in containers:
            device_dir = os.path.join(ZUG.top_level_dir, ZUG.device_dir (container[1]))
            zug.create(container[1], container[2])
        zug.write()

    for (_, _, tmp_dir) in containers:
        shutil.rmtree (tmp_dir)

if __name__ == "__main__":
    main ()

