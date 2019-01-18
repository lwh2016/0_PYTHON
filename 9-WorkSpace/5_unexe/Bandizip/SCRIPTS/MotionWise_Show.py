# -*- coding: iso-8859-15 -*-
# Copyright (C) 2014 TTTech Computertechnik AG. All rights reserved
# Schoenbrunnerstrasse 7, A--1040 Wien, Austria. office@tttech.com
#
#++
# Name
#    MotionWise_Show.py
#
# Purpose
#    This script can be used to quickly monitor certail values of/ or
#    complete Rte Messages received from MotionWise
#
# Author
#    Sebastian Aigner <Sebastian.aigner@tttech-automotive.com>
#
# Revision Dates
#    09-Feb-2016 (HLI) taken from zFAS
#
#--

from __future__ import absolute_import, division, print_function, unicode_literals

__version__ = "1.0.0"
__doc__     = """Script for monitoring single port elements, routed from MotionWise"""

import sys
if sys.version_info.major == 3:
    basestring = str
    long = int

import os
import sys
import time
import ctypes
import argparse
import textwrap
import random
import string
from   pprint     import PrettyPrinter
import argparse
import functools
import thread

pjoin = os.path.join

pyToolsDir = pjoin \
   ( os.path.dirname( os.path.abspath( __file__ ) )
   , ".."
   )

if not os.path.exists( pjoin( pyToolsDir, "lib", "site-packages" ) ) :
    sys.path.append ( pyToolsDir )

from MotionWise.RA import RA
from MotionWise.RA import RA_Args


from MotionWise.RA import Ra_Enum
from MotionWise.RA import Ra_Config_Log_Level
from MotionWise.RA import Ra_Config_Log_Sink
from MotionWise.RA import Ra_Config_Routing_Mode

def structured_struct(current_field):
    """!
    @internal
    @brief convert a ctypes structure to a pythonic dict/list composition
    
    @param  :  <br>

    @return pythonic dict/list composition from the ctypes struct passed
    """

    if hasattr(current_field,'value'):
      return current_field.value

    elif hasattr(current_field,'_fields_'):
        return \
            { field_identifier : structured_struct ( getattr(current_field,field_identifier) )
            
              # for each element
              for field_identifier in map(lambda f:f[0],current_field._fields_)
              
              # we're not interrested in Padding Gaps
              if not field_identifier.startswith('PaddingGap')
            } 

    elif hasattr(current_field,'_length_') : #array type
        return [ structured_struct(field) for field in current_field ]
            
    else:
        import pdb;pdb.set_trace()
        print("="*30,"ERR")
    
    return

#end def structured_struct

def callback_dex_complex ( data, **kw_args) :
    """!
    @internal
    
    @brief callbackfunction that simply pretty-prints the received message
           starting at the hierarchical point passed via De_path
           
    @param  :  <br>
    
    TDB
    
    """
    
    # move to requested subelement within the received structure
    if kw_args['De_path'] :
        d_tar = eval('data.contents.%s'%kw_args['De_path'])
    else :
        d_tar = data.contents
    
    # pretty printing
    kw_args['pretty_print'] ( structured_struct( d_tar) )
    
    # early abort when by request
    if kw_args.has_key('f_stop_receive') :
        kw_args['f_stop_receive']()
        kw_args['lock'].release()

# end def callback_dex

def main(parser) :
    
    args = parser.parse_args( )

    if args.version :
        print( "MotionWise_Log.py v%s" % (__version__, ) )
        sys.exit(0)
    
    try :
    
        # extract SWC_Pp<>_De<> from argument
        SWC_Pp_De            = args.PpDe.split('.')[0]
    except : 
    
        # notify user aout the invalid argument
        print( 'invalid argument "%s"'%(args.PpDe or ""))
        print( 'you must specify a valid RTE-Message that you want to receive' )
        sys.exit(0)
        
    
    # explicit ra-initialization - we start the rx-thread later by hand
    ra   = RA( parser, args,init=False )

    # determine required routing and callback identifiers 
    ra_cb_element_id     = ra.get_element_id( "RA_%s"%SWC_Pp_De )
    if ( ra_cb_element_id is None ) :
        print ( 'element id for "%s" not found' % SWC_Pp_De )
        return
    
    port_routing_id      = ra.get_port_id_of_port_name( SWC_Pp_De.split('_De')[0] )
    if ( port_routing_id is None ) :
        print ( 'port routing id for "%s" not found' % SWC_Pp_De )
        return
    
    #little helper to allow immediate shutdown on single-sot mode
    global_sh_lock = thread.allocate_lock()
    global_sh_lock.acquire()
        
    # compose callback function argument set
    ftp_callback_arguments = \
        { 'pretty_print'   : PrettyPrinter(indent=4).pprint
        , 'De_path'        : '.'.join(args.PpDe.split('.')[1:])
        , 'lock'           : global_sh_lock
       }

    # create reference to wrapped callback function
    ref_cba_ccp = functools.partial \
        ( callback_dex_complex
        , **ftp_callback_arguments
        )

    # tell the callback function to unregister itsef once executed
    if args.single_shot :
        ref_cba_ccp.keywords['f_stop_receive'] = ra.receiving_stop
    
    # now initialize
    ra.init()

    # dont flood the net - turn off transmission of trace message
    # ra.config_trace(0,False)
    
    # register callback function
    ra.callback_add( ra_cb_element_id, ref_cba_ccp)
    
    # apply routing configuration if not forbidden by cmd-line
    if not args.no_auto_route :
        ra.config_routing_port( port_routing_id, 'record' )
        ra.config_routing_sync( )
    
    # start receive thread
    ra.receiving_start()

    # little looping so polite
    try :
        print( "press ctrl-c to stop" )
        while( global_sh_lock.locked() ) :
            time.sleep( 0.5 )

    except KeyboardInterrupt as e:
        
        # stop receive thread
        ra.receiving_stop()

    # apply routing configuration if not forbidden by cmd-line
    if not args.no_auto_route :
        ra.config_routing_port( port_routing_id, 'default' )
        ra.config_routing_sync( )

    # the clean way
    ra.shutdown()
        
# end def 

if __name__ == "__main__":
    description = """\
    This script can be used to monitor RTE-Messages send by SW-Cs running
    on the MotionWise. All flags can be combined in any fashion. The following
    scenarios outline the usage of this script:

        To display this help message:
            MotionWise_Show.py -h

        Print out the current version of this script:
            MotionWise_Show.py -v

        continoulsy receive RTE-messages from the specified SW_Cs Port/Element:
            MotionWise_Show.py <SWC_Name>_<PortName>_<DataElementName>

        receive one RTE-message from the specified SW_Cs Port/Element:
            MotionWise_Show.py -s <SWC_Name>_<Pp>_<De>
        
        continously receive RTE-messages from the specified SW_Cs Port/Element,
        without changing the MotionWise Routing Configuration:
            MotionWise_Show.py --no-auto-route <SWC_Name>_<PortName>_<DataElementName>
            
            This can become very hand when executed on a second PC, or combined
            with other Remote Acces utilizing Tools, such as ADTF.

        If you are interrested in a specific element of an RTE-Message, rather 
        than the whole content, you have the possibility to specify these in 
        exactly the same way as you would reference a structure element in the C
        programming language. This also applies to arrays:
        
            MotionWise_Show.py <SWC_Name>_<Pp>_<De>.Sub.Element[index].SubSubElement
    """
    
    parser = argparse.ArgumentParser\
        ( formatter_class = argparse.RawDescriptionHelpFormatter
        , description = textwrap.dedent (description)
        )

    parser.add_argument \
            ( "-v", "--version"
            , action = "store_true"
            , help = "show program's version number and exit"
            )
    
    parser.add_argument \
        ( "PpDe"
        , nargs='?'
        , default = None
        , help='specify which RTE message should be monitored. e.g.:\n'
               '<SWC>_Pp<>_De<>[.subelements][arrayinices]'
        )
    
    parser.add_argument \
        ( "--no-auto-route"
        , action='store_true'
        , help='skip automatic routing configuration'
        )
    
    parser.add_argument \
        ( "-s", "--single-shot"
        , action='store_true'
        , help='quit after pricessing the a single message'
        )
        
    # add ra-specific general arguments to the parser
    RA_Args( parser )
    
    # invoke the app
    main(parser)
    
# end if
