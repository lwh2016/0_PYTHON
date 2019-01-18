#!C:\Python27\python.exe

# Copyright (C) 2014 TTTech Computertechnik AG. All rights reserved
# Schoenbrunnerstrasse 7, A--1040 Wien, Austria. office@tttech.com
#
#++
# Name
#    MotionWise_Routing.py
#
# Purpose
#    Script for MotionWise Routing Configuration
#
# Author
#    Bernhard Leiner <bernhard.leiner@tttech-automotive.com>
#
# Revision Dates
#    09-Feb-2016 (HLI) taken from zFAS
#
#--

from __future__ import absolute_import, division, print_function, unicode_literals

__version__ = "1.0.5"
__doc__     = """Script for MotionWise routing configuration"""

import sys
import os
import time
import argparse
import textwrap

# special handling if script is directly used inside the TTTech MotionWise repository
parent_dir = os.path.join (os.path.dirname (os.path.abspath (__file__)), "..")
if not os.path.exists (os.path.join (parent_dir, "lib", "site-packages")):
    # looks like we are NOT running from the regular install location
    sys.path.append (parent_dir)

from MotionWise.RA import RA
from MotionWise.RA import RA_Args
from MotionWise.RA import Ra_Enum
from MotionWise.RA import Ra_Config_Log_Level
from MotionWise.RA import Ra_Config_Log_Sink
from MotionWise.RA import Ra_Config_Routing_Mode

def main():
    description = """\
    This script can be used to configure the MotionWise Rte message routing. It enables 
    the user to set SW-Cs into a specific operation mode. These modes are:

      * default: Default routing for the messages sent by the SW-C. Messages are
                 delivered to the receivers on the MotionWise but are not routed to
                 the debug port.
      * record:  In this mode, all Rte messages are sent to the internal MotionWise 
                 receivers and also to the debug port. This mode is intended to
                 be used for recording or inspecting internal Rte communication.
      * replay:  In this mode all messages sent by the SW-C are discarded by the
                 middleware. Neither intra nor inter host communication on the
                 MotionWise is enabled. Use this mode if you like to feed in the output 
                 messages of a SW-C via the debug Ethernet port.

    Some examples:

        Reset the middleware routing configuration to the default values:
            MotionWise_Routing.py -r

        Set SWC CpApEML to record:
            MotionWise_Routing.py -s CpApEML -m record

        Set all SWCs to record:
            MotionWise_Routing.py -s all -m record
    """
    
    parser = argparse.ArgumentParser \
            ( formatter_class = argparse.RawDescriptionHelpFormatter
            , description = textwrap.dedent (description)
            )

    parser.add_argument \
            ( "-v", "--version"
            , action = "version"
            , version = "MotionWise_Routing v%s" % (__version__, )
            )

    parser.add_argument \
            ( "-r", "--reset"
            , action = "store_true"
            , help = "Reset the complete routing configuration to default values."
            )

    parser.add_argument \
            ( "-s", "--swcs"
            , metavar = "SWCID", nargs = "+"
            , help = "Specifies the routing for one or multiple SWCs. Use 'all' "
                     "to select all SWCs."
            )

    parser.add_argument \
            ( "-m", "--mode"
            , choices = [str(s) for s in Ra_Enum.enums (Ra_Config_Routing_Mode)]
            , help = "Specifies the operation mode."
            )

    devel = parser.add_argument_group ("optional developer/test arguments")

    devel.add_argument \
            ( "-p", "--ports"
            , type = int
            , metavar = "PORTID", nargs = "+"
            , help = "Specifies the routing for Ports"
            )

    devel.add_argument \
            ( "-f", "--frames"
            , type = int
            , metavar = "FRAMEID", nargs = "+"
            , help = "Specifies the routing for Frames"
            )
    
    RA_Args (parser)            # add RA library cmd arguments
    args = parser.parse_args () # parse the command line
    ra = RA (parser, args)      # check and load RA library
    
    # --- check command line arguments ---
    
    # parse MotionWise log script specific command line options
    reset  = args.reset
    mode   = args.mode
    ports  = args.ports  if args.ports  else []
    frames = args.frames if args.frames else []
    
    # check swcs for validity and convert names into IDs
    swcs = []
    if args.swcs is not None :
        for s in args.swcs :
            if s == "all":
                swcid = 254
            elif s in ra.get_swc_names() :
                swcid = ra.get_swc_id_of_swc_name( s )
            else :
                try :
                    swcid = int( s )
                except ValueError :
                    parser.error( "invalid SWC ID -s argument '" + str( s ) + "'" )
                if swcid not in ra.get_swc_ids() :
                    parser.error( "invalid SWC ID -s argument '" + str( s ) + "'" )
            swcs.append (swcid)
        swcs = sorted (set (swcs))
        # 'all' includes all other SW-Cs
        if 254 in swcs:
            swcs = ra.get_swc_ids()

    if (swcs or ports or frames):
        if not mode:
            parser.error ("Specify a mode for configuration.")
    
    # --- perform the requested action from the command line options ---
    
    if mode and not (swcs or ports or frames) :
        parser.error( "Neither a SWC, port nor frame was specified to configure the requested mode. Please use at least the '-s' option to specify a SWC for configuration." )

    if not mode and not (swcs or ports or frames) :
        parser.error( "Please provide a configuration (see '-h')." )
        
    if reset:
        ra.config_routing_reset()
    
    for swc in swcs:
        ra.config_routing_swc (swc, mode)
    for port in ports:
        ra.config_routing_port (port, mode)
    for frame in frames:
        ra.config_routing_frame (frame, mode)

    ra.config_routing_sync()


    # prevent script from exiting
    print ("Press Ctrl-C to stop.")
    try:
        while (True):
            time.sleep( 1 )
    except KeyboardInterrupt as e:
        pass
    finally:
        # send a reset of the routing configuration 
        # to stop sending record frames
        ra.config_routing_reset()
        ra.config_routing_sync()
    
if __name__ == "__main__" :
    main()

