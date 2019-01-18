#!C:\Python27\python.exe

# Copyright (C) 2013 TTTech Computertechnik AG. All rights reserved
# Schoenbrunnerstrasse 7, A--1040 Wien, Austria. office@tttech.com
#
#++
# Name
#    MotionWise_Log.py
#
# Purpose
#    Script for MotionWise Logging and Tracing Configuration
#
# Author
#    Bernhard Leiner <bernhard.leiner@tttech-automotive.com>
#
# Revision Dates
#    09-Feb-2016 (HLI) taken from zFAS
#
#--

from __future__ import absolute_import, division, print_function, unicode_literals

__version__ = "2.0.2"
__doc__     = """Script for MotionWise logging and tracing configuration"""

import sys
import os
import time
import argparse
import textwrap
import functools
import struct
import ctypes

# special handling if script is directly used inside the TTTech MotionWise repository
parent_dir = os.path.join (os.path.dirname (os.path.abspath (__file__)), "..")
if not os.path.exists (os.path.join (parent_dir, "lib", "site-packages")):
    # looks like we are NOT running from the regular install location
    sys.path.append (parent_dir)

from MotionWise.RA import RA
from MotionWise.RA import _warning
from MotionWise.RA import RA_Args
from MotionWise.RA import Ra_Enum
from MotionWise.RA import Ra_Config_Log_Level
from MotionWise.RA import Ra_Config_Log_Group
from MotionWise.RA import Ra_Config_Log_Sink
from MotionWise.RA import Ra_TraceLog_Message
from MotionWise.RA import Ra_TraceLog_LogNotCodedData
from MotionWise.RA import Ra_TraceLog_LogCodedData
from MotionWise.RA import Ra_TraceLog_TraceData

def main ():
    description = """\
    This script can be used to configure the MotionWise logging and tracing
    functionality. Both system wide and SWC specific logging configurations
    can be performed with this script. For more information please take a
    look in the 'optional arguments' description below. The following
    scenarios outline the basic usage of this script:

        To display this help message:
            MotionWise_Log.py -h

        Print out the current version of this script:
            MotionWise_Log.py -v

        Reset the system wide logging configuration to the default values
        (error and warning levels only):
            MotionWise_Log.py -z -r

        Disable (mute) logging system wide ('-m' equals '-l mute'):
            MotionWise_Log.py -z -m

        Set the logging sink to Ethernet:
            MotionWise_Log.py -z -k eth

        Set the logging sink to UART:
            MotionWise_Log.py -z -k uart

        Set the system wide logging level configuration to output
        warning, error and info logs:
            MotionWise_Log.py -z -l warning error info

        Set the logging configuration for all groups of all SWCs to
        error and warning:
           MotionWise_Log.py -s all -l error warning

        Enable all log levels for group 1 and 4 for SWCs 3 5 and 7:
            MotionWise_Log.py -s 3 5 7 -g 1 4 -l all

        Use -o FILE to keep the script running after sending the configuration.
        Logging messages are written into files. Use 'stdout' as
        filename to print logging messages and discharge everything else.
        Changing the logging sink to Ethernet and printing log messages can
        be done via:
            MotionWise_Log.py -z -k eth -o stdout

    """

    parser = argparse.ArgumentParser \
            ( formatter_class = argparse.RawDescriptionHelpFormatter
            , description = textwrap.dedent (description)
            )

    parser.add_argument \
            ( "-v", "--version"
            , action = "store_true"
            , help = "show program's version number and exit"
            )

    parser.add_argument \
            ( "-r", "--reset", action = "store_true"
            , help =
              "Reset the system wide logging configuration to default values. "
              "By default the logging sink is 'uart', all groups are enabled "
              "and the logging levels for all SW-Cs are 'error' and 'warning'."
            )

    parser.add_argument \
            ( "-m", "--mute", action = "store_true"
            , help="Globally disable logging all logging outputs."
            )

    parser.add_argument \
            ( "-k", "--sink"
            , choices = [str(s) for s in Ra_Enum.enums (Ra_Config_Log_Sink)]
            , help = "Specifies the system wide logging sink configuration."
            )

    parser.add_argument \
            ( "-c", "--coded"
            , choices = [ "on", "off" ]
            , help = "Enables/Disables the system wide logging coded/non-coded messages."
            )

    parser.add_argument \
            ( "-s", "--swcs"
            , metavar = "SWCID", nargs = "+"
            , help = "Select the SW-Cs that should be configured. "
              "The 'SWCID' can either be a valid SWC name or its numeric "
              "identifer (ID). "
              "Using 'all' selects all SW-Cs."
            )

    parser.add_argument \
            ( "-z", "--MotionWise"
            , action = "store_true"
            , help = "Select the MotionWise platform"
            )

    parser.add_argument \
            ( "-g", "--groups"
            , metavar = "GROUP", nargs = "+"
            , type = int
            , help =
              "Specifies one or multiple logging groups that should be configured. "
              "Valid logging group values are {%s}. Per default all groups (1-8) are "
              "selected."
              % (",".join (str(i) for i in (range (1,9))), )
            )

    possible_levels = [str(l) for l in Ra_Enum.enums (Ra_Config_Log_Level)] + [ "all" ]
    parser.add_argument \
            ( "-l", "--levels"
            , metavar = "LEVEL", nargs = "+"
            , help =
              "Specifies the logging levels that should be activated for the selected "
              "SW-Cs and groups. If no SW-Cs are selected, the global log level for all "
              "SW-Cs and groups is changed. "
              "Valid logging level values are: for -z -l { mute, error, warning, info, all }, "
              "for -s ID -l { mute, error, warning, info, all }, "
              "Use level 'mute' to disable logging for the platform ('-z'), selected SW-C ('-s') and groups."
            )

    parser.add_argument \
            ( "-o", "--output"
            , metavar = "FILE"
            , help = "Use FILE_log.csv and FILE_trc.csv as outputs for storing "
              "logging and tracing messages. The filename 'stdout' can be used to "
              "print log messages directly on stdout while tracing information "
              "are discarded. By default this argument is disabled and if you want "
              "to receive and store the logging and tracing messages this argument "
              "has to be provided."
            )

    parser.add_argument \
            ( "-f", "--format"
            , action = "store_true"
            , help = "Activate the MotionWise logging style format, otherwise a default CSV format is used."
            )

    RA_Args (parser)            # add RA library cmd arguments
    args = parser.parse_args () # parse the command line
    ra = RA (parser, args)      # check and load RA library

    if args.version :
        print( "MotionWise_Log.py v%s" % (__version__, ) )
        sys.exit(0)

    # --- check command line arguments ---
    #import pdb; pdb.set_trace()
    # command line combination checks
    if  args.MotionWise is False  \
    and args.swcs is None   \
    and args.coded is not None :
        parser.error ( "option -c has to be used with -z" )

    if  args.MotionWise is False  \
    and args.swcs is None   \
    and args.output is None :
        parser.error ("please use one of the following options: -z or -s or -o.")

    if args.swcs :
        if args.levels is None and not args.mute :
            parser.error ("Option -s requires either option -l or option -m.")

    if args.format and args.output is None :
        parser.error ("Option -f is allowed only together with option -o.")


    if args.groups and args.swcs is None :
        parser.error ("Option -g can only be used together with option -s")

    # check groups for validity and convert into "bitmask"
    all_groups = Ra_Enum.enums( Ra_Config_Log_Group )
    if args.groups:
        if any (x not in range (1,9) for x in args.groups):
            parser.error ("log group argument out of range [1;8] found!")
        groups = [1 << (x-1) for x in sorted(args.groups)]
    else:
        groups = all_groups

    # check levels for validity
    if args.levels:
        if any (l not in possible_levels for l in args.levels):
            parser.error( "invalid log levels argument!" )

        if "all" in args.levels :
            if len( args.levels ) > 1 :
                parser.error( "log level 'all' cannot be combined with other levels" )
            levels = \
            [ "error"
            , "warning"
            , "info"
            ]

        elif "mute" in args.levels :
            if len( args.levels ) > 1 :
                parser.error( "log level 'mute' cannot be combined with other levels" )
            levels = \
            [ "mute"
            ]

        else:
            levels = args.levels

    else:
        levels = None

    # check swcs for validity and convert names into IDs
    if args.swcs:
        swcs = []
        for s in args.swcs :
            if s.startswith( "Cp" ) :
                _s = "Ct%s" % s[ 2: ]
                _warning( "usage of Cp* SWC names is deprecated, mapping '%s' to '%s'", s, _s )
                s = _s

            if s == "all" :
                swcs = [ 255 ]
                break

            elif s in ra.get_swc_names() :
                swcid = ra.get_swc_id_of_swc_name( s )

            else :
                try :
                    swcid = int( s )
                except ValueError :
                    parser.error( "invalid SWC ID -s argument '%s': there is no SWC with this name or ID in the MotionWise definition" % s )
                if swcid not in ra.get_swc_ids() :
                    parser.error( "invalid SWC ID -s argument '%s': there is no SWC with this ID in the MotionWise definition" % ( swcid ) )

            ra._verbose( "SWC ID: %s --> %s", s, ra.get_swc_name_of_swc_id( swcid ) )

            swcs.append (swcid)
        swcs = sorted (set (swcs))

        if 255 in swcs and len( args.swcs ) > 1 :
            parser.error( "invalid SWC ID -s argument '%s': the 'all' SWC ID can only be used alone" % \
                          args.swcs )

    else:
        swcs = None

    # command line combination checks
    if  args.MotionWise \
    and swcs is not None :
        parser.error ( "option -s and -z can not be used together, use either -s or -z" )

    # perform the requested action from the command line options
    # system wide cfg
    if args.MotionWise :
        if args.groups :
            parser.error( "option -g can not be used together with -z" )

        if args.coded :
            print( "Setting MotionWise coded logging to '%s'" % args.coded )
            ra.config_log_coded( { "on" : True, "off" : False }[ args.coded ] )

        if args.reset :
            if args.sink or levels or args.mute :
                parser.error( "option -r can only be used alone with -z" )
            print( "Reseting MotionWise logging configuration" )
            ra.config_log_reset()

        if args.sink :
            if args.reset or levels or args.mute :
                parser.error( "option -k can only be used alone with -z" )
            print( "Setting MotionWise logging sink to %s" % args.sink )
            ra.config_log_sink( args.sink )

        if args.mute :
            if args.reset or levels or args.sink :
                parser.error( "option -m can only be used alone with -z" )
            print( "Disabling MotionWise logging outputs" )
            ra.config_log_level( "mute" )

        if levels :
            if args.reset or args.mute or args.sink :
                parser.error( "option -l can only be used alone with -z" )

            lstr = ""
            for l in levels :
                lstr = "%s'%s', " % ( lstr, l )
            if len( lstr ) > 0 :
                lstr = lstr[ 0:-2 ]

            print( "Setting MotionWise logging levels to %s" % lstr )
            ra.config_log_level( levels )

    # perform the requested action from the command line options
    # component based cfg
    if swcs is not None :
        if args.sink :
            parser.error( "option -k can not be used together with -s, only with -z" )

        if args.coded :
            parser.error( "option -c can not be used together with -s, only with -z" )

        if args.reset :
            if args.groups or args.mute or levels :
                parser.error( "option -r can only be used alone with -s" )
            # reset SWCs logging configuration
            print( "Reseting SWCs logging configuration of '%s'" % swcs )
            for swc in swcs :
                ra.config_log( swc, all_groups, ["info", "warning", "error"] )
                time.sleep( 0.01 )

        if args.mute :
            if args.groups or args.reset or levels :
                parser.error( "option -m can only be used alone with -s" )
            # set SWCs to mute
            print( "Disabling SWCs logging outputs of '%s'" % swcs )
            for swc in swcs :
                ra.config_log( swc, groups, "mute" )
                time.sleep( 0.01 )

        if levels :
            if args.reset or args.mute :
                parser.error( "option -l can only be used alone with -s and optional -g" )
            lstr = ""
            for l in levels :
                lstr = "%s'%s', " % ( lstr, l )
            if len( lstr ) > 0 :
                lstr = lstr[ 0:-2 ]

            # set SWCs logging level(s)
            print( "Setting SWCs specific log level to %s" % lstr )
            for swc in swcs:
                ra.config_log( swc, groups, levels )
                time.sleep( 0.01 )


    # --- handle incoming logging and tracing data ---

    if args.output is not None:
        if args.output == "stdout":
            print ("Printing log messages to stdout.")
            logfile   = sys.stdout
        else:
            logf = "%s.csv" % (args.output, )

            print ( "Recording log and data into %s" % logf )
            logfile   = open (logf, "w")
        
        #ra.tracelog_callback_remove()
        ra.tracelog_callback_add (functools.partial (log_and_trace_cb, args.format, logfile))
        print ("Press Ctrl-C to stop.")

        # # PPA: lines below enables logging offline tests
        # ra.replay_config( "issue/issue.pcap", "offline" )
        # ra.replay_start( 0 )

        try :
            #test_frames (ra)
            while( True ) :
                time.sleep (1) # sleep instead of "pass" to prevent high CPU load
        except KeyboardInterrupt as e:
            pass
        finally :
            ra.receiving_stop()
            time.sleep( 0.1 )

            try :
                ra.tracelog_callback_remove ()
                if args.output != "stdout":
                    logfile.close()
                    
            except Exception as e :
                ra._verbose( "exception: %s", e )

def log_and_trace_cb ( format_flag, logfile, data):
    msg = ctypes.cast( data, ctypes.POINTER (Ra_TraceLog_Message))[0]

    if msg.entry_type == 0x01 \
    or msg.entry_type == 0x02 :
        cls = { 0x01 : Ra_TraceLog_LogNotCodedData, 0x02 : Ra_TraceLog_LogCodedData }[ msg.entry_type ]

        log = ctypes.cast( msg.data, ctypes.POINTER (cls))[0]

        if not format_flag :
            # CSV format
            fmt = "%u,%u,%u,%u,%u,%u,%s\n"

        else :
            # MotionWise log format style
            fmt = "%u %u %u-%u:%u:%u|%s\n"

        stxt = log.reconstructed_string
        if ord(stxt[0]) == 0xff :
            if len(stxt) <= 3 :
                stxt = ""
            else :
                stxt = stxt[ 3: ]
            #import pdb; pdb.set_trace()

        if cls == 0x01 :
            slen =  log.string_length
        else :
            slen = len( str(log.reconstructed_string) )

        line = fmt  % \
        ( msg.entry_type
        , msg.zgt_stamp
        , msg.component_id
        , log.log_option
        , msg.msg_count
        , slen
        , stxt
        )

        logfile.write (line)

    if (msg.entry_type == 0x03) :
        # trace data
        pass
# end def


# --- test code ---
def test_frames (ra):

    def create_log_entry (message):
        return struct.pack \
                ( b"<BBBQBBBBB%dBBB" % (len(message))
                , 1, 1          # frame count, frame limit,
                , 1             # type log
                , 0x1122334455667788 # ZGT
                , 42            # CID
                , 12            # Log option
                , 14            # message counter
                , len(message)
                , 0
                , *[ord(c) for c in message.encode("latin-1")] + [0xFF]
                )

    ra._forward_frame (5, 3, create_log_entry ("hello world!"))


if __name__ == "__main__" :
    main()

# |----+--------+----+-------+------------------------------------+-----------------+------+------+-------+------|
# | -z |        | -k | SINK  | set MotionWise log/trace sink            | uart            | 0xff | 0xf0 |  0x01 | n.a. |
# |    |        |    |       |                                    | eth             | 0xff | 0xf0 |  0x02 | n.a. |
# |    |        |    |       |                                    |                 |      |      |       |      |
# |    |        | -l | LEVEL | set level(s) of MotionWise log/trace     | mute            | 0xff | 0xf1 |  0x00 | n.a. |
# |    |        |    |       |                                    | error           | 0xff | 0xf1 |  0x01 | n.a. |
# |    |        |    |       |                                    | warning         | 0xff | 0xf1 |  0x02 | n.a. |
# |    |        |    |       |                                    | info            | 0xff | 0xf1 |  0x04 | n.a. |
# |    |        |    |       |                                    |                 |      |      |       |      |
# |    |        | -g |       | NOT POSSIBLE                       |                 |      |      |       |      |
# |    |        | -r |       | reset MotionWise log/trace               |                 | 0xff | 0xf2 |  0x00 | n.a. |
# |    |        | -m |       | <==> '-l mute'                     |                 | 0xff | 0xf1 |  0x00 | n.a. |
# |----+--------+----+-------+------------------------------------+-----------------+------+------+-------+------|
# | -s | ID/all | -k | SINK  | NOT POSSIBLE                       |                 |      |      |       |      |
# |    |        |    |       |                                    |                 |      |      |       |      |
# |    |        | -l | LEVEL | set level(s) of SWC log/trace      | mute            | 0xfd |   ID | GROUP | 0x00 |
# |    |        |    |       |                                    | error           | 0xfd |   ID | GROUP | 0x01 |
# |    |        |    |       | ID = [ 0; 253 ]                    | warning         | 0xfd |   ID | GROUP | 0x02 |
# |    |        |    |       |                                    | info            | 0xfd |   ID | GROUP | 0x04 |
# |    |        |    |       | 'all' = 255                        |                 |      |      |       |      |
# |    |        |    |       |                                    |                 |      |      |       |      |
# |    |        | -g | GROUP | set group(s) of the SWC log/trace  | [0x01; 0x80]+   |      |      |       |      |
# |----+--------+----+-------+------------------------------------+-----------------+------+------+-------+------|
