#!C:\Python27\python.exe

# Copyright (C) 2014 TTTech Computertechnik AG. All rights reserved
# Schoenbrunnerstrasse 7, A--1040 Wien, Austria. office@tttech.com
#
#++
# Name
#    MotionWise_postinstall.py
#
# Purpose
#    postinstall (and uninstall) script for the TTTech MotionWise Python Tools
#
# Author
#    Bernhard Leiner <bernhard.leiner@tttech-automotive.com>
#
# Revision Dates
#    09-Feb-2016 (HLI) taken form zFAS
#    09-Feb-2016 (HLI) adapted MotionWise structure
#
#--

from   __future__ import absolute_import, division, print_function, unicode_literals

__version__ = "1.0.1"
__doc__     = """Script for MotionWise post installation processes - install and remove"""

import os
import re
import sys
import site
import time
import shutil

def install ():
    dst = os.path.abspath( os.path.join( site.getsitepackages()[1], "MotionWise", "Contract_Header" ) )

    if os.path.isdir( dst ) :
        for entry in os.listdir( dst ) :
            shutil.rmtree( os.path.join( dst, entry ) )
        os.rmdir( dst )

    time.sleep( 0.5 )

    if not os.path.isdir( dst ) :
        os.mkdir( dst )
    directory_created( dst )

    # print( dst )
    
    cwd  = os.getcwd()
    
    sep = ""
    while True :
        if os.getcwd().endswith( "0200_Platform" ) \
        or os.getcwd().endswith( "0600_Utils" ) :
            os.chdir( cwd )
            break
            
        if os.getcwd().endswith( ":\\" ) or os.getcwd() == "/" :
            sep = None
            break

        os.chdir( ".." )
        sep = os.path.join( sep, ".." )
    
    if sep is not None :
        src = os.path.join( os.getcwd(), sep, "..", "0900_System", "02_interfaces" )
        
        if os.path.exists( src ) :
            for entry in os.listdir( src ) :
                if os.path.exists( os.path.join( src, entry, "ContractHeader", "Ra_Type.py" ) ) :
                    if not os.path.isdir( os.path.join( dst, entry ) ) :
                        os.mkdir( os.path.join( dst, entry ) )

                    shutil.copy( os.path.join( src, entry, "ContractHeader", "Ra_Type.py" )
                                 , os.path.join( dst, entry ) )
                    directory_created( os.path.join( dst, entry ) )

                    file_created( os.path.join( dst, entry, "Ra_Type.py" ) )
                    file_created( os.path.join( dst, entry, "Ra_Type.pyc" ) )
                    file_created( os.path.join( dst, entry, "Ra_Type.pyo" ) )
        
        else :
            # the release package has not the proper path/file structure
            # are we in the repository?
            branch = os.sep
            if branch == "\\" :
                branch = "\\%s" % branch
            branch = "(?<=0200_Platform%s).*?(?=%s0230_Tools)" % ( branch, branch, )
            branch = re.search( branch, os.getcwd() )

            if branch is None :
                # if the installer is not located in the Platform/Tools path
                # us the trunk
                branch = "trunk"
            else :
                branch = branch.group( 0 )
            
            src = os.path.join( os.getcwd(), sep, "..", "0900_SystemVariants", "02_interfaces", "Contract_Header" )
            
            if os.path.exists( src ) :
                for entry in os.listdir( src ) :
                    if os.path.exists( os.path.join( src, entry, "Ra_Type.py" ) ) :
                        if not os.path.isdir( os.path.join( dst, entry ) ) :
                            os.mkdir( os.path.join( dst, entry ) )

                        shutil.copy( os.path.join( src, entry, "Ra_Type.py" )
                                     , os.path.join( dst, entry ) )

                        directory_created( os.path.join( dst, entry ) )

                        file_created( os.path.join( dst, entry, "Ra_Type.py" ) )
                        file_created( os.path.join( dst, entry, "Ra_Type.pyc" ) )
                        file_created( os.path.join( dst, entry, "Ra_Type.pyo" ) )
            else :
                print( "\nWARNING: no contract headers found in repo" )
    else :
        print( "\nWARNING: no contract headers found" )
    
    # Workaround for Python bug http://bugs.python.org/issue15321
    # to avoid cryptic 'lost sys.stderr' message in Installer
    if sys.stdout.fileno() != -2:
        print( "TTTech MotionWise Python Tools successfully installed" )

# end def

def uninstall ():
    print( "TTTech MotionWise Python Tools successfully removed" )
# end def


if __name__ == "__main__":
    # This script is run from inside the bdist_wininst created
    # binary installer or uninstaller, the command line args are either
    # '-install' or '-remove'.
    {"-install" : install , "-remove" : uninstall}[sys.argv[1]]()
