# -*- coding: iso-8859-15 -*-
# Copyright (C) 2013 Martin Glueck All rights reserved
# Langstrasse 4, A--2244 Spannberg, Austria. martin@mangari.org
#
#++
# Name
#    RA.py
#
# Purpose
#    Remote Access Library python wrapper
#
# Revision Dates
#    09-Feb-2016 (HLI) taken from zFAS
#    09-Feb-2016 (HLI) adapted MotionWise structure
#    05-May-2017 (MAT) added SRH support
#    23-Jun-2017 (MotionWise-3874) [JDU] streamlined SRH support
#    27-Jul-2017 (MotionWise-4356) [JDU] detect missing contract headers at startup
#
#--

from   __future__ import absolute_import, division, print_function, unicode_literals

__version__ = "5.0.2"
__doc__     = """Script for MotionWise RA (Remote Access) shared library python wrapper"""

## @file  RA.py
## @brief Remote Access (RA) library Python API
##
## Remote Access Library python wrapper.
##

import sys
if sys.version_info.major == 3:
    basestring = str
    long = int

import argparse, textwrap
from functools import wraps

import ctypes
import struct
import socket
import threading
import atexit
import collections
import os
import re
import copy
import array
import logging
import inspect
import time
try :
    import queue
except :
    import Queue as queue

pjoin = os.path.join


# PPA: move this to independent module
# depends on 'sys' module
# returns map of attributes with content, otherwise None
def _load_module_attr( module_filename, attributes = [] ) :
    """!
    @brief Loading module attributes

    This function loads module attributes.

    @param module_filename : { `str` }<br>
    the name of module file

    @param attributes : { `list` }<br>
    attributes with content

    @return { `list`, `None` }
    """

    result = {}

    module_object = _load_module( module_filename )

    module_split     = os.path.split( module_filename )
    module_directory = module_split[0]
    module_file      = module_split[1]
    module_name      = module_file[:-3]

    if module_object is not None :

        for attr in attributes :
            result[ attr ] = getattr( module_object, attr )

        sys.path.remove( module_directory )

        del module_object
        sys.modules.pop( module_name )

        return result

    else :
        return None

# end def _load_module_attr


# PPA: move this to independent module
def _load_module( module_filename ) :
    """!
    @brief Loading module

    This function loads module.

    @param module_filename : { `str` }<br>
    the name of module file

    @return { `obj`, `None` }
    """

    if  os.path.isfile( module_filename ) \
    and os.access( module_filename, os.R_OK ):

        module_split     = os.path.split( module_filename )
        module_directory = module_split[0]
        module_file      = module_split[1]
        module_name      = module_file[:-3]

        sys.path.append( module_directory )

        module_object    = __import__( module_name )
        # check for errors

        return module_object
    else :
        return None

# end def _load_module



# PPA: move this to RA helper classes
class RA_Error (Exception):
    """!
    @brief RA error code

    This class returns RA error code message.

    @return { `str` }
    """

    def __init__ (self, result, func, arguments):
        self.result    = result
        self.func      = func
        self.arguments = arguments
    # end def __init__

    def __str__ (self):
        return "%s failed with error code %d" % (self.func.__name__, self.result)
    # end def __str__

# end class RA_Error


# PPA: move this to enumerations with checking inside the ctypes class
RA_E_OK = 0
def Std_ReturnType (result, func, arguments):
    """!
    @brief Return type

    This function returns type.

    @param result : { `str` }<br>
    error code

    @param func : { `str` }<br>
    name of the function

    @param arguments : { `str` }<br>
    arguments of the function

    @return { `str` }
    """

    if result != RA_E_OK:
        _warning( "'%s' return value received for function call '%s%s'" % \
                  ( result, func.__name__, arguments )
        )

        #import pdb; pdb.set_trace()
        #raise RA_Error (result, func, arguments)
# end def


def _print( message, *args ) :
    """!
    @brief Printing message

    This function prints message.

    @param message : { `str` }<br>
    the message that will be printed

    @param args : { `list` }<br>
    pointer to arguments of the message

    @return { `str` }
    """

    message = "[RA.py] %s" % ( message, )
    sys.stderr.flush()
    print( message % args, file=sys.stderr )
# end def

def _warning( message, *args ) :
    """!
    @brief Printing warning

    This function prints warning message.

    @param message : { `str` }<br>
    the message that will be printed

    @param args : { `list` }<br>
    pointer to arguments of the message

    @return { `str` }
    """

    message = "warning: %s" % ( message, )
    _print( message, *args )
# end def

def _error( message, *args, **kwargs ) :
    """!
    @brief Printing error

    This function prints error message.

    @param message : { `str` }<br>
    the message that will be printed

    @param args : { `list` }<br>
    pointer to arguments of the message

    @param kwargs : { `bool` }<br>

    @return { `int` }
    """

    # previous_function = inspect.currentframe().f_back.f_code
    # fn = os.path.basename( previous_function.co_filename )
    message = "error: %s" % ( message, )
    _print( message, *args )

    # caller = inspect.currentframe()
    # if "scope" in kwargs and kwargs["scope"] > 0 :
    #     for i in range( kwargs["scope"] ) :
    #         caller = caller.f_back
    # caller = caller.f_code
    # fn = os.path.basename( caller.co_filename )
    # fl = caller.co_firstlineno

    # _print( "       see %s at line %s" % ( fn, fl, ) )

    if "abort" in kwargs :
        if kwargs[ "abort" ] == False :
            return

    sys.exit( -1 )
# end def

def _internal_error( message, *args, **kwargs ) :
    """!
    @brief Printing internal error

    This function prints internal error message.

    @param message : { `str` }<br>
    the message that will be printed

    @param args : { `list` }<br>
    pointer to arguments of the message

    @param kwargs : { `bool` }<br>

    @return { `int` }
    """

    previous_function = inspect.currentframe().f_back.f_code
    fn = os.path.basename( previous_function.co_filename )
    fl = previous_function.co_firstlineno
    message = "internal error: %s:%i: %s" % ( fn, fl, message, )
    _print( message, *args )

    if "abort" in kwargs :
        if kwargs[ "abort" ] == False :
            return
    sys.exit( -1 )
# end def

def printf( *args ) :
    """!
    @brief Printing message 

    This function prints message.

    @param args : { `list` }<br>
    pointer to arguments of the message

    @return { `str` }
    """

    fstr = "===---"

    for arg in args :
        fstr = fstr + "\n%s,"

    fstr = fstr + "\n---==="

    print( fstr % ( args ) )
# end def

def ctypes_array_to_string( array
                          , seperator = ""
                          , convert = (lambda e : "%s" % e)
                          , stop = None
                          ) :
    """!
    @brief Converting array to string 

    This function converts array to string.

    @param array : { `list` }<br>
    the array that needs to be converted

    @param seperator : { `str` }<br>
    separator empty space between the elements  

    @param convert : { `str` }<br>
    element conversion

    @param stop : { `int` }<br>
    stopping the conversion

    @return { `str` }
    """  
  
    assert( type(seperator) is unicode or \
            type(seperator) is str        )

    result = ""
    first  = True
    for e in array :
        if  stop is not None \
        and stop == e :
            break
        if first :
            result = "%s%s" % (result, convert( e ),)
            first  = False
        else :
            result = "%s%s%s" % (result, seperator, convert( e ),)
    return result
# end def

def ctypes_string_to_array( string
                          , seperator = None
                          , ctor = (lambda e : ctypes.c_int8(e))
                          , cast = (lambda e : ord(e))
                          ) :
    """!
    @brief Converting string to array

    This function converts string to array.

    @param string : { `str` }<br>
    the string that needs to be converted

    @param seperator : { `None` }<br>
    separator between the elements is None

    @param ctor : { `list` }<br>
    element conversion

    @param cast : { `list` }<br>
    casting the elements

    @return { `list` }
    """  
 
    assert( type(string) is unicode or \
            type(string) is str        )

    if seperator is None :
        return tuple( [ ctor( cast(i) ) for i in list( string ) ] )

    else :
        assert( type(seperator) is unicode or \
                type(seperator) is str        )

        return tuple( [ ctor( cast( i ) ) for i in string.split( seperator )] )
# end def



#-------------------------------------------------------------------------------
# RA enumerations
#-------------------------------------------------------------------------------

class Ra_Enum( ctypes.c_uint8 ) :
    """!
    @brief RA enumeration helper class

    This class represents a enumeration prototype. It checks if the used values
    are unique and allows three representations of the same enum value -
    identifier, integer or string.
    """

    __coder = {}
    __enums = {}

    def __init__( self, value, name = None, size = False ) :

        if value in Ra_Enum.__coder :
            print( "error: value '%s' already exists in Ra_Enum" % (value,) )
            sys.exit(-1)

        class_name = self.__class__.__name__

        # if class_name in Ra_Enum.__coder \   # PPA: add class naming check
        # and Ra_Enum.__coder[ class_name ] is not None :
        #     _error( "Ra_Enum '%s' already defined", class_name )
        # Ra_Enum.__coder[ class_name ] = []

        Ra_Enum.__coder[  "%s%s" % (class_name, value) ] = ctypes.c_uint8(value)
        Ra_Enum.__coder[ "_%s%s" % (class_name, value) ] = self
        Ra_Enum.__coder[ self  ] = ctypes.c_uint8(value)

        if name is not None :
            if name in Ra_Enum.__coder :
                print( "error: name '%s' already exists in Ra_Enum" % (name,) )
                sys.exit(-1)
            Ra_Enum.__coder[ name ] = self
            Ra_Enum.__coder[ "%s%s" % (class_name, value) ] = name

        setattr( self, "value", value )

        if not (class_name in Ra_Enum.__enums ) :
            Ra_Enum.__enums[ class_name ] = []

        if not size :
            Ra_Enum.__enums[ class_name ].append( self )

        #print( "%s" % ( getattr(self, "value") ,) )
    # end def __init__


    def __str__( self ):
        key = "%s%s" % (self.__class__.__name__, self.value)

        if key in Ra_Enum.__coder :
            val = Ra_Enum.__coder[ key ]
            if type(val) is ctypes.c_uint8 :
                return "%s" % val.value
            else :
                return val
        else :
            return None
    # end def __str__


    def __hash__( self ):
        return getattr( self, "value" )
    # end def __hash__


    def get_name( self, value ) :
        """!
        @brief RA enumeration string representation

        Returns for a given Ra_Enum value the string representation if
        there exists one otherwise a `None` is returned.

        @param value : { `Ra_Enum`, `int` }<br>
        the value to be looked up

        @return { `str`, `None` }
        """

        key = "%s%s" % (self.__class__.__name__, value)

        if key in Ra_Enum.__coder :
            return Ra_Enum.__coder[ key ]
        else :
            return None
    # end def get_identifier


    @staticmethod
    def enums( obj_class ) :
        """!
        @brief List of enumerations of a Ra_Enum class

        Returns a list or Ra_Enum values (or objects) for a given Ra_Enum class.

        @param obj_class : `Ra_Enum`<br>
        the class of which the values shall be fetched

        @return `list`
        """

        if not issubclass( obj_class, Ra_Enum ) :
            _error( "used class is no Ra_Enum sub-class" )

        return Ra_Enum.__enums[ obj_class.__name__ ]
    # def end enums


    @staticmethod
    def to_string( obj_class ) :
        """!
        @brief Conversion to string of a Ra_Enum class

        Returns converted string (message) for a given Ra_Enum class.

        @param obj_class : `Ra_Enum`<br>
        the class of which the values shall be fetched

        @return `str`
        """

        if not issubclass( obj_class, Ra_Enum ) :
            _error( "used class is no Ra_Enum sub-class" )

        msg = "{"
        for e in Ra_Enum.enums( obj_class ) :
            msg = "%s%s," % (msg,e)
        return msg[:-1] + "}"
    # def end enums


    @staticmethod
    def cast( obj_class, obj ) :
        """!
        @brief Ra_Enum type checking and type cast

        This function performs a type checking and type cast from a given
        value to a specified Ra_Enum class.

        @param obj_class : `Ra_Enum` <br>
        the type cast class

        @param obj : { `Ra_Enum`, `int`, `str` } <br>
        the value (or object) which shall be checked for the given type class
        and converted to the Ra_Enum subclass object

        @return { `Ra_Enum`, `None` }
        """

        if not issubclass(obj_class,Ra_Enum) :
            _error( "used class is no Ra_Enum sub-class" )

        if isinstance( obj, basestring ) :
            try:
                return Ra_Enum.__coder[ obj ]
            except KeyError:
                return None

        elif isinstance( obj, Ra_Enum ) :
            return obj

        elif isinstance( obj, int ) :
            try:
                return Ra_Enum.__coder[  "_%s%s" % (obj_class.__name__, obj) ]
            except KeyError:
                return None

        elif isinstance( obj, ctypes.c_uint8 ) :
            try:
                return Ra_Enum.__coder[  "_%s%s" % (obj_class.__name__, obj.value) ]
            except KeyError:
                return None

        else :
            return None
    # end def cast

    @staticmethod
    def bitmask( obj_class, values ) :
        """!
        @brief Ra_Enum bitmask calculation

        This function performs a bitmask calculation of all the given
        values (as list). Each value is first casted to the given
        class and then a bitmask is calculated via the integer value
        of the enum.

        @param obj_class : `Ra_Enum` <br>
        the type cast class

        @param values : list <br>
        a list of Ra_Enum objects and/or values

        @return `int`
        """

        if not isinstance( values, list ) :
            values = [ values ]
        _bitmask = 0x00
        for e in values :
            _e = Ra_Enum.cast( obj_class, e )
            if _e is None :
                _error( "value '%s' is an invalid %s list value", e, obj_class.__name__, scope = 1 )
            _bitmask = _bitmask | _e.value
        return _bitmask
    # end def
# end class Ra_Enum


class Ra_ReturnType( Ra_Enum ) :
    """!
    @brief RA library return type

    This class includes the enumeration-based RA shared library return type
    A valid Std_ReturnType value can either be an identifier, an integer
    or a string literal which are outlined in the following table:

          Identifier | Integer | String
          ===========|=========|========  
          `RA_E_OK`  | `0`     | `"OK"`
          `RA_E_NOK` | `1`     | `"NOK"`

    Identifier   | Integer | String
    -------------| ------- | ------
    `RA_E_OK`    | `0`     | `"OK"`
    `RA_E_NOK`   | `1`     | `"NOK"`
    """
_RA_E_OK  = Ra_ReturnType( 0, "OK"  ) # PPA: do not use this for NOW
_RA_E_NOK = Ra_ReturnType( 1, "NOK" )


# RA host IDs
class Ra_Host( Ra_Enum ) :
    """!
    @brief RA library MotionWise hosts

    This class includes the enumeration-based RA shared library MotionWise hosts.
    A valid Ra_Host value can either be an identifier, an integer or a
    string literal which are outlined in the following table:

          Identifier    | Integer | String
          ==============|=========|============  
          `RA_HOST_APH` | `0`     | `"APH"`
          `RA_HOST_SSH` | `1`     | `"SSH"`
          `RA_HOST_DBG` | `3`     | `"DBG"`
          `RA_HOST_SIZE`| `4`     | `size=True`

    Identifier    | Integer | String
    ------------- | ------- | -----------
    `RA_HOST_APH` | `0`     | `"APH"`
    `RA_HOST_SSH` | `1`     | `"SSH"`
    `RA_HOST_DBG` | `3`     | `"DBG"`
    `RA_HOST_SIZE`| `4`     | `size=True`
    """
RA_HOST_APH  = Ra_Host( 0, "APH" )
RA_HOST_SSH  = Ra_Host( 1, "SSH" )
RA_HOST_SRH  = Ra_Host( 2, "SRH" )
RA_HOST_DBG  = Ra_Host( 3, "DBG" )
RA_HOST_SIZE = Ra_Host( 4, size=True )

# RA frame kinds
class Ra_Kind( Ra_Enum ) :
    """!
    @brief RA library middleware frame kinds

    This class includes the enumeration-based RA shared library middleware
    frame kinds. A valid Ra_Kind value can either be an identifier or an
    integer literal which are outlined in the following table:

          Identifier    | Integer 
          ==============|========= 
          `RA_DEX_KING` | `0`
          `RA_SYN_KIND` | `1`
          `RA_TST_KIND` | `2`
          `RA_DEV_KIND` | `3`
          `RA_MAX_KIND` | `4`

    Identifier    | Integer
    ------------- | -------
    `RA_DEX_KING` | `0`
    `RA_SYN_KIND` | `1`
    `RA_TST_KIND` | `2`
    `RA_DEV_KIND` | `3`
    `RA_MAX_KIND` | `4`
    """
RA_DEX_KIND = Ra_Kind( 0 )
RA_SYN_KIND = Ra_Kind( 1 )
RA_TST_KIND = Ra_Kind( 2 )
RA_DEV_KIND = Ra_Kind( 3 )
RA_MAX_KIND = Ra_Kind( 4 )

# RA lib operation mode
class Ra_Mode( Ra_Enum ) :
    """!
    @brief RA library replay mode behaviour

    This class includes the enumeration-based RA shared library behaviour mode.
    A valid Ra_Mode value can either be an identifier, an integer or a
    string literal which are outlined in the following table:

          Identifier                      | Integer | String
          ================================|=========|============  
          `RA_ONLINE`                     | `0`     | `"online"`
          `RA_OFFLINE_SIMULATED_REALTIME` | `1`     | `"simulate"`
          `RA_OFFLINE`                    | `2`     | `"offline"`

    Identifier                      | Integer | String
    ------------------------------- | ------- | ------
    `RA_ONLINE`                     | `0`     | `"online"`
    `RA_OFFLINE_SIMULATED_REALTIME` | `1`     | `"simulate"`
    `RA_OFFLINE`                    | `2`     | `"offline"`
    """
RA_ONLINE                       = Ra_Mode( 0, "online"   )
RA_OFFLINE_SIMULATE_REALTIME    = Ra_Mode( 1, "simulate" )
RA_OFFLINE                      = Ra_Mode( 2, "offline"  )

# RA lib routing config mode
class Ra_Config_Routing_Mode( Ra_Enum ) :
    """!
    @brief RA library routing configuration mode

    This class includes the enumeration-based RA shared library routing
    configuration mode. A valid Ra_Config_Routing_Mode value can either
    be an identifier, an integer or a string literal which are outlined
    in the following table:

          Identifier                      | Integer | String
          ================================|=========|===========  
          `RA_CFG_ROUTE_DEFAULT`          | `0`     | `"default"`
          `RA_CFG_ROUTE_RECORD`           | `1`     | `"record"`
          `RA_CFG_ROUTE_REPLAY`           | `2`     | `"replay"`

    Identifier                      | Integer | String
    ------------------------------- | ------- | ------
    `RA_CFG_ROUTE_DEFAULT`          | `0`     | `"default"`
    `RA_CFG_ROUTE_RECORD`           | `1`     | `"record"`
    `RA_CFG_ROUTE_REPLAY`           | `2`     | `"replay"`
    """
RA_CFG_ROUTE_DEFAULT = Ra_Config_Routing_Mode( 0, "default" )
RA_CFG_ROUTE_RECORD  = Ra_Config_Routing_Mode( 1, "record" )
RA_CFG_ROUTE_REPLAY  = Ra_Config_Routing_Mode( 2, "replay" )

# Log sinks
class Ra_Config_Log_Sink( Ra_Enum ) :
    """!
    @brief RA library logging/tracing sink

    This class includes the enumeration-based RA shared library logging
    and tracing sink. A valid Ra_Config_Log_Sink value can either
    be an identifier, an integer or a string literal which are outlined
    in the following table:

          Identifier              | Integer | String
          ========================|=========|========  
          `LOG_SINK_UART`         | `0`     | `"uart"`
          `LOG_SINK_ETH`          | `1`     | `"eth"`

    Identifier              | Integer | String
    ----------------------- | ------- | ------
    `LOG_SINK_UART`         | `0`     | `"uart"`
    `LOG_SINK_ETH`          | `1`     | `"eth"`
    """
LOG_SINK_UART = Ra_Config_Log_Sink( 0x01, "uart" )
LOG_SINK_ETH  = Ra_Config_Log_Sink( 0x02, "eth"  )

# Log levels
class Ra_Config_Log_Level( Ra_Enum ) :
    """!
    @brief RA library logging/tracing function levels

    This class includes the enumeration-based RA shared library logging
    and tracing function levels. A valid Ra_Config_Log_Level value can
    either be an identifier, an integer or a string literal which are
    outlined in the following table:

          Identifier          | Integer | String
          ====================|=========|===========  
          `LOG_MUTE`          | `0x00`  | `"mute"`
          `LOG_ERROR`         | `0x01`  | `"error"`
          `LOG_WARNING`       | `0x02`  | `"warning"`
          `LOG_INFO`          | `0x04`  | `"info"`

    Identifier          | Integer | String
    ------------------- | ------- | ------
    `LOG_MUTE`          | `0x00`  | `"mute"`
    `LOG_ERROR`         | `0x01`  | `"error"`
    `LOG_WARNING`       | `0x02`  | `"warning"`
    `LOG_INFO`          | `0x04`  | `"info"`
    """
LOG_MUTE      = Ra_Config_Log_Level( 0x00, "mute" )
LOG_ERROR     = Ra_Config_Log_Level( 0x01, "error" )
LOG_WARNING   = Ra_Config_Log_Level( 0x02, "warning" )
LOG_INFO      = Ra_Config_Log_Level( 0x04, "info" )


# Log groups
class Ra_Config_Log_Group( Ra_Enum ) :
    """!
    @brief RA library logging/tracing group

    This class includes the enumeration-based RA shared library logging
    and tracing group. A valid Ra_Config_Log_Group value can either be
    an identifier, an integer or a string literal which are outlined in
    the following table:

          Identifier          | Integer | String
          ====================|=========|===========  
          `LOG_GROUP_1`       | `1`     | `"group1"`
          `LOG_GROUP_2`       | `2`     | `"group2"`
          `LOG_GROUP_3`       | `4`     | `"group3"`
          `LOG_GROUP_4`       | `8`     | `"group4"`
          `LOG_GROUP_5`       | `16`    | `"group5"`
          `LOG_GROUP_6`       | `32`    | `"group6"`
          `LOG_GROUP_7`       | `64`    | `"group7"`
          `LOG_GROUP_8`       | `128`   | `"group8"`

    Identifier          | Integer | String
    ------------------- | ------- | ------
    `LOG_GROUP_1`       | `1`     | `"group1"`
    `LOG_GROUP_2`       | `2`     | `"group2"`
    `LOG_GROUP_3`       | `4`     | `"group3"`
    `LOG_GROUP_4`       | `8`     | `"group4"`
    `LOG_GROUP_5`       | `16`    | `"group5"`
    `LOG_GROUP_6`       | `32`    | `"group6"`
    `LOG_GROUP_7`       | `64`    | `"group7"`
    `LOG_GROUP_8`       | `128`   | `"group8"`
    """
LOG_GROUP_1 = Ra_Config_Log_Group( 0x01, "group1" )
LOG_GROUP_2 = Ra_Config_Log_Group( 0x02, "group2"  )
LOG_GROUP_3 = Ra_Config_Log_Group( 0x04, "group3"  )
LOG_GROUP_4 = Ra_Config_Log_Group( 0x08, "group4"  )
LOG_GROUP_5 = Ra_Config_Log_Group( 0x10, "group5"  )
LOG_GROUP_6 = Ra_Config_Log_Group( 0x20, "group6"  )
LOG_GROUP_7 = Ra_Config_Log_Group( 0x40, "group7"  )
LOG_GROUP_8 = Ra_Config_Log_Group( 0x80, "group8"  )


#-------------------------------------------------------------------------------
# RA structs
#-------------------------------------------------------------------------------

class Ra_TraceLog_Message (ctypes.Structure):
    """!
    @brief RA library logging/tracing message

    This class includes the definition of a received logging and tracing
    messages. It is composed of an entry_type, host_id, component_id, zgt_stamp,
    msg_count and the actual message data field. The data field can either be a
    Ra_TraceLog_LogNotCodedData, a Ra_TraceLog_LogCodedData or
    a Ra_TraceLog_TraceData object.
    """
    _fields_ = \
            [ ("entry_type"  , ctypes.c_uint8)
            , ("host_id"     , ctypes.c_uint8)
            , ("component_id", ctypes.c_uint8)
            , ("zgt_stamp"   , ctypes.c_uint64)
            , ("msg_count"   , ctypes.c_uint8)
            , ("data"        , ctypes.POINTER (ctypes.c_uint8))
            ]

class Ra_TraceLog_LogNotCodedData (ctypes.Structure):
    """!
    @brief RA library logging log not coded message data

    This class includes the definition of a received logging 
    log not coded message data field of the Ra_TraceLog_LogNotCodedData object.
    It is composed of the log_option, string_length, string, parameters_length,
    parameters, reconstructed_string.
    """
    _fields_ = \
            [ ("log_option"           , ctypes.c_uint8)
            , ("string_length"        , ctypes.c_uint8)
            , ("string"               , ctypes.c_char_p)
            , ("parameters_length"    , ctypes.c_uint8)
            , ("parameters"           , ctypes.c_char_p)
            , ("reconstructed_string" , ctypes.c_char_p)
            ]

class Ra_TraceLog_LogCodedData (ctypes.Structure):
    """!
    @brief RA library logging log coded message data

    This class includes the definition of a received logging 
    log coded message data field of the Ra_TraceLog_LogCodedData object.
    It is composed of the log_option, string_code, parameters_length, parameters,
    reconstructed_string.
    """
    _fields_ = \
            [ ("log_option"           , ctypes.c_uint8)
            , ("string_code"          , ctypes.c_uint8)
            , ("parameters_length"    , ctypes.c_uint8)
            , ("parameters"           , ctypes.c_char_p)
            , ("reconstructed_string" , ctypes.c_char_p)
            ]

class Ra_TraceLog_TraceData (ctypes.Structure):
    """!
    @brief RA library logging/tracing trace message data

    This class includes the definition of a trace message data.
    It is composed of a msg_count and the actual trace message data field.
    """
    _fields_ = \
            [ ("core_id"     , ctypes.c_uint8)
            , ("event_type"  , ctypes.c_uint8)
            , ("event_data"  , ctypes.c_uint64)
            ]


# Type used for reporting PIE profiling data
class Ra_ProfilingData (object):
    """!
    @brief RA library reporting profiling data.

    This class is used for reporting PIE profiling data.
    """
    class _Ra_ProfilingData (ctypes.Structure) :
        _fields_ = \
            [ ("exe_time", ctypes.c_uint32)
            , ("stack",    ctypes.c_int32)
            ]
    # end class _Ra_ProfilingData

    ctype  = _Ra_ProfilingData
    header = "ID  | Exe. time [us] |  Stack [bytes] |"

    def __init__ (self, ctype_instance, runnable_id):
        for field in (f[0] for f in Ra_ProfilingData.ctype._fields_):
            setattr (self, field, getattr (ctype_instance, field))
        self.runnable_id = runnable_id
    # end def __init__

    def asrow (self):
        return  "{:>3d} | {:>14d} | {:>14s} |".format \
                ( self.runnable_id
                , self.exe_time
                , str (self.stack) if self.stack != -1 else "meas. disabled"
                )
# end class Ra_ProfilingData



class Ra_NetworkConfig( ctypes.Structure ) :
    """!
    @brief RA network configuration representation

    This class represents a full MotionWise platform network configuration as is
    defined in the Ra.h. Additionally this class stores the MotionWise default
    network configuration setting which would equal the following constructor
    call of this class:

    ~~~{.py}
    Ra_NetworkConfig( { "APH": { "name": "eth0"
                               , "mac" : "00:00:00:00:00:00"
                               , "ip"  : "192.168.1.50"
                               , "port": "50050"
                               }
                      , "SSH": { "name": "eth0"
                               , "mac" : "00:00:00:00:00:00"
                               , "ip"  : "192.168.1.60"
                               , "port": "50060"
                               }
                      , "DBG": { "name": "eth0"
                               , "mac" : "00:00:00:00:00:00"
                               , "ip"  : "192.168.1.40"
                               , "port": "50040"
                               } } )
    ~~~
    """
    # Single host port network configuration
    class _Ra_NetworkHostConfig( ctypes.Structure ) :
        """!
        @brief Single host port network configuration

        This class represents a single host port network configuration as is
        defined in the Ra.h
        """

        _fields_ = \
                   [ ("name", ctypes.c_int8   * 8 )
                   , ("mac",  ctypes.c_uint8  * 6 )
                   , ("ip",   ctypes.c_uint8  * 4 )
                   , ("port", ctypes.c_uint16     )
                   ]

        def __init__( self, setting ) :

            ft = { "name": [ None, (lambda e : ctypes.c_int8(e)),   (lambda e : ord(e)) ]
                 , "mac" : [ ":",  (lambda e : ctypes.c_uint8(e)),  (lambda e : int(e,16)) ]
                 , "ip"  : [ ".",  (lambda e : ctypes.c_uint8(e)),  (lambda e : int(e)) ]
                 , "port": [ None, (lambda e : ctypes.c_uint16(e)), (lambda e : int(e)) ]
                 }

            if "name" in setting :
                # trunk inferface name at 8 characters
                setting[ "name" ] = "%-8s" % (setting[ "name" ],)

            for option in setting :
                if option != "port" :
                    opt = ctypes_string_to_array( setting[ option ], *ft[ option ] )
                else :
                    opt = ft[ option ][1]( ft[ option ][2]( setting[ option ] ) )
                setattr( self, option, opt )

        def __str__( self ) :
            n = ctypes_array_to_string( self.name, convert = (lambda e : "%s" % chr(e) ), stop = ord("\0") )
            m = ctypes_array_to_string( self.mac,  ":", (lambda e : "%02x" % e) )
            i = ctypes_array_to_string( self.ip,   ".", (lambda e : "%3d"  % e) )
            p = "%s" % self.port

            return "%s: %s %s %s" % (n, m, i, p)
    # end class


    _fields_ = \
            [ ("hosts", _Ra_NetworkHostConfig * RA_HOST_SIZE.value )
            ]

    _default_cfg =  { RA_HOST_APH: { "name": "eth0"
                                   , "mac" : "40:7A:46:41:53:50"
                                   , "ip"  : "192.168.1.50"
                                   , "port": "50050"
                                   }
                    , RA_HOST_SSH: { "name": "eth0"
                                   , "mac" : "40:7A:46:41:53:60"
                                   , "ip"  : "192.168.1.70"
                                   , "port": "50060"
                                   }
                    , RA_HOST_SRH: { "name": "eth0"
                                   , "mac" : "40:7A:46:41:53:70"
                                   , "ip"  : "192.168.1.70"
                                   , "port": "50070"
                                   }
                    , RA_HOST_DBG: { "name": "eth0"
                                   , "mac" : "00:00:00:00:00:00"
                                   , "ip"  : "192.168.1.40"
                                   , "port": "50040"
                                   } }

    _current_cfg = None

    def __init__( self, configuration_map = None ) :
        """!
        @brief Create new RA network configuration

        This constructor creates based on the configuration_map parameter a
        new (= default configuration) or a partial network setting. By partial
        is meant that each construction of a Ra_NetworkConfig object with
        partial configuration_map alters a static class variable to "sum" up
        all the incremental changes.

        ~~~{.py}
        # loads default configuration
        Ra_NetworkConfig()

        # only change APH IP address
        Ra_NetworkConfig( { "APH" : { "ip" : "1.2.3.4" } } )

        # only change SSH UDP port number
        Ra_NetworkConfig( { RA_HOST_SSH : { "port" : "1234" } } )

        # change SRH MAC address and Debug/Test interface name
        Ra_NetworkConfig( { 2 : { "mac"  : "12:34:56:78:9a" }
                                  , 3 : { "name" : "example" } } )

        # loads default configuration, again
        Ra_NetworkConfig()
        ~~~

        Due the usage of the Ra_Host type it is possible to address the
        different MotionWise hosts in three different literal forms. The
        constructor assures this property.

        @param configuration_map : `{ Ra_Host : { str : str } }` <br>
        Specifies the network setting based on a dictionary inside a dictionary.
        The key of the first dictionary has to be a Ra_Host literal. The second
        key can either be `"name"`, `"ip"`, `"mac"` or `"port"`. Each value
        has a specific string value format which is defined in the following:

              Key      | Value 
              =========|======================================================== 
              `"name"` | plain string bounded by 8 characters (e.g. `"ethDev"` )
              `"ip"`   | IP address string (e.g. `"192.168.0.1"`)
              `"mac"`  | Ethernet MAC address string (e.g. `"00:00:00:00:00:00"`)
              `"port"` | UDP/IP port number string (e.g. `"8080"`)

        Key | Value
        --- | -----
        `"name"` | plain string bounded by 8 characters (e.g. `"ethDev"` )
        `"ip"`   | IP address string (e.g. `"192.168.0.1"`)
        `"mac"`  | Ethernet MAC address string (e.g. `"00:00:00:00:00:00"`)
        `"port"` | UDP/IP port number string (e.g. `"8080"`)

        If the parameter is `None` than the default configuration is loaded.
        """

        if Ra_NetworkConfig._current_cfg is None :
            Ra_NetworkConfig._current_cfg = dict()
            for h in Ra_NetworkConfig._default_cfg :
                Ra_NetworkConfig._current_cfg[ h ] = copy.deepcopy( Ra_NetworkConfig._default_cfg[ h ] )

        # get current config
        _cfg = Ra_NetworkConfig._current_cfg
        _key = None

        # override all or partial setting
        if configuration_map is None :
            _cfg = Ra_NetworkConfig._default_cfg
            Ra_NetworkConfig._current_cfg = None
        else :
            for host in configuration_map :
                host_name = Ra_Enum.cast( Ra_Host, host )
                printf( host_name, _cfg[ host_name ] )
                for prop in configuration_map[ host ] :
                    if prop in _cfg[ host_name ] :
                        _cfg[ host_name ][ prop ] = configuration_map[ host ][ prop ]

        # create the ctypes
        for host in _cfg :
            host_id = Ra_Enum.cast( Ra_Host, host )
            if host_id is None:
                    assert( 0 and "host id not valid" )
            self.hosts[ host_id.value ] = Ra_NetworkConfig._Ra_NetworkHostConfig( _cfg[ host ] )
    # end def __init__

    def __str__( self ) :
        msg = ""
        for e in Ra_Enum.enums( Ra_Host ) :
            msg = msg + "%s: %s\n" % ( e, self.hosts[ e.value ] )
        return msg
    # end def __str__
# end class Ra_NetworkConfig


# RA logging and replay configuration
class Ra_LogAndReplayConfig( ctypes.Structure ) :
    """!
    @brief RA logging and replay configuration.

    This class represents RA logging and replay configuration. This class stores message of 
    pcap configuration: pcap log file, pcap replay file and pcap mode.
    """

    _fields_ = \
            [ ("pcaplog_fname",    ctypes.c_int8 * 1024 )
            , ("pcapreplay_fname", ctypes.c_int8 * 1024 )
            , ("mode",             Ra_Mode              )
            ]

    def __init__( self, log_file, replay_file, mode ) :
        assert( type(mode) is Ra_Mode )

        lf = ctypes_string_to_array( log_file    )
        rf = ctypes_string_to_array( replay_file )

        printf( lf, rf )

        b = len( lf )
        for i in range( len( self.pcaplog_fname ) ) :
            if i < b :
                self.pcaplog_fname[i] = lf[i]
            else :
                self.pcaplog_fname[i] = 0

        b = len( rf )
        for i in range( len( self.pcapreplay_fname ) ) :
            if i < b :
                self.pcapreplay_fname[i] = rf[i]
            else :
                self.pcapreplay_fname[i] = 0

        self.mode = mode
    # end def __init__

    def __str__( self ) :
        lf = ctypes_array_to_string( self.pcaplog_fname
                                   , convert = (lambda e : "%s" % chr(e) ), stop = ord("\0") )
        rf = ctypes_array_to_string( self.pcapreplay_fname
                                   , convert = (lambda e : "%s" % chr(e) ), stop = ord("\0") )
        md = self.mode

        msg = "pcap log file:    %s\n" \
              "pcap replay file: %s\n" \
              "pcap mode:        %s" % (lf, rf, md )
        return msg
    # end def __str__
# end class Ra_LogAndReplayConfig



#-------------------------------------------------------------------------------
# Remote Access helper classes and functions
#-------------------------------------------------------------------------------

# Wrapper object around the Ra_Transmit library functions
class Function (object) :
    """!
    @brief Remote Access helper functions

    Wrapper object around the Ra_Transmit library functions.
    """

    UNDEF    = object ()

    def __init__ (self, lib, name, alias, swc, *parameters) :
        if hasattr(lib._lib, name) :
            self.fct           = getattr (lib._lib, name)
        else :
            _error( "RA lib does not contain contract header function '%s'", name, abort = False )
            return

        self.name = name
        self.para_types    = []
        self.para_names    = []
        self.parameters    = parameters
        self.alias         = alias
        self.swc           = swc
        for pt, pn in parameters :
            lib.TYPES [pn]          = pt
            lib.TYPES [pt.__name__] = pt
            self.para_types.append (ctypes.POINTER (pt))
            self.para_names.append (pn)
        self.fct.argtypes  = self.para_types
        self.signature     = "%s (%s)" % ( name, ", ".join (self.para_names))
    # end def __init__

    def __str__ (self) :
        return self.signature
    # end def __str__


    def __call__( self, params = None, internal = False ) :
        parameters = []
        index = 0

        if internal :
            assert( isinstance( params, list ) )

            for p in params :
                parameters.append( ctypes.cast( ctypes.addressof( p ), self.fct.argtypes[ index ] ) )
                index = index + 1

            return self.fct( *parameters )

        if isinstance( params, dict ) :
            params = [ params ]

        for (pt, pn) in self.parameters :
            arg = self._factory( pt, params[ index ] )
            arg = ctypes.cast( ctypes.addressof(arg), self.fct.argtypes[ index ] )
            parameters.append( arg )
            index = index + 1

        return self.fct( *parameters )
    # end def __call__


    def _factory( self, t, v ) :
        default = 0
        result  = t()
        if issubclass( t, ctypes.Structure ) :
            # we got a structure
            for fn, ft in t._fields_ :
                #print( "    {%s} %s" % (fn, ft) )
                x = None
                if isinstance( v, dict ) and fn in v :
                    x = self._factory( ft, v[ fn ] )
                else :
                    x = self._factory( ft, default )
                setattr( result, fn, x )

        elif issubclass( t, ctypes.Array ) :
            # we got a array
            for i in xrange( t._length_ ) :
                #print( "    [%s] %s" % ( i, t._type_ ) )
                x = None
                if isinstance( v, list ) and i < len( v ) :
                    x = self._factory( t._type_, v[ i ] )
                else :
                    x = self._factory( t._type_, default )
                result[ i ] = x

        elif issubclass( t, ( ctypes.c_byte, ctypes.c_ubyte
                            , ctypes.c_short, ctypes.c_ushort
                            , ctypes.c_int, ctypes.c_uint
                            , ctypes.c_long, ctypes.c_ulong
                            , ctypes.c_longlong, ctypes.c_ulonglong
                            , ctypes.c_float
                            ) ) :
            #print( "%s : %s" % ( v, t ) )

            # we got a primitive data type
            if isinstance( v, basestring ) and v.endswith (".0") :
                v = v [:-2]
            x = v
            if x is None :
                x = default

            result = t( x )

        else :
            # PPA: this should not be triggered!
            assert( 0 )

        return result
    # end def
# end class Function



#-------------------------------------------------------------------------------
# Remote Access shared library C wrapper function loading, checking and calling
#-------------------------------------------------------------------------------

RA_API_Data = { "__init__" : False }

def RA_API( fname, etype = None, rtype = None, atype = None) :
    """!
    @brief RA API

    Remote Access shared library C wrapper function loading,
    checking and calling. 

    @param fname : `str` <br>
    shared library symbol C function name

    @param etype : `None` <br>
    error checking type (e.g. Std_ReturnType)

    @param rtype : `None` <br>
    C return type (e.g. ctypes.c_int8)

    @param atype : `None` <br>
    C function argument type signature:

          Python                            | C
          ==================================|==============  
          None                              | ()
          []                                | ()
          [ ctypes.c_uint8 ]                | (uint8_t)
          [ ctypes.c_char, ctypes.c_short ] | (char,short)

    @return `int`
    """ 

    def _init( func ):

        RA_API_Data[ "RAlib" + func.__name__ ] = \
            ( fname
            , etype
            , rtype
            , atype
            )

        #_print( "%s ==> %s", fname, func.__name__ )

        @wraps( func )
        def _call_cdll( self, *args, **kwargs ):
            #print( "[%s]: %s, %s" % ( func.__name__, args, kwargs) )

            if RA_API_Data[ "__init__" ] == False :

                del RA_API_Data[ "__init__" ]

                dump = []
                specification_keys = []

                for k in RA_API_Data.keys() :
                    specification_keys.append( k )

                for specification_key in specification_keys:
                    function_key = specification_key[ 5: ]
                    #specification_key = "RAlib" + func.__name__
                    function_specification = RA_API_Data[ specification_key ]

                    fname = function_specification[0]
                    etype = function_specification[1]
                    rtype = function_specification[2]
                    atype = function_specification[3]

                    # PPA: change this to _internal_error() call
                    assert( fname is not None and \
                            fname != "" and \
                            "invalid RA_API function name" )

                    #self._verbose( "[%s]: '%s': checking RA API call ", func.__name__, fname, level=9998 )

                    try :
                        function_obj = getattr( self._lib, fname )
                    except AttributeError:
                        dump.append( "--> %s" % fname )
                        #_internal_error( "RA shared library does not contain function '%s'", fname )

                    if etype:
                        function_obj.errcheck = etype
                    if rtype:
                        function_obj.restype  = rtype
                    if atype:
                        function_obj.argtypes = atype

                    #del RA_API_Data[ specification_key ]

                    function_key

                    RA_API_Data[ function_key ] = function_obj

                    self._verbose( "successfully registered API call '%s'", fname, level=9998 )

                if len( dump ) > 0 :
                    _error( "RA API VERSION ERROR", abort = False )
                    _error( "RA shared library does not contain APIs:", abort = False )
                    for msg in dump :
                        _error( msg, abort = False )
                    _error( "aborting" )

                RA_API_Data[ "__init__" ] = True
            else :
                self._verbose( "[%s]: already checked", func.__name__, level=9998 )

            function_key = func.__name__

            self._verbose( "%s %s %s", func.__name__, args, kwargs, level=9996 )

            arguments = func( self, *args, **kwargs )

            if arguments is None :
                return

            assert( function_key in RA_API_Data and \
                    "invalid initialization of shared library function pointer")

            function_obj = RA_API_Data[ function_key ]

            # assert( function_obj.argtypes is not None and \    ##PPA: improve this check!!!
            #         len(function_obj.argtypes) > 0    and \
            #         len(arguments) == len(function_obj.argtypes) and \
            #         "invalid argument length passed in the return statement")

            self._verbose( "[%s]: args = %s | %s"
                           , func.__name__
                           , RA_API_Data[ function_key ]
                           , arguments, level=9997 )

            # PPA: improve this with better and generic error handling!!!
            try:
                result = function_obj( *arguments )
            except RA_Error as e:
                print( str(e) )
                sys.exit(1)

            self._verbose( "[%s]: result = %s", func.__name__, result, level=9996 )

            return result
        return _call_cdll
    return _init


#-------------------------------------------------------------------------------
# Remote Access wrapper class
#-------------------------------------------------------------------------------

class RA (object) :
    """!
    @brief Remote Access (RA) library Python wrapper class

    This class represents a Python wrapper around the RA C library API calls.
    Furthermore, it provides additional information about the MotionWise system.
    """

    def _verbose( self, message, *args, **kwargs ) :
        _vb  = int(self.verbose)

        if "level" in kwargs :
            _lvl = int( kwargs["level"] )
        else :
            _lvl = int( 0 )

        if _vb >= 0 :
            level_msg = ""

            if _lvl > 0 :
                level_msg = "(%s)" % (_lvl,)

            if _vb >= _lvl :
                message = "verbose%s: %s" % ( level_msg, message, )

                _print( message, *args )
    # end def

    def __init__( self, parser = None, args = None, init = True ) :
        """!
        @brief RA library python wrapper constructor

        The RA library python wrapper class be constructed in two ways. Either
        to integrate it into a available `argparse` command line option
        facility or to use the plain default settings.

        The following code snippet shows an example integration with an other
        argparse facility:
        
        ~~~{.py}
            parser = argparse.ArgumentParser \
            ( formatter_class = # ...
            , description     = # ...
            )
        
            RA_Args( parser )            # add RA library cmd arguments to parser object
            args = parser.parse_args ()  # parse the command line arguments from sys.args
            ra = RA( parser, args )      # check and load the RA library
        ~~~
        
        In the code is a special function ( RA_Args() ) used to add the RA specific 
        command line options of the RA itself to the parser before it evaluates and
        checks the command line. After that, the RA library gets constructed with the
        parser and the arguments.
        
        The following example demonstrates the initialization/construction of the RA
        library Python wrapper with no command line argument handling and to prevent
        the RA initialization the init flag was set to `False`.
        
        ~~~{.py}
            ra = RA( init = False )      # check and load the RA library, no args and no init
        ~~~
        
        To be operational additional calls to the initialization and receiving API
        of the Python wrapper have to be made.


        @param parser : argparse.ArgumentParser <br>
        provide an argparse parser object
        
        @param args : argparse.Namespace <br>
        provide an argparse namespace of the command line arguments which have been
        checked (parsed) already
        
        @param init : bool <br>
        (`True` : RA library gets initialized with the selected transport backend - 
        either the default one or a command line specific one - and the RA library
        starts with the receiving of frames.
        `False` : the RA library only gets loaded, further operations have to be done
        manually.)


        @see RA_Args()
        @see init()
        @see receiving_start()
        """

        # class members
        self.ra_model = None
        self.verbose = -1

        self._FUNCTIONS     = []
        self.TYPES          = dict ()
        self.CALLBACK_TYPES = dict()
        self.bdl_hooks = []

        _print( "RA.py v%s", __version__ )

        # check if parser was defined, if not use a dummy
        if parser is None or args is None :
            parser = argparse.ArgumentParser(add_help=False, usage=argparse.SUPPRESS )
            RA_Args( parser )
            args = parser.parse_args("")

        # manage verbose option
        ra_verbose_lvl  = args.ra_verbose
        if ra_verbose_lvl is None :
            self.verbose = 0
        else :
            try :
                ra_verbose_lvl = int(ra_verbose_lvl)
            except ValueError :
                parser.error( "option --ra-verbose needs an integer argument" )

            if ra_verbose_lvl < 0 :
                self.verbose = -1
            else :
                self.verbose = ra_verbose_lvl

        # hidden option --ra-devel [ RA_LIB_DIR ]
        #
        # provide default path settings for --ra-contract and --ra-model
        # and --ra-lib to work directly from the MotionWise repository
        # OPTIONAL: pointing to RA shared library build directory
        ra_model_file   = None
        ra_lib_dir      = None
        ra_contract_dir = None
        lib_name_dbg    = ""

        if "site-package" in __file__ :
            ra_model_file   = pjoin (__file__, "..", "RA_Model.py")
            ra_lib_dir      = pjoin (__file__, "..", "bin")
            ra_contract_dir = pjoin (__file__, "..", "Contract_Header")
        else :
            base_dir        = os.environ ["BF_MotionWise_SW_ROOT"]
            ra_model_file = pjoin \
                ( base_dir, "0700_GenData", "01_Platform", "DEV", "System", "RA"
                , "python", "RA_Model.py"
                )
            ra_lib_dir    = pjoin \
                ( base_dir, "0200_Platform", "0270_DevelopmentHost", "06_bin", "RA")
            ra_contract_dir = pjoin \
                ( base_dir, "0900_SystemVariants", "02_interfaces"
                , "Contract_Header" 
                )

        if self.verbose > 0 :
            ra_lib_dir = pjoin( ra_lib_dir, "debug" )
            lib_name_dbg = "_dbg"


        # load RA model python wrapper
        if ra_model_file:
            self._verbose( "load RA model '%s'", ra_model_file )
            self._verbose( "load attributes * from '" + ra_model_file + "'", level=1 )
            self.ra_model = _load_module( ra_model_file )
            if self.ra_model is None :
                parser.error( "could not load RA model file '" + ra_model_file + "'" )
            else:
                self.ra_model.ID2Type_Map = {}
        else:
            parser.error( "please provide a RA model file via --ra-model argument" )
            #from . import RA_Model   # relative import from RA.py location

        # load RA shared library
        base_name = "RA"
        lib_name_bit = str (ctypes.sizeof (ctypes.c_voidp) * 8)

        if os.name == "posix" and sys.platform.startswith("linux") :
            lib_name_sys = "linux"
            lib_name_ext = "so"
        else :
            lib_name_sys = "win"
            lib_name_ext = "dll"

        lib_name = "libRA_%s%s%s.%s" % ( lib_name_sys, lib_name_bit, lib_name_dbg, lib_name_ext )

        ra_lib_file = pjoin( ra_lib_dir, lib_name )
        self._verbose( "load shared library '" + ra_lib_file + "'" )
        try :
            #if lib_name_sys == "win" :
            self._lib = ctypes.CDLL( ra_lib_file )
            #else :
            #    self._lib = ctypes.CDLL( ra_lib_file, mode = ctypes.RTLD_GLOBAL )
        except OSError :
            #import pdb; pdb.set_trace()

            parser.error( "could not load shared library '%s'" % (ra_lib_file,) )

        # register some additional callback function data types from Ra.h
        self.callbacks = collections.defaultdict (lambda : collections.defaultdict (list))
        self._verbose( "initialize RA callback functions" )

        # PPA: this function gets transformed into function decorators
        #      see RA_CB (CB not available and ready yet)
        self.CALLBACK_TYPES ["Ra_Download_Cb"] = \
                ctypes.CFUNCTYPE (None, ctypes.c_uint8)

        self.CALLBACK_TYPES ["Ra_Upload_Cb"] = \
                ctypes.CFUNCTYPE (None, ctypes.c_uint8, ctypes.c_void_p, ctypes.c_uint32)

        self.CALLBACK_TYPES ["Ra_TraceLog_Cb"] = \
                ctypes.CFUNCTYPE (None, ctypes.c_void_p)

        # RA Mw TL backend and receive thread control variables
        self._backend                = None
        self._receive_thread_running = None
        self._replaying              = None

        # initialize RA library with specified middleware transport layer backend
        if init:
            self._verbose( "default initialization of the RA shared library" )
            self.init()

        # contract header variables
        self._swc_to_host   = dict()
        self._swc_to_frames = dict()
        self._frame_to_swcs = dict()
        self._element_to_id = dict()

        # load SW-C specific contract header information regarding the RA transmit functions
        # Note that this is optional an not needed for use cases such as configuring the logging
        # and tracing functionality
        self._verbose( "load contract header '%s'", ra_contract_dir )
        if ra_contract_dir :
            if not os.path.exists( ra_contract_dir ) :
                parser.error( "could not open SW-C contract header folder '" + ra_contract_dir + "'" )

            self._swc_name_to_swc_id = dict()
            self._swc_id_to_swc_name = dict()

            for key, val in self.ra_model.SWCID_Map.iteritems() :
                # ignore the init SW-C
                if key == "INIT" :
                    continue

                self._swc_name_to_swc_id[ key ] = val
                self._swc_id_to_swc_name[ val ] = key

            _error_cnt          = 0
            no_contract_headers = True

            for swc in self._swc_name_to_swc_id :
                _swc_key = str( swc )

                swc = _swc_key
                _s2h = swc + "_swc_host_name"
                _s2f = swc + "_swc_to_frames"
                _f2s = swc + "_frame_to_swcs"
                _id2t = "ID2Type_Map"
                _e2i = "element_to_id"

                _transmit_func = "_" + swc + "_functions"

                swc_file = pjoin( ra_contract_dir, swc, "Ra_Type.py" )
                swc_attr =  [ _transmit_func
                            , _s2h
                            , _s2f
                            , _f2s
                            , _id2t
                            , _e2i
                            ]

                # load the SW-C functions from the Contract Header Ra_Type.py
                result = _load_module_attr( swc_file, swc_attr )

                # if it is None, the file does not exists and we continue
                if result is None :
                    continue
                else :
                    no_contract_headers = False

                for _swc_attr in swc_attr :
                    self._verbose( "loaded from '%s' the attribute '%s'"
                                , os.path.basename( swc_file )
                                , _swc_attr
                                , level=999 )

                self.ra_model.ID2Type_Map = dict(self.ra_model.ID2Type_Map.items() + result[_id2t].items())

                for k,v in result[ _e2i ].iteritems() :
                    if k in self._element_to_id :
                        _v = self._element_to_id[ k ]
                        if v != _v :
                            _error( "element ID of '%s' is defined with different values '%s' and '%s' ", k,v,_v )
                        else :
                            continue

                    self._verbose( "%s -> %s", k, v, level=10000 )
                    self._element_to_id[ k ] = v


                # :::... SWC to host mapping ...:::
                if _swc_key not in self._swc_to_host :
                    self._swc_to_host[ _swc_key ] = set()
                self._swc_to_host[ _swc_key ] = result[ _s2h ]

                # :::... SWC to FRAME mapping and vice versa ...:::
                for sid, fids in result[ _s2f ].iteritems() :
                    if sid not in self._swc_to_frames :
                        self._swc_to_frames[ sid ] = ( set(), set() )
                    for recv_or_send in [ 0, 1 ] :
                        for f in fids[ recv_or_send ] :
                            for item in list(result[ _f2s ][f][recv_or_send]) :
                                if list(item)[1] == True:
                                    self._swc_to_frames[ sid ][ recv_or_send ].add( f )

                for fid, sids in result[ _f2s ].iteritems() :
                    if fid not in self._frame_to_swcs :
                        self._frame_to_swcs[ fid ] = ( set(), set() )
                    for recv_or_send in [ 0, 1 ] :
                        for s in sids[ recv_or_send ] :
                            self._frame_to_swcs[ fid ][ recv_or_send ].add( s[0] )

                # :::... TRANSMIT FUNCTIONS LOADING ...:::
                # add the SW-C functions to the self._FUNCTIONS member
                for name, parameters, aliases in result[ _transmit_func ] :

                    fct = Function( self, name, aliases, swc, *parameters )

                    if not hasattr( fct, "signature" ) :
                        _error_cnt = _error_cnt + 1
                        continue

                    found = False
                    for f in self._FUNCTIONS :
                        if str(f) == str(fct) :
                            found = True
                            break

                    if not found :
                        self._FUNCTIONS.append (fct)
                        setattr(self, name, fct)
                        for a in aliases :
                            if a :
                                setattr(self, a, fct)
            if no_contract_headers :
                _error ( "No contract headers found! "
                         "(Did you move the installer before running it?)"
                       )

        self._path_contract_header = ra_contract_dir


        # PPA: unstable, investigate this!!!
        # add RA shutdown exit hooks
        #atexit.register( self._deinit )

        if _error_cnt > 0 :
            _error( "to many errors occurred, aborting!" )

        self._verbose( "python wrapper loaded" )

        # start receive by default if selected
        if init:
            self.receiving_start()

    # end def __init__


    def _deinit( self ) :
        # self.stop_receive_thread

        if self._backend is not None :
            self.shutdown()
            #pass

    # end def


    # **************************************************************************
    # Public API
    # **************************************************************************
    def get_IFSET( self ) :
        """!
        @brief Get the IFSET version

        This function returns IFSET version.

        @return IFSET version as string 'x.y.z'
        """
        return self.ra_model.IFSET
    # end def

    def get_functions( self ) :
        """!
        @brief Get the transmit functions

        This function returns all loaded transmit functions.

        @return `dict`
        """
        return self._FUNCTIONS
    # end def

    def get_element_id( self, de_name ) :
        """!
        @brief Get element id of element names

        This function returns element ID based on element name.

        @param de_name : `str` <br>
        an element name

        @return  { `int`, `None` }
        """

        try :
            return self._element_to_id[ de_name ]
        except :
            return None
    # end def

    def get_port_id_of_port_name( self, port_name ) :
        """!
        @brief Get port id of port names

        This function returns port ID based on port name.

        @param port_name : `str` <br>
        a port name

        @return { `int`, `None` }
        """
        if port_name in self.ra_model.port_to_id :
            return self.ra_model.port_to_id[ port_name ]
        else :
            return None
    # end def

    def get_type_map( self ) :
        """!
        @brief Get the SW-C ID to Data-type map

        This function returns a map of a SWC ID string to c-types data type.

        @return `dict`
        """
        return self.ra_model.ID2Type_Map
    # end def

    def get_swc_ids( self ) :
        """!
        @brief Get the SW-C IDs.

        This function returns SWC IDs.

        @return `list`
        """
        return sorted( list( self._swc_id_to_swc_name.keys() ) )
    # end def

    def get_swc_names( self ) :
        """!
        @brief Get the SWC names
        
        This function returns a list of all SWC names.
        
        @return `list` 
        """
        return sorted( list( self._swc_name_to_swc_id.keys() ) )
        #return sorted( list( self._swc_to_frames.keys() ) )
    # end def

    def get_swc_name_of_swc_id( self, swc_id ) :
        """!
        @brief Get the SWC name of a SWC ID
        
        This function returns if defined the SWC name of the
        corresponding SWC ID, otherwise `None` is returned.
        
        @param swc_id : int, str <br>
        valid SWC id
        
        @return { `str`, `None` }
        """
        if swc_id in self._swc_id_to_swc_name :
            return self._swc_id_to_swc_name[ swc_id ]
        else :
            return None
    # end def

    def get_swc_id_of_swc_name( self, swc_name ) :
        """!
        @brief Fetch SWC ID of a SWC name

        This function returns for a given SWC name the corresponding
        SWC ID. Alternatively the function get_swc_ids() can be used,
        but this function directly checks if the requested SWC name
        is valid.

        @param swc_name : str <br>
        a valid SWC name

        @return { `int`, `None` }
        """
        if swc_name in self._swc_name_to_swc_id :
            return self._swc_name_to_swc_id[ swc_name ]
        else :
            return None
    # end def


    def get_frame_ids( self ) :
        """!
        @brief Get all frame IDs
        
        This function returns all DEX frame IDs.

        @return `list`
        """
        return list( self._frame_to_swcs.keys() )
    # end def

    def get_receiver_swc_names_of_frame_id( self, frame_id ) :
        """!
        @brief Get SWC receiver names of frame ID
        
        This function returns the SWC names which are receiving this frame ID.
        If this frame is received by no SWC, `None` is returned.
        
        @param frame_id : `int` <br>
        the frame ID
        
        @return { `list`, `None` }
        """
        if frame_id in self._frame_to_swcs :
            return list( self._frame_to_swcs[ frame_id ][ 0 ] )
        else :
            return None
    # end def

    def get_sender_swc_names_of_frame_id( self, frame_id ) :
        """!
        @brief Get SWC sender names of frame ID
        
        This function returns the SWC names which are sending this frame ID.
        If this frame is send by no SWC, `None` is returned.
        
        @param frame_id : `int` <br>
        the frame ID
        
        @return { `list`, `None` }
        """
        if frame_id in self._frame_to_swcs :
            return list( self._frame_to_swcs[ frame_id ][ 1 ] )
        else :
            return None
    # end def

    def get_receive_frame_ids_of_swc_name( self, swc_name ) :
        """!
        @brief Get frame IDs received by SWC name
        
        This function returns the frame IDs which are received by this SWC.
        If this SWC receives no frames, `None` is returned.
        
        @param swc_name : `str` <br>
        a valid SWC name
        
        @return { `list`, `None` }
        """
        if swc_name in self._swc_to_frames :
            return list( self._swc_to_frames[ swc_name ][ 0 ] )
        else :
            return None
    # end def

    def get_send_frame_ids_of_swc_name( self, swc_name ) :
        """!
        @brief Get frame IDs send by SWC name
        
        This function returns the frame IDs which are send by this SWC.
        If this SWC sends no frames, `None` is returned.
        
        @param swc_name : `str` <br>
        a valid SWC name
        
        @return { `list`, `None` }
        """
        if swc_name in self._swc_to_frames :
            return list( self._swc_to_frames[ swc_name ][ 1 ] )
        else :
            return None
    # end def

    def get_host_name_of_swc_name( self, swc_name ) :
        """!
        @brief Get the host names of a SWC name
        
        This function returns host name were this SWC is located.
        If the SWC name is invalid, `None` is returned.
        
        @param swc_name : `str` <br>
        a valid SWC name
        
        @return { `str`, `None` }
        """
        try :
            return self.ra_model.swc_to_host[ swc_name ]
        except :
            return None
    # end def

    def get_swc_name_of_runnable_id( self, rID ) :
        """!
        @brief Get SWC names of runnable ID
        
        This function returns for the given SWC name the corresponding runnable ID.
        If this runnable is send by no SWC, `None` is returned.
        
        @param rID : `int` <br>
        the runnable ID
        
        @return { `int`, `None` }
        """
        try :
            return self.ra_model.runnable_to_swc[ rID ]
        except :
            return None
    # end def

    def get_runnable_name_of_runnable_id( self, rID ) :
        """!
        @brief Get runnable names of runnable ID
        
        This function returns for the given runnable name the corresponding runnable ID.
        If this runnable ID is send by no runnable, `None` is returned.
        
        @param rID : `int` <br>
        the runnable ID
        
        @return { `int`, `None` }
        """
        try :
            return self.ra_model.id_to_runnable[ rID ]
        except :
            return None
    # end def

    #**************************************************************************
    # RA General API Wrapper Functions
    #**************************************************************************

    @RA_API \
    ( "Ra_Get_Version"
    , rtype = ctypes.c_char_p
    )
    def get_version( self ) :
        """!
        @brief Retrieve the RA library version string

        This function returns the version string of the RA library.

        @return `str`

        @see C shared library equivalent Ra_Get_Version() in Ra.h
        """

        return []
    # end def


    @RA_API \
    ( "Ra_Init"
    , Std_ReturnType, ctypes.c_uint8
    )
    def init( self ) :
        """!
        @brief RA library initialization

        This method initializes the RA shared library with a specific
        middleware transport backend implementation. By default this method
        gets called in the RA() constructor. To re-initialize the
        library after a shutdown() this method is indispensable, because
        only this method opens the PCAP communication channel.
        By default this method loads the default
        network configuration setting which is stored inside the RA shared
        library. To alter the network configuration see set_network_config().

        @return { `int`, `None` }

        @see C shared library equivalent Ra_Init() in Ra.h
        """

        if self._backend is not None :
            self._verbose( "already initialized" )
            return None

        self._backend = "pcap"

        self._verbose( "initialize RA" )

        return [ ]
    # end def


    @RA_API \
    ( "Ra_Shutdown"
    , Std_ReturnType, ctypes.c_uint8
    )
    def shutdown( self ) :
        """!
        @brief RA library deinitialization

        This method is shutting down the RA shared library and releases all
        resources which are used by the shared library itself. If there is
        an ongoing receiving (invoked via receiving_start()) this method
        implicitly calls the recieving_stop() method to stop this process too.

        @return { `int`, `None` }

        @see C shared library equivalent Ra_Shutdown() in Ra.h
        """

        if self._backend is None :
            self._verbose( "already shutdown RA shared library" )
            return None

        self._verbose( "shutting down RA with '%s'", self._backend )
        self._backend = None

        return []
    # end def
    # PPA: found issue in C RAlib
    #      -> does not stutdown correctly, maybe because of the receive thread issue (see above!)

    @RA_API \
    ( "Ra_Set_NetworkConfig"
    , Std_ReturnType, ctypes.c_uint8
    , [ ctypes.POINTER( Ra_NetworkConfig ) ]
    )
    def set_network_config( self, nwcfg = None ) : # map of host to config, or nwcfg object or nothing
        """!
        @brief RA library network configuration

        This method enables to setup the network configuration for all MotionWise platform hosts.
        By default the init() function loads the directly into
        the RA shared library coded default network configuration which would
        equal the following method call:

        ~~~{.py}
        ra = RA()
        ra.set_network_config()
        ~~~

        Furthermore, this method allows upon the parameter flexible way to create
        partial

        @param nwcfg : `Ra_NetworkConfig` or `dict( dict() )` <br>
        the new (sub-) network configuration, if there is none provided the default
        network configuration is loaded

        @return { `int`, `None` }

        @see C shared library equivalent Ra_Set_NetworkConfig() in Ra.h
        """

        _cfg = None

        if nwcfg is None :
            _cfg = Ra_NetworkConfig() # load default setting
        else :
            if type(nwcfg) is dict :
                # PPA: add here more checks to guarantee type safety { str(host) : list(options) }
                _cfg = Ra_NetworkConfig( nwcfg )

            elif isinstance( nwcfg, Ra_NetworkConfig ) :
                _cfg = nwcfg

            else :
                assert(0)

        assert( _cfg is not None )

        self._verbose( "set_network_config:\n%s", _cfg )

        return [ ctypes.POINTER( Ra_NetworkConfig )( _cfg ) ]

    # end def



    # RA Receive API Wrapper Functions

    @RA_API \
    ( "Ra_Callback_Add"
    , Std_ReturnType, ctypes.c_uint8
    # , [ Ra_Kind, ctypes.c_uint32, Ra_Data_Cb ]
    )
    # PPA: function is not ready yet!
    def callback_add( self, id, function, type = None, kind = 0 ) :
        """!
        @brief Register a callback function for a specific frame kind and ID

        For receiving regular data element sent via MW frames use RA_DEX_KIND as kind
        and use Ra_<SWC>_<Port>_<Element> as ID. Have a look at <B>Ra_Distributor_Ids.h</B>
        for a list of all available IDs.


        @param id : `int` <br>
        either data element ID for data exchange frames, otherwise it is the frame ID

        @param function : `Ra_Data_Cb` <br>
        the function to be called on data reception

        @param type : `int` <br>

        @param kind : `Ra_Kind` <br>
        specifies the frame kind 


        @return `Ra_Kind`, `int`, `Ra_Data_Cb`

        @see C shared library equivalent Ra_Callback_Add() in Ra.h
        """

        if isinstance (id, basestring) :
            #id   = getattr (self.ra_model, id)
            id   = self.get_element_id( id )
        if type is None :
            type = self.ra_model.ID2Type_Map.get (id, type)
        if isinstance (type, basestring) :
            type = self.TYPES.get (type, type)
        if type not in self.CALLBACK_TYPES :
            self.CALLBACK_TYPES [type] = ctypes.CFUNCTYPE \
                (None, ctypes.POINTER (type))

        c_fct  = self.CALLBACK_TYPES [type] (function)

        # we need to keep a reference to the c_fct object to avoid that
        # python garbage collects it which would case a problem once
        # the c-library wants to execute this callback
        self.callbacks[kind][id].append( ( function, c_fct ) )

        self._verbose( "add reader (callback) '%s', '%s', '%s'", kind, id, c_fct )
        return [ kind, id, c_fct ]
    # end def




    def callback_remove( self, id, function, kind = 0 ) :
        """!
        @brief Unregister a callback function

        This function is the inverse operation to the callback_add() function. It
        removes the added (registered) callback function for a specific frame id
        and kind.


        @param id : `int` <br>
        either data element ID for data exchange frames, otherwise it is the frame ID 

        @param function : `Ra_Data_Cb` <br>
        the callback function to be removed 

        @param kind : `Ra_Kind` <br>
        specifies the frame kind, per default it is a DEX frame kind 

        @return { `int`, `None` }
 
        @see _callback_remove()
        @see callback_add()
        @see C shared library equivalent Ra_Callback_Remove() in Ra.h
        """

        for cb, c_fct in self.callbacks [kind] [id] :
            if cb is function :
                self._callback_remove( kind, id, c_fct )
    # end def

    @RA_API \
    ( "Ra_Callback_Remove"
    , None, None
    # , [ Ra_Kind, ctypes.c_uint32, Ra_Data_Cb ]
    )
    # PPA: function is not ready yet!
    def _callback_remove( self, kind, id, c_fct ) :
        """!
        @private
        @brief Callback removing function

        This internal function removes specific reader callback.


        @param kind : `Ra_Kind` <br>
        specifies the frame kind

        @param id : `int` <br>
        either data element ID for data exchange frames, otherwise it is the frame ID

        @param c_fct : `Ra_Data_Cb` <br>
        callback function to be removed


        @return `Ra_Kind`, `int`, `Ra_Data_Cb` 

        @see callback_remove()
        @see callback_add()
        @see C shared library equivalent Ra_Callback_Remove() in Ra.h
        """

        self._verbose( "remove reader (callback) '%s', '%s', '%s'", kind, id, c_fct )
        return [ kind, id, c_fct ]
    # end def


    @RA_API \
    ( "Ra_Receiving_Start"
    , Std_ReturnType, ctypes.c_uint8
    )
    def receiving_start( self ) :
        """!
        @brief Start receiving frames periodically

        This function starts an OS-based thread which periodically receives frames
        from the MotionWise platform and calls the registered receive function callbacks.

        @return { `int`, `None` }

        @see callback_add()
        @see callback_remove()
        @see C shared library equivalent Ra_Receiving_Start() in Ra.h
        """

        if (  (self._receive_thread_running is None)
           or (self._receive_thread_running == False)
           ):
            self._verbose( "starting receive thread" )
            self._receive_thread_running = True
        else:
            self._verbose( "already started RA receive thread" )
            return None
        return []
    # end def


    @RA_API \
    ( "Ra_Receiving_Stop"
    , Std_ReturnType, ctypes.c_uint8
    )
    def receiving_stop( self ) :
        """!
        @brief Stopping receiving frames

        The started receiving frames from the function receiving_start()
        can be stopped with this function.

        @return { `int`, `None` }

        @see C shared library equivalent Ra_Receiving_Stop() in Ra.h
        """

        if self._receive_thread_running is None :
            self._verbose( "RA receive thread was never started" )
            return None

        elif self._receive_thread_running == False :
            self._verbose( "already stopped RA receive thread" )
            return None

        else:  # self._receive_thread_running == True :
            self._verbose( "stopping receive thread" )
            self._receive_thread_running = False

        return []
    # end def


    # # PPA: removed this python wrapper function due some instabilities
    # @RA_API \
    # ( "Ra_Receive"
    # , None, None
    # , [ ctypes.c_uint16 ]
    # )
    # def receive( self, timeout_in_ms ) :
    #     """!
    #     @brief TODO

    #     TBD

    #     @param  :  <br>

    #     @see C shared library equivalent Ra_Receive() in Ra.h
    #     """

    #     if not (type(timeout_in_ms) is int) :
    #         return None

    #     self._verbose( "receiving frames bounded by a %sms time out", timeout_in_ms )

    #     return [ ctypes.c_uint16( timeout_in_ms ) ]
    # # end def


    _log_file = None

    @RA_API \
    ( "Ra_Log_Config"
    , Std_ReturnType, ctypes.c_uint8
    , [ ctypes.c_char_p ]
    )
    def log_config( self, log_file ) :
        """!
        @brief Configures a RA logging file for raw Ethernet frames

        This function sets a log file name where the incoming Ethernet frames are
        stored if frame logging is enabled via log_start(). This function
        is only available if the RA library is initialized with the PCAP backend.

        @param log_file : `str` <br>
        the name of the log file which will be created

        @return { `int`, `None` }

        @see init()
        @see RA_TL_PCAP 
        @see C shared library equivalent Ra_Log_Config() in Ra.h
        """

        assert( type(log_file) is unicode or \
                type(log_file) is str        )

        if not log_file.endswith( ".pcap" ) :
            log_file = log_file + ".pcap"

        self._log_file = ctypes.c_char_p( log_file )

        return [ self._log_file ]
    # end def


    @RA_API \
    ( "Ra_Log_Start"
    , Std_ReturnType, ctypes.c_uint8
    )
    def log_start( self ) :
        """!
        @brief Starting the logging of raw Ethernet frames to a log file

        This function enables that the RA library writes every incoming
        raw Ethernet frame to the configured log file.

        @return { `int`, `None` }

        @see log_config()
        @see C shared library equivalent Ra_Log_Start() in Ra.h
        """

        return [ ]
    # end def


    @RA_API \
    ( "Ra_Log_Stop"
    , Std_ReturnType, ctypes.c_uint8
    , [ ctypes.c_uint32 ]
    )
    def log_stop( self, timeout ) :
        """!
        @brief Stopping the logging of raw Ethernet frames to a log file

        This function disables the logging of raw Ethernet frames to the
        configured log file.

        @param timeout : `int` <br>

        @return `int`

        @see log_config()
        @see C shared library equivalent Ra_Log_Stop() in Ra.h
        """

        assert( type(timeout) is int )

        return [ ctypes.c_uint32( timeout ) ]
    # end def


    @RA_API \
    ( "Ra_Replay_Config"
    , Std_ReturnType, ctypes.c_uint8
    , [ ctypes.c_char_p, Ra_Mode ]
    )
    def replay_config( self, replay_file, mode ) :
        """!
        @brief Configure the replay of raw Ethernet frames

        This function sets a replay file from where recorded (logged) raw
        Ethernet frames are read later and replayed into the system. The mode
        defines the behaviour in which fashion the frames are inserted.


        @param replay_file : `str` <br>
        a path to the replay file

        @param mode : `Ra_Mode` <br>
        the mode of the replaying behaviour

        @return `str`, `Ra_Mode`

        @see replay_start()
        @see Ra_Mode
        @see C shared library equivalent Ra_Replay_Config() in Ra.h
        """

        assert( type(replay_file) is unicode or \
                type(replay_file) is str        )

        if not replay_file.endswith( ".pcap" ) :
            replay_file = replay_file + ".pcap"

        if not (type(mode) is Ra_Mode) :
            mode = Ra_Enum.cast( Ra_Mode, mode )

        if not os.path.exists( replay_file ) :
            with open( replay_file, "w+" ) as f: pass

        self._replay_file = ctypes.c_char_p( replay_file )

        return [ self._replay_file, mode ]
    # end def



    @RA_API \
    ( "Ra_Replay_Start"
    , Std_ReturnType, ctypes.c_uint8
    , [ ctypes.c_uint32 ]
    )
    def replay_start( self, leap_time ) :
        """!
        @brief Replay a PCAP file

        This method allows to 'replay' stored Ethernet frames which means that
        all frames are either transmitted to the connected MotionWise platform or
        transmitted directly to the RA shared library user. The stored frames
        are read from a configured PCAP file which can be configured by using
        the set_logandreplay_config() method.

        To implement a repeating replay functionality the combination of the
        replay_start() and replay_waitforfinish() methods is necessary, e.g.:

        ~~~{.py}
          ra = RA()
          while True :
              // starting replay
              ra.replay_start()
              // wait max. 1sec to replay the file
              ra.replay_waitforfinish( 1000 )
        ~~~

        @param leap_time : `int` <br>
        time in micro seconds in which the packets are sent in advance
        to original time interval

        @return { `int`, `None` }

        @see replay_waitforfinish()
        @see set_logandreplay_config()
        @see C shared library equivalent Ra_Replay_Start() in Ra.h
        """

        if self._replaying is None \
        or self._replaying is False :
            self._replaying = True
        else :
            self._verbose( "already replaying ==> NOP" )
            return None

        self._verbose( "starting replaying of configured PCAP file" )
        return [ ctypes.c_uint32( leap_time ) ]
    # end def


    @RA_API \
    ( "Ra_Replay_Wait"
    , Std_ReturnType, ctypes.c_uint8
    , [ ctypes.c_uint32 ]
    )
    def replay_wait( self, timeout_ms ) :
        """!
        @brief Stopping the replay from a PCAP file

        This method finalizes the replay from a PCAP file, but it assures
        that a specific amount of time (millisec) is waited before the replay
        functionality is stopped.

        @param timeout_ms : `int` <br>
        time in ms to wait for the end of the replaying, otherwise abort if the
        timeout has elapsed

        @return { `int`, `None` }

        @see replay_start()
        @see C shared library equivalent Ra_Replay_Wait() in Ra.h
        """

        if self._replaying is None \
        or self._replaying is False :
            self._verbose( "RA has not started the replaying functionality!" )
            return None
        else :
            self._replaying = False

        self._verbose( "finalizing replaying of configured PCAP file with "
                       "timeout '%s'", timeout_ms )
        return [ ctypes.c_uint32( timeout_ms ) ]
    # end def

    @RA_API \
    ( "Ra_Replay_Abort"
    , Std_ReturnType, ctypes.c_uint8
    )
    def replay_abort( self ) :
        """!
        @brief Immediately Stop replaying raw Ethernet frames from the replay

        The started frame replay from the function replay_start() is forced
        to stop. This function does not wait for the replay to finish, and returns
        immediately (In contrast to replay_wait(), which allows a running replay
        to complete).

        @return None

        @see replay_start()
        @see C shared library equivalent Ra_Replay_Abort() in Ra.h
        """

        return [ ]
    # end def



    # RA Logging and Tracing Configuration API Wrapper Functions

    @RA_API \
    ( "Ra_Config_Log"
    , Std_ReturnType, ctypes.c_uint8
    , [ ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint8 ]
    )
    def config_log( self, swc_id, group, level ) :
        """!
        @brief Change log configuration for SWC(s)

        This function allows to re-configure the logging setting on the
        MotionWise for specific SWC(s), by sending out an configuration frame, e.g.:

        ~~~{.py}
        # ra is an RA object
        
        # sets for SWC ID 5 the group 1 to level 'error'
        ra.config_log( 5, 1, "error" )
        
        # sets for SWC ID 8 the groups 2,4 and 6 to levels 'error' and 'trace'
        ra.config_log( 8, [ 2,4,6 ], [ "error", "trace" ] )
        ~~~

        @param swc_id : `int` <br>
        the id of the SWC to configure. Use the SWCID_<SWC_name> defines
        from Rte_Type.h

        @param group : `Ra_Config_Log_Group` <br>
        either one group instance or a list of the used logging group (bitmask) instances

        @param level : `Ra_Config_Log_Level` <br>
        either one used logging level instance or a list of level instances


        @return `int`, `Ra_Config_Log_Group`, `Ra_Config_Log_Level` 

        @see C shared library equivalent Ra_Config_Log() in Ra.h
        """

        if type(swc_id) is not int :
            _error( "swc id '%s' is not an integer value", swc_id, scope = 1 )

        _group = Ra_Enum.bitmask( Ra_Config_Log_Group, group )
        _level = Ra_Enum.bitmask( Ra_Config_Log_Level, level )

        self._verbose( "setting log configuration for SW-C '%s' to "
                       "group '0x%x' and level '0x%x'", swc_id, _group, _level )

        return [ ctypes.c_uint8( swc_id ), ctypes.c_uint8( _group ), ctypes.c_uint8( _level ) ]
    # end def


    @RA_API \
    ( "Ra_Config_LogSink"
    , Std_ReturnType, ctypes.c_uint8
    , [ Ra_Config_Log_Sink ]
    )
    def config_log_sink( self, sink ) :
        """!
        @brief Change the system wide log sink

        This function re-configures the system wide used logging sink for the
        MotionWise by sending out an appropriate configuration frame.
        It can be selected either be the (default) UART or the Ethernet sink.
        E.g.:
        
        ~~~{.py}
        # ra is an RA object
        
        # set the zFAS logging and tracing sink to Ethernet
        ra.config_log_sink( "eth" )
        ~~~

        @param sink : `Ra_Config_Log_Sink` <br>
        the sink which shall be configured
        
        @return { `int`, `None` }

        @see C shared library equivalent Ra_Config_LogSink() in Ra.h
        """

        log_sink = Ra_Enum.cast( Ra_Config_Log_Sink, sink )
        if log_sink is None :
            _error( "logging sink '%s' is an invalid Ra_Config_Log_Sink value", sink, scope = 1 )

        self._verbose( "setting logging system sink to '%s'", sink )
        return [ log_sink ]
    # end def


    @RA_API \
    ( "Ra_Config_LogLevel"
    , Std_ReturnType, ctypes.c_uint8
    , [ ctypes.c_uint8 ]
    )
    def config_log_level( self, level ) :
        """!
        @brief Change the system wide log level

        This function re-configures the system wide logging option/level for the
        MotionWise.

        @param level : `Ra_Config_Log_Level` <br>
        either one level instance or a list of level instances
        
        @return { `int`, `None` }

        @see C shared library equivalent Ra_Config_LogLevel() in Ra.h
        """
        _level = None

        if  isinstance( level, int ) \
        and level == 0 :
            _level = 0x00
        else :
            _level = Ra_Enum.bitmask( Ra_Config_Log_Level, level )

        self._verbose( "setting logging system level to '0x%x'", _level )
        return [ ctypes.c_uint8( _level ) ]
    # end def


    @RA_API \
    ( "Ra_Config_LogReset"
    , Std_ReturnType, ctypes.c_uint8
    )
    def config_log_reset( self ) :
        """!
        @brief Reset the system wide log levels

        This function resets the system wide logging configuration for the
        MotionWise platform.

        @return { `int`, `None` }

        @see C shared library equivalent Ra_Config_LogReset() in Ra.h
        """

        self._verbose( "re-setting system wide log levels" )
        return []
    # end def


    @RA_API \
    ( "Ra_Config_LogCoded"
    , Std_ReturnType, ctypes.c_bool
    )
    def config_log_coded( self, enable ) :
        """!
        @brief Enable/Disable the system wide coded logging

        This function enables/disables the MotionWise feature for coded logging
        messages which are send from the MotionWise platform to the debug host.

        @param enable : `bool` <br>
        state of the coded logging

        @return `bool`

        @see C shared library equivalent Ra_Config_LogCoded() in Ra.h
        """

        if not isinstance( enable, bool ) :
            _error( "invalid boolean parameter '%s'", enable, scope = 1 )
            return None

        self._verbose( "configuring log coded to '%s'", enable )
        return [ enable ]
    # end def


    ### NEW RA TRACING CFG API!!!

    @RA_API \
    ( "Ra_Config_Trace"
    , Std_ReturnType, ctypes.c_uint8
    , [ ctypes.c_uint8, ctypes.c_uint8 ]
    )
    def config_trace( self, enable, host ) :
        """!
        @brief Configure trace

        This function sets the trace configuration.


        @param enable : `int` <br>
        state of the trace configuration

        @param host : `int` <br>
        the unique host parameter to configure


        @return `int`, `int`

        @see C shared library equivalent Ra_Config_Trace() in Ra.h
        """
        if  not isinstance( enable, int ) :
            _error( "invalid parameter '%s'", enable, scope = 1 )
        if  not isinstance( host, int ) :
            _error( "invalid host parameter '%s'", host, scope = 1 )

        self._verbose( "setting trace to '0x%x'", enable )
        return [ ctypes.c_uint8( enable ), ctypes.c_uint8( host ) ]
    # end def

    @RA_API \
    ( "Ra_Config_TraceEvent"
    , Std_ReturnType, ctypes.c_uint8
    , [ ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint8 ]
    )
    def config_trace_event( self, event_type, enable, host ) :
        """!
        @brief Configure trace event

        This function sets the trace event configuration.


        @param event_type : `int` <br>
        the unique event type number (ID) to configure

        @param enable : `int` <br>
        state of the trace event configuration

        @param host : `int` <br>
        the unique host parameter to configure


        @return `int`, `int`, `int`

        @see C shared library equivalent Ra_Config_TraceEvent() in Ra.h
        """
        _id = event_type

        if  not isinstance( enable, int ) :
            _error( "invalid parameter '%s'", enable, scope = 1 )
        if  not isinstance( host, int ) :
            _error( "invalid host parameter '%s'", host, scope = 1 )
        if  not isinstance( _id, int ) :
            _error( "invalid parameter '%s'", _id, scope = 1 )

        self._verbose( "setting trace event '0x%x' to '0x%x'", _id, enable )
        return [ ctypes.c_uint8( _id ), ctypes.c_uint8( enable ), ctypes.c_uint8( host ) ]
    # end def

    @RA_API \
    ( "Ra_Config_TraceRunnable"
    , Std_ReturnType, ctypes.c_uint8
    , [ ctypes.c_uint16, ctypes.c_uint8, ctypes.c_uint8 ]
    )
    def config_trace_runnable( self, runnable_id, enable, host ) :
        """!
        @brief Configure trace runnable

        This function sets the trace runnable configuration.


        @param runnable_id : `int` <br>
        the unique runnable number (ID) to configure

        @param enable : `int` <br>
        state of the trace runnable configuration

        @param host : `int` <br>
        the unique host parameter to configure


        @return `int`, `int`, `int`

        @see C shared library equivalent Ra_Config_TraceRunnable() in Ra.h
        """
        _id = runnable_id

        if  not isinstance( enable, int ) :
            _error( "invalid parameter '%s'", enable, scope = 1 )
        if  not isinstance( host, int ) :
            _error( "invalid host parameter '%s'", host, scope = 1 )
        if  not isinstance( _id, int ) :
            _error( "invalid parameter '%s'", _id, scope = 1 )

        self._verbose( "setting trace runnable '0x%x' to '0x%x'", _id, enable )
        return [ ctypes.c_uint16( _id ), ctypes.c_uint8( enable ), ctypes.c_uint8( host ) ]
    # end def

    @RA_API \
    ( "Ra_Config_TraceTask"
    , Std_ReturnType, ctypes.c_uint8
    , [ ctypes.c_uint32, ctypes.c_uint8, ctypes.c_uint8 ]
    )
    def config_trace_task( self, task_id, enable, host ) :
        """!
        @brief Configure trace task

        This function sets the trace task configuration.


        @param task_id : `int` <br>
        the unique task number (ID) to configure

        @param enable : `int` <br>
        state of the trace task configuration

        @param host : `int` <br>
        the unique host parameter to configure


        @return `int`, `int`, `int`

        @see C shared library equivalent Ra_Config_TraceTask() in Ra.h
        """
        _id = task_id

        if  not isinstance( enable, int ) :
            _error( "invalid parameter '%s'", enable, scope = 1 )
        if  not isinstance( host, int ) :
            _error( "invalid host parameter '%s'", host, scope = 1 )
        #if  not isinstance( _id, int ) :
        #    _error( "invalid parameter '%s'", _id, scope = 1 )

        self._verbose( "setting trace task '0x%x' to '0x%x'", _id, enable )
        return [ ctypes.c_uint32( _id ), ctypes.c_uint8( enable ), ctypes.c_uint8( host ) ]
    # end def

    @RA_API \
    ( "Ra_Config_TraceDriver"
    , Std_ReturnType, ctypes.c_uint8
    , [ ctypes.c_uint32, ctypes.c_uint8, ctypes.c_uint8 ]
    )
    def config_trace_driver( self, driver_id, enable, host ) :
        """!
        @brief Configure trace driver

        This function sets the trace driver configuration.


        @param driver_id : `int` <br>
        the unique driver number (ID) to configure

        @param enable : `int` <br>
        state of the trace driver configuration

        @param host : `int` <br>
        the unique host parameter to configure


        @return `int`, `int`, `int`

        @see C shared library equivalent Ra_Config_TraceDriver() in Ra.h
        """
        _id = driver_id

        if  not isinstance( enable, int ) :
            _error( "invalid parameter '%s'", enable, scope = 1 )
        if  not isinstance( host, int ) :
            _error( "invalid host parameter '%s'", host, scope = 1 )
        if  not isinstance( _id, int ) :
            _error( "invalid parameter '%s'", _id, scope = 1 )

        self._verbose( "setting trace driver '0x%x' to '0x%x'", _id, enable )
        return [ ctypes.c_uint32( _id ), ctypes.c_uint8( enable ), ctypes.c_uint8( host ) ]
    # end def

    @RA_API \
    ( "Ra_Config_TraceISR"
    , Std_ReturnType, ctypes.c_uint8
    , [ ctypes.c_uint32, ctypes.c_uint8, ctypes.c_uint8 ]
    )
    def config_trace_isr( self, isr_id, enable, host ) :
        """!
        @brief Configure trace ISR

        This function sets the trace ISR configuration.


        @param isr_id : `int` <br>
        the unique ISR number (ID) to configure

        @param enable : `int` <br>
        state of the trace ISR configuration

        @param host : `int` <br>
        the unique host parameter to configure


        @return `int`, `int`, `int`

        @see C shared library equivalent Ra_Config_TraceISR() in Ra.h
        """
        _id = isr_id

        if  not isinstance( enable, int ) :
            _error( "invalid parameter '%s'", enable, scope = 1 )
        if  not isinstance( host, int ) :
            _error( "invalid host parameter '%s'", host, scope = 1 )
        if  not isinstance( _id, int ) :
            _error( "invalid parameter '%s'", _id, scope = 1 )

        self._verbose( "setting trace ISR '0x%x' to '0x%x'", _id, enable )
        return [ ctypes.c_uint32( _id ), ctypes.c_uint8( enable ), ctypes.c_uint8( host ) ]
    # end def

    @RA_API \
    ( "Ra_Config_TraceSetTrigger"
    , Std_ReturnType, ctypes.c_uint8
    , [ ctypes.c_uint32, ctypes.c_uint8 ]
    )
    def config_trace_set_trigger( self, trigger_id, host ) :
        """!
        @brief Set trace trigger configuration 

        This function sets the trace trigger configuration.


        @param trigger_id : `int` <br>
        the unique trigger number (ID) to configure

        @param host : `int` <br>
        the unique host parameter to configure


        @return `int`, `int`

        @see C shared library equivalent Ra_Config_TraceSetTrigger() in Ra.h
        """
        _id = trigger_id

        if  not isinstance( _id, int ) :
            _error( "invalid parameter '%s'", _id, scope = 1 )
        if  not isinstance( host, int ) :
            _error( "invalid host parameter '%s'", host, scope = 1 )

        self._verbose( "setting trace trigger '0x%x'", _id )
        return [ ctypes.c_uint32( _id ), ctypes.c_uint8( host ) ]
    # end def




    # RA Routing Configuration API Wrapper Functions

    @RA_API \
    ( "Ra_Config_RoutingReset"
    , Std_ReturnType, ctypes.c_uint8
    )
    def config_routing_reset( self ) :
        """!
        @brief Reset routing configuration to default values

        This function loads the default routing information. To send it to the
        MotionWise platform use the function config_routing_sync() function.

        @return { `int`, `None` }

        @see C shared library equivalent Ra_Config_RoutingReset() in Ra.h
        """

        self._verbose( "re-setting routing configuration to default values" )
        return []
    # end def


    @RA_API \
    ( "Ra_Config_RoutingSWC"
    , Std_ReturnType, ctypes.c_uint8
    , [ ctypes.c_uint8, Ra_Config_Routing_Mode ]
    )
    def config_routing_swc( self, swc_id, operation_mode ) :
        """!
        @brief Configure routing of all frames sent by a specific SWC

        This function sets the routing information for all frames of a specific SWC.
        To send it to the MotionWise platform use the function config_routing_sync() function.


        @param swc_id : `int` <br>
        the unique SWC number (ID) to configure

        @param operation_mode : `Ra_Config_Routing_Mode` <br>
        routing configuration mode for this SWC


        @return { `int`, `None` }

        @see C shared library equivalent Ra_Config_RoutingSWC() in Ra.h
        """

        operation_mode = Ra_Enum.cast( Ra_Config_Routing_Mode, operation_mode )
        if operation_mode is None :
            _error( "routing configuration mode '%s' is an invalid "
                    "Ra_Config_Routing_Mode value", operation_mode, scope = 1 )

        self._verbose( "setting SWC ID '%s' to routing configuration "
                       "mode '%s'" % ( swc_id, operation_mode,) )
        return [ ctypes.c_uint8( swc_id ), operation_mode ]
    # end def


    @RA_API \
    ( "Ra_Config_RoutingPort"
    , Std_ReturnType, ctypes.c_uint8
    , [ ctypes.c_uint16, Ra_Config_Routing_Mode ]
    )
    def config_routing_port( self, output_port_id, operation_mode ) :
        """!
        @brief Configure routing of a specific output Port of an SWC

        This function sets the routing information for a port of a specific SWC.
        To send it to the MotionWise platform use the function config_routing_sync() function.


        @param output_port_id : `int` <br>
        the unique output port number (ID) to configure

        @param operation_mode : `Ra_Config_Routing_Mode` <br>
        the routing configuration mode for this port


        @return { `int`, `None` }

        @see C shared library equivalent Ra_Config_RoutingPort() in Ra.h
        """

        operation_mode = Ra_Enum.cast( Ra_Config_Routing_Mode, operation_mode )
        if operation_mode is None :
            _error( "routing configuration mode '%s' is an invalid "
                    "Ra_Config_Routing_Mode value", operation_mode, scope = 1 )

        self._verbose( "setting Port ID '%s' to routing configuration "
                       "mode '%s'" % ( output_port_id, operation_mode,) )
        return [ ctypes.c_uint16( output_port_id ), operation_mode ]
    # end def


    @RA_API \
    ( "Ra_Config_RoutingFrame"
    , Std_ReturnType, ctypes.c_uint8
    , [ ctypes.c_uint16, Ra_Config_Routing_Mode ]
    )
    def config_routing_frame( self, frame_id, operation_mode ) :
        """!
        @brief Configure routing of a specific Frame ID

        This function sets the routing information for a specific frame ID.
        To send it to the MotionWise platform use the function config_routing_sync() function.

        @param frame_id : `int` <br>
        the unique frame number (ID) to configure

        @param operation_mode : `Ra_Config_Routing_Mode` <br>
        the routing configuration mode for this middleware frame


        @return { `int`, `None` }

        @see C shared library equivalent Ra_Config_RoutingFrame() in Ra.h
        """

        operation_mode = Ra_Enum.cast( Ra_Config_Routing_Mode, operation_mode )
        if operation_mode is None :
            _error( "routing configuration mode '%s' is an invalid "
                    "Ra_Config_Routing_Mode value", operation_mode, scope = 1 )

        self._verbose( "setting Frame ID '%s' to routing configuration "
                       "mode '%s'" % ( frame_id, operation_mode,) )
        return [ ctypes.c_uint16( frame_id ), operation_mode ]
    # end def


    @RA_API \
    ( "Ra_Config_RoutingSync"
    , Std_ReturnType, ctypes.c_uint8
    )
    def config_routing_sync( self ) :
        """!
        @brief Synchronizing the routing information on MotionWise platform

        All changes made by the the functions config_routing_reset(),
        config_routing_swc(), config_routing_port() are performed only locally.
        This function transmits the current local routing information to the MotionWise.

        @return { `int`, `None` }

        @see C shared library equivalent Ra_Config_RoutingSync() in Ra.h
        """

        self._verbose( "transmitting (sync) routing configuration" )
        return []
    # end def

    @RA_API( "Ra_Get_VLID_for_Frame"
                        , rtype = ctypes.c_int32
                        , atype = [ ctypes.c_uint16, Ra_Config_Routing_Mode ]
                        )
    def get_VLID_for_frame( self, frame_id, operation_mode ) :
        """!
        @brief Get a Virtual Link ID (VLID) for a specific frame ID

        Getting VLID based on mode values for the specific frame: RA_CFG_ROUTE_DEFAULT, RA_CFG_ROUTE_RECORD, RA_CFG_ROUTE_REPLAY
        and specifies which lookup table is used: VLID_Default, VLID_Record, VLID_Replay.


        @param frame_id : `int` <br>
        frame ID of Middleware DEX frame to decode into the VLID

        @param operation_mode : `Ra_Config_Routing_Mode` <br>
        mode is one of the values: RA_CFG_ROUTE_DEFAULT, RA_CFG_ROUTE_RECORD, RA_CFG_ROUTE_REPLAY
        and specifies which lookup table is used: VLID_Default, VLID_Record, VLID_Replay


        @return `int`, `Ra_Config_Routing_Mode`

        @see C shared library equivalent Ra_Get_VLID_for_frame() in Ra.h
        """
        operation_mode = Ra_Enum.cast( Ra_Config_Routing_Mode, operation_mode )
        if operation_mode is None :
            _error( "routing configuration mode '%s' is an invalid "
                    "Ra_Config_Routing_Mode value", operation_mode, scope = 1 )


        return [ ctypes.c_uint16( frame_id ), operation_mode ]
    #end def



    @RA_API \
    ( "Ra_gPTP_GetZGT"
    , Std_ReturnType, ctypes.c_uint8
    , [ ctypes.POINTER( ctypes.c_uint64 ) ]
    )
    def _gptp_get_zgt( self, time_stamp ) :
        """!
        @private
        @brief Returns the ZGT

        This internal function returns the gPTP synchronized ZGT time stamp. Please note that
        in fact, this function's return values differ from Std_ReturnType. Refer to
        the definition of Ra_gPTP_Error for further details.

        @param time_stamp : `Dt_RECORD_Timestamp` <br>
        ZGT time stamp as a RTE time stamp struct

        @return `Dt_RECORD_Timestamp`

        @see gptp_get_zgt()
        @see C shared library equivalent Ra_gPTP_GetZGT() in Ra.h
        """

        return [ time_stamp ]
    # end def

    def gptp_get_zgt( self ) :
        """!
        @brief Returns the current ZGT time stam

        This function returns the gPTP synchronized ZGT time stamp which is stored
        inside the RA library. Please note that in fact, this function's return 
        values differ from Std_ReturnType. Refer to the definition of Ra_gPTP_Error
        for further details.

        @return `int`

        @see _gptp_get_zgt()
        @see C shared library equivalent Ra_gPTP_GetZGT() in Ra.h
        """
        time_stamp     = ctypes.c_uint64( 0 )
        time_stamp_ptr = ctypes.POINTER( ctypes.c_uint64 )( time_stamp )

        self._gptp_get_zgt( time_stamp_ptr )

        self._verbose( "getting gPTP ZGT: %s | %s", time_stamp, time_stamp_ptr )

        return time_stamp.value
    # end def


    @RA_API \
    ( "Ra_TraceLog_Callback_Add"
    , Std_ReturnType, ctypes.c_uint8
    , [ ctypes.CFUNCTYPE( None, ctypes.c_void_p ) ]
    )
    def tracelog_callback_add( self, callback ) :
        """!
        @brief Specify a callback for incoming logging/tracing messages

        This function sets a callback hook which is called when the RA library
        receives logging/tracing messages via the Ethernet interface. To receive
        such messages, the sink on the MotionWise platform has to be configured to Ethernet
        (see config_log_sink()).

        @param callback : `def()` <br>
        a logging and tracing function which returns a pointer to a 
        Ra_TraceLog_Message structure which contains either a Ra_TraceLog_LogData, 
        a Ra_TraceLog_TraceData or a Ra_TraceLog_MemDumpData

        @return `int`

        @see C shared library equivalent Ra_TraceLog_Callback_Add() in Ra.h
        """

        c_fct = self.CALLBACK_TYPES ["Ra_TraceLog_Cb"] (callback)
        self.callbacks[3][5].append( (callback, c_fct) )
        return [ c_fct ]
    # end def


    @RA_API \
    ( "Ra_TraceLog_Callback_Remove"
    , Std_ReturnType, ctypes.c_uint8
    , [ ctypes.CFUNCTYPE( None, ctypes.c_void_p ) ]
    )
    def tracelog_callback_remove( self, callback = None ) :
        """!
        @brief Removes the logging/tracing callback

        This function just removes the callback from the internal logic.
        It does not mean the MotionWise platform sink is re-configured. If Ethernet sink
        is still active the RA library just drops the logging/tracing
        messages which are received through the Ethernet interface.

        @param callback : `def()` <br>
        a logging and tracing function function which returns a pointer to 
        a Ra_TraceLog_Message structure which contains either a Ra_TraceLog_LogData,
        a Ra_TraceLog_TraceData or a Ra_TraceLog_MemDumpData

        @return { `int`, `None` }

        @see C shared library equivalent Ra_TraceLog_Callback_Remove() in Ra.h
        """

        if callback is None :
            return None

        c_fct = None

        for c in self.callbacks[3][5] :
            if c[0] == callback :
                c_fct = c[1]
                #self.callbacks[3][5].remove( c )
                break

        return [ c_fct ]
    # end def


    @RA_API \
    ( "Ra_Log_Callback_Add"
    , Std_ReturnType, ctypes.c_uint8
    , [ ctypes.CFUNCTYPE( None, ctypes.c_void_p ) ]
    )
    def log_callback_add( self, callback ) :
        """!
        @brief Specify a callback for incoming logging messages

        This function sets a callback hook which is called when the RA library
        receives logging messages via the Ethernet interface. To receive
        such messages, the sink on the board has to be configured to Ethernet
        (see Ra_Config_LogSink()).

        @param callback : `def()` <br>
        a logging function which returns a pointer to a Ra_TraceLog_Message
        structure which contains only Ra_TraceLog_LogData

        @return `int`

        @see C shared library equivalent Ra_Log_Callback_Add() in Ra.h
        """

        c_fct = self.CALLBACK_TYPES ["Ra_TraceLog_Cb"] (callback)
        self.callbacks[3][5].append( (callback, c_fct) )
        return [ c_fct ]
    # end def


    @RA_API \
    ( "Ra_Log_Callback_Remove"
    , Std_ReturnType, ctypes.c_uint8
    )
    def log_callback_remove( self ) :
        """!
        @brief Removes the logging callback

        This function just removes the callback from the internal logic.
        It does not mean the MotionWise sink is re-configured. If Ethernet sink
        is still active the RA library just drops the logging
        messages which are received through the Ethernet interface.

        @return { `int`, `None` }

        @see C shared library equivalent Ra_Log_Callback_Remove() in Ra.h
        """

        return []
    # end def


    @RA_API \
    ( "Ra_Profiling_Callback_Add"
    , Std_ReturnType, ctypes.c_uint8
    , [ ctypes.CFUNCTYPE( None, ctypes.c_void_p ) ]
    )
    def profiling_callback_add( self, callback ) :
        """!
        @brief Specify a profiling callback for incoming trace frames

        This function sets a callback hook which is called when the RA library
        receives trace frames via the Ethernet interface. To receive
        such messages, the sink on the MotionWise platform has to be configured to Ethernet
        (see Ra_Config_LogSink()).

        @param callback : `def()` <br>
        Hook function which returns a pointer to a profiling
        structure which contains state of the various SW-Cs and its runnables 
        (state, runtime consumed so far, etc.)

        @return `int`

        @see C shared library equivalent Ra_Profiling_Callback_Add() in Ra.h
        """

        c_fct = self.CALLBACK_TYPES ["Ra_TraceLog_Cb"] (callback)
        self.callbacks[3][5].append( (callback, c_fct) )
        return [ c_fct ]
    # end def


    @RA_API \
    ( "Ra_Profiling_Callback_Remove"
    , Std_ReturnType, ctypes.c_uint8
    )
    def profiling_callback_remove( self ) :
        """!
        @brief Removes the profiling callback

        This function just removes the callback from the internal logic.
        It does not mean the MotionWise platform sink is re-configured. If Ethernet sink
        is still active the RA library just drops the trace
        messages which are received through the Ethernet interface.

        @return { `int`, `None` }

        @see C shared library equivalent Ra_Profiling_Callback_Remove() in Ra.h
        """

        return []
    # end def


    # --- RA TEST API ---
    @RA_API \
    ( "Ra_Forward_Frame"
    , None, None
    , [ ctypes.POINTER( ctypes.c_uint8 )
      , ctypes.c_uint8
      , ctypes.c_uint8
      ]
    )
    def _forward_frame ( self, ID, kind, payload, msg_counter = 0
                       , counter_status = 0, crc_status = 0
                       ) :
        """!
        @private
        @brief Internal test function to simulate an incoming frame
        """
        header = struct.pack(b"I", ((msg_counter << 24) | (kind << 20) | ID))
        frame = (ctypes.c_uint8 * (len(header) + len(payload))) \
                    (*(ord(b) for b in header + payload))
        # we need a pointer with an offset of 4 bytes for the Ra_Forward_Frame function
        payload_pointer = (ctypes.c_uint8 * len(payload)).from_buffer (frame, 4)

        return [ ctypes.cast( payload_pointer, ctypes.POINTER( ctypes.c_uint8 ))
               , ctypes.c_uint8 (counter_status)
               , ctypes.c_uint8 (crc_status)
               ]
    # end def

    @RA_API \
    ( "Ra_Distribute_Frame"
    , etype = None
    , rtype = None
    , atype = [ ctypes.POINTER( ctypes.c_uint8 )]
    )
    def distribute_frame (self, data) :
        """!
        @brief Test function to simulate an incoming frame's data

        This function forwards a complete incoming Middleware frame
        (header + payload, which is the UDP PlayLoad) to the distributing
        mechanism and callback function evaluation.

        @param data : `list` <br>
        a pointer to the start of the Middleware frame

        @return `list`

        @see C shared library equivalent Ra_Distribute_Frame() in Ra.h
        """

        # this function wraps and supersedes `Ra_Forward_Frame` -
        # `data` is the whole frame ( =  header + payload)
        data_pointer = (ctypes.c_uint8 * len(data)) ()
        for i, e in enumerate (data) :
            data_pointer [i] = ctypes.c_uint8 (e)
        return [ctypes.cast (data_pointer, ctypes.POINTER( ctypes.c_uint8 ))]
    # end def

    @RA_API \
    ( "Ra_Inject_Frame"
    , None, None
    , [ ctypes.c_uint32
      , ctypes.c_uint8
      , ctypes.POINTER( ctypes.c_uint8 )
      , ctypes.c_uint16
      ]
    )
    def _inject_frame ( self, ID, kind, data ) :
        """!
        @private
        @brief Test function to send directly a BE ETH frame

        This internal function forwards a complete incoming Middleware frame
        (header + payload, which is the UDP PlayLoad) to the distributing
        mechanism and callback function evaluation.


        @param ID : `int` <br>
        either data element ID for data exchange frames, otherwise it is the frame ID

        @param kind : `Ra_Kind` <br>
        specifies the frame kind

        @param data : `list` <br>
        a pointer to the Middleware frame of insertion


        @return `list`

        @see C shared library equivalent Ra_Inject_Frame() in Ra.h
        """

        #      |<--MWheader-->|<-- payload
        data = [ 0, 0, 0, 0 ] + data

        data_arr = (ctypes.c_uint8 * len( data ))()

        for i in range( len( data ) ) :
            data_arr[i] = data[i]

        return [ ctypes.c_uint32( ID )
               , ctypes.c_uint8( kind )
               , ctypes.cast( data_arr, ctypes.POINTER( ctypes.c_uint8 ))
               , ctypes.c_uint16( len( data ) )
               ]
    # end def




        # self.CALLBACK_TYPES ["Ra_Download_Cb"] = \
        #         ctypes.CFUNCTYPE (None, ctypes.c_uint8)

        # self.CALLBACK_TYPES ["Ra_Upload_Cb"] = \
        #         ctypes.CFUNCTYPE (None, ctypes.c_uint8, ctypes.c_void_p, ctypes.c_uint32)


    # # RA Block Data Load Configuration API Wrapper Functions

    @RA_API( "Ra_Config_BDLDownload"
                        , None, None
                        , [ ctypes.c_uint16
                          , ctypes.c_void_p
                          , ctypes.c_uint32
                          , ctypes.CFUNCTYPE( None, ctypes.c_uint8 )
                          ]
                        )
    def config_bdl_download( self, swc_id, data, callback_function ) :
        """!
        @private
        @brief Download a block of data

        This internal function allows to send/download data from the Debug/Test PC to the MotionWise platform.


        @param swc_id : `int` <br>
        the BDL ID of the SWC which should receive the data block

        @param data : `list` <br>
        a pointer to the data block size of data block in bytes `c_uint32`

        @param callback_function : `Ra_Data_Cb` <br>
        a pointer to function which will be called after the block data download has been finished


        @return `list`

        @see bdl_download()
        @see C shared library equivalent Ra_Config_BDLDownload() in Ra.h
        """

        cast = ( lambda x : int( x ) )

        if isinstance( data, basestring ) \
        or isinstance( data, str ) :
            cast = ( lambda x : ord( x ) )

        length = len( data )

        data_arr = (ctypes.c_uint8 * length)()
        for i in range( length ) :
            data_arr[i] = cast( data[i] )

        data_ptr = ctypes.cast( data_arr, ctypes.POINTER( ctypes.c_uint8 ))
        data_ptr = ctypes.cast( data_ptr, ctypes.POINTER( ctypes.c_void_p ))

        c_fct = self.CALLBACK_TYPES[ "Ra_Download_Cb" ]( callback_function )
        self.bdl_hooks.append( c_fct )

        self._verbose( "BDL: download: id=%s, length=%s, data=%s, data_arr=%s" % (swc_id, length, data, data_arr) )

        return \
        [ ctypes.c_uint16( swc_id )
        , data_ptr
        , ctypes.c_uint32( length )
        , c_fct
        ]
    # end def

    def bdl_download( self, swc_id, data, timeout = 3.0 ) :
        """!
        @brief Download a block of data

        This function allows to send/download data from the Debug/Test PC to the MotionWise platform.


        @param swc_id : `int` <br>
        the BDL ID of the SWC which should receive the data block

        @param data : `c_void_p` <br>
        a pointer to the data block size of data block in bytes `c_uint32`

        @param timeout : predefined to 3.0 <br>


        @return `bool`

        @see config_bdl_download()
        @see C shared library equivalent Ra_Config_BDLDownload() in Ra.h
        """

        result = queue.Queue( 1 )

        def _callback( ret ) :
            if ret == 0 :
                result.put( True )
            else :
                result.put( False )
        # end def

        self.config_bdl_download( swc_id, data, _callback )

        try :
            result = result.get( True, timeout )
        except queue.Empty :
            return False
        return result
    # end def

    @RA_API( "Ra_Config_BDLTriggerUpload"
                        , None, None
                        , [ ctypes.c_uint16
                          , ctypes.CFUNCTYPE( None, ctypes.c_uint8, ctypes.c_void_p, ctypes.c_uint32 )
                          ]
                        )
    def config_bdl_upload( self, swc_id, callback_function ) :
        """!
        @private
        @brief Upload a block of data


        This internal function allows to receive/upload data from the MotionWise platform to the debug/test PC.

        @param swc_id : `int` <br>
        the BDL ID of the SWC which should provide the data block

        @param callback_function : `Ra_Data_Cb` <br>
        a pointer to function which will be called after the block data upload has been finished


        @return `int`

        @see bdl_upload()
        @see C shared library equivalent Ra_Config_BDLTriggerUpload() in Ra.h
        """

        c_fct = self.CALLBACK_TYPES[ "Ra_Upload_Cb" ]( callback_function )
        self.bdl_hooks.append( c_fct )

        self._verbose( "BDL: upload: id=%s, hook=%s" % (swc_id, c_fct) )

        return \
        [ ctypes.c_uint16( swc_id )
        , c_fct
        ]
    # end def

    def bdl_upload( self, swc_id, timeout = 3.0 ) :
        """!
        @brief Upload a block of data

        This function allows to receive/upload data from the MotionWise platform to the debug/test PC.


        @param swc_id : `int` <br>
        the BDL ID of the SWC which should provide the data block

        @param timeout : predefined to 3.0 <br>


        @return `list`

        @see config_bdl_upload()
        @see C shared library equivalent Ra_Config_BDLTriggerUpload() in Ra.h
        """

        result = queue.Queue( 1 )
        data   = None
        length = None

        def _callback( ret, _data, _length ) :
            if ret == 0 :
                result.put( True )
            else :
                result.put( False )

            data     = _data
            length   = _length
        # end def

        self.config_bdl_upload( swc_id, _callback )

        try :
            result = result.get( True, timeout )
        except queue.Empty :
            return None

        if length is None \
        or result is not None :
            return None

        class Data( ctypes.Structure ) :
            _fields_ = [ ( "data", ctypes.c_uint8 * length ) ]

        data = ctypes.cast( data, ctypes.POINTER( Data ) )

        return data.contents.data
    # end def

    @RA_API( "Ra_Config_BDLReset"
                        , None, None
                        )
    def config_bdl_reset( self ) :
        """!
        @private
        @brief Reset Block Data Load

        This private function stops all ongoing BDL actions and clear the callback pointers.

        @return { `int`, `None` }

        @see C shared library equivalent Ra_Config_BDLReset() in Ra.h
        """

        self._verbose( "stopping ongoing BDL actions and clearing callbacks" )
        return []
    # end def


    # RA Other Configuration API Wrapper Functions

    @RA_API \
    ( "Ra_Config_DebugIP"
    , None, None
    , [ ctypes.c_uint32 ]
    )
    def config_debug_ip( self, ip_str ) :
        """!
        @private
        @brief Change the IP address of the debug PC

        This internal function changes the IP address of the debug PC for a running
        system on all hosts by transmitting an appropriate frame.

        @param ip_str : `str` <br>
        IP address in network byte order

        @return `str`

        @see C shared library equivalent Ra_Config_DebugIP() in Ra.h
        """

        ip_num   = struct.unpack  (b"@I", socket.inet_aton (ip_str)) [0]

        self._verbose( "setting debug IP address '%s' (%s)", ip_str, ip_num )

        return [ ctypes.c_uint32( ip_num ) ]
    # end def



    ## Persistence APIs

#    @RA_API \
#    ( "Ra_Persistence_SaveSWC"
#    , Std_ReturnType, ctypes.c_uint8
#    , [ ctypes.c_uint8 ]
#    )
#    def persistence_save_swc( self, swc_id ) :
#        """!
#        @brief TODO
#
#        TBD
#
#        @param  :  <br>
#
#        @see C shared library equivalent Ra_Persistence_SaveSWC() in Ra.h
#        """
#
#        self._verbose( "saving persistence data of SWC ID '%s' from MotionWise" % swc_id )
#
#        return [ ctypes.c_uint8( swc_id ) ]
#    # end def
#
#    @RA_API \
#    ( "Ra_Persistence_LoadSWC"
#    , Std_ReturnType, ctypes.c_uint8
#    , [ ctypes.c_uint8 ]
#    )
#    def persistence_load_swc( self, swc_id ) :
#        """!
#        @brief TODO
#
#        TBD
#
#        @param  :  <br>
#
#        @see C shared library equivalent Ra_Persistence_LoadSWC() in Ra.h
#        """
#
#        self._verbose( "loading persistence data of SWC ID '%s' to MotionWise" % swc_id )
#
#        return [ ctypes.c_uint8( swc_id ) ]
#    # end def
#
#    @RA_API \
#    ( "Ra_Persistence_Save"
#    , Std_ReturnType, ctypes.c_uint8
#    )
#    def persistence_save( self ) :
#        """!
#        @brief TODO
#
#        TBD
#
#        @param  :  <br>
#
#        @see C shared library equivalent Ra_Persistence_Save() in Ra.h
#        """
#
#        self._verbose( "saving persistence data of all SWCs from MotionWise" )
#
#        return [ ]
#    # end def
#
#    @RA_API \
#    ( "Ra_Persistence_Load"
#    , Std_ReturnType, ctypes.c_uint8
#    )
#    def persistence_load( self ) :
#        """!
#        @brief TODO
#
#        TBD
#
#        @param  :  <br>
#
#        @see C shared library equivalent Ra_Persistence_Load() in Ra.h
#        """
#
#        self._verbose( "loading persistence data of all SWCs to MotionWise" )
#
#        return [ ]
#    # end def




    #++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # PPA: START
    #      move functions below into callback_add and callback_remove functions!
    #      --> DO NOT USE THIS FUNCTION - THEY WILL BE DELETE IN THE NEAR FUTURE!
    #--------------------------------------------------------------------------

    def register_callback ( self, id, function
                          , type = None
                          , kind = 0
                          ) :
        """!
        @brief Register a callback function for a specific frame kind and ID

        This function callback is for receiving regular data element sent via
        MW frames use RA_DEX_KIND as kind and use Ra_<SWC>_<Port>_<Element> 
        as ID. Have a look at <B>Ra_Distributor_Ids.h</B> for a list of all
        available IDs.

        @param id : `int` <br>
        either data element ID for data exchange frames, otherwise it is the frame ID

        @param function : `Ra_Data_Cb` <br>
        the function to be called on data reception

        @param type : `int` <br>
        specifies the frame type

        @param kind : `Ra_Kind` <br>
        specifies the frame kind

        @return `Ra_Kind`,`int`

        @see C shared library equivalent Ra_Callback_Add() in Ra.h
        """  

        if isinstance (id, basestring) :
            id   = getattr (self.ra_model, id)
        if type is None :
            type = self.ra_model.ID2Type_Map.get (id, type)
        if isinstance (type, basestring) :
            type = self.TYPES.get (type, type)
        if type not in self.CALLBACK_TYPES :
            self.CALLBACK_TYPES [type] = ctypes.CFUNCTYPE \
                (None, ctypes.POINTER (type))
        c_fct  = self.CALLBACK_TYPES [type] (function)
        try:
            self._lib.Ra_Add_Reader (kind, id, c_fct)
            # we need to keep a reference to the c_fct object to avoid that
            # python garbage collects it which would case a problem once
            # the c-library wants to execute this callback
            self.callbacks [kind] [id].append   ((function, c_fct))
        except RA_Error as e:
            print ("Failed to register callback for Kind %d, ID: %d" % (kind, id))
            raise e
    # end def register_callback

    def unregister_callback (self, id, function, kind = 0) :
        """!
        @brief Unregister a callback function

        This function removes the specified function from the receive invocation
        list.

        @param id : `int` <br>
        either data element ID for data exchange frames, otherwise it is the frame ID

        @param function : `Ra_Data_Cb` <br>
        callback function to be removed

        @param kind : `Ra_Kind` <br>
        specifies the frame kind

        @return `Ra_Kind`,`int`,`Ra_Data_Cb`

        @see C shared library equivalent Ra_Callback_Remove() in Ra.h
        """

        for cb, c_fct in self.callbacks [kind] [id] :
            if cb is function :
                self._lib.Ra_Remove_Reader (kind, id, c_fct)
    # end def unregister_callback

    # PPA: END
    #--------------------------------------------------------------------------


    @classmethod
    def as_ctype_instance (cls, type, v) :
        if issubclass (type, ctypes.Structure) :
            if v is None :
                v = type()
            return cls._as_ctype_struct (type, v)
        elif issubclass (type, ctypes.Array) :
            if v is None :
                v = type()
            return cls._as_ctype_array (type, v)
        elif issubclass (type, (ctypes.c_float, ctypes.c_double, ctypes.c_longdouble)):
            if isinstance (v, basestring) and v.endswith (".0") :
                v = v [:-2]
            return type (float (v) or 0.0)
        elif issubclass (type, ( ctypes.c_byte, ctypes.c_ubyte
                               , ctypes.c_short, ctypes.c_ushort
                               , ctypes.c_int, ctypes.c_uint
                               , ctypes.c_long, ctypes.c_ulong
                               , ctypes.c_longlong, ctypes.c_ulonglong
                               )):
            if isinstance (v, basestring) and v.endswith (".0") :
                v = v [:-2]

            if v is None or not isinstance( v, int ) :
                return type( 0 )
            else :
                return type( v )
        return type (v or 0)
    # end def as_ctype_instance

    @classmethod
    def _as_ctype_struct (cls, type, v) :
        values = []
        for fn, ft in type._fields_ :
            if hasattr( v, "get" ) :
                values.append( cls.as_ctype_instance( ft, v.get (fn) ) )
            else :
                values.append( cls.as_ctype_instance( ft, None ) )
        return type (* values)
    # end def _as_ctype_struct

    @classmethod
    def _as_ctype_array (cls, type, v) :
        result = []
        for i in xrange (type._length_) :
            if v is not None :
                try :
                    vi = v [i]
                except IndexError :
                    vi = None
                result.append (cls.as_ctype_instance( type._type_, vi ) )
            else :
                result.append( cls.as_ctype_instance( type._type_, None ) )
        return type (* result)
    # end def _as_ctype_array

    @classmethod
    def as_python_instance (cls, v) :
        if isinstance (v, basestring) :
            v = cls.TYPES [v] ()
        if isinstance (v, ctypes._Pointer) :
            v = v.contents
        if isinstance (v, ctypes.Structure) :
            return cls._as_python_dict (v)
        if isinstance (v, ctypes.Array) :
            return cls._as_python_sequence (v)
        return v.value
    # end def as_python_instance

    @classmethod
    def _as_python_dict (cls, v) :
        result = dict () # use ordered dict ???
        for fn, ft in v._fields_ :
            result [fn] = cls.as_python_instance (getattr (v, fn))
        return result
    # end def _as_python_dict

    @classmethod
    def _as_python_sequence (cls, v) :
        result = []
        for vi in v :
            result.append (cls.as_python_instance (vi))
        return result
    # end def _as_python_sequence

# end class RA


def RA_Args( parser ) :
    """!
    @brief RA library arguments for debugging/development

    The RA library python arguments for debugging/development
    add argument group that enables debug messages, sets the 
    contract header folder path to DIR, sets the RA library 
    {libRA_win32.dll, libRA_win64.dll, libRA_linux32.so, libRA_linux64.so}
    search path to RA_LIB_DIR, sets the RA model file path to RA_MODEL. 

    @param parser : `argparse` <br>
    a parser object where the RA library options can be added to
    """

    default_msg = " (default: %(default)s)"

    ra_args = parser.add_argument_group \
        ( "optional generic RA library arguments for debugging/development")

    ra_args.add_argument \
        ( "--ra-verbose"
        , metavar = "LEVEL"
        , default = -1
        , help = "enables debug messages"
        )

    ra_args.add_argument \
        ( "--ra-contract"
        , metavar = "DIR"
        , default = pjoin (os.path.dirname(os.path.abspath(__file__)), "Contract_Header")
        , help = "set the contract header folder path to <DIR>" + default_msg
        )

    # --- development command line arguments below, should not be needed by SW-C suppliers ---
    # set the RA library {libRA_win32.dll, libRA_win64.dll, libRA_linux32.so, libRA_linux64.so}
    # search path to RA_LIB_DIR
    ra_args.add_argument \
        ( "--ra-lib"
        , metavar = "RA_LIB_DIR"
        , default = pjoin (os.path.dirname(os.path.abspath(__file__)), "bin")
        , help    = argparse.SUPPRESS
        )

    # set the RA model file path to RA_MODEL
    parser.add_argument \
        ( "--ra-model"
        , metavar = "RA_MODEL"
        , default = pjoin (os.path.dirname(os.path.abspath(__file__)), "RA_Model.py")
        , help   = argparse.SUPPRESS
        )

    parser.add_argument \
        ( "--ra-devel"
        , nargs   = "?"
        , default = ""
        , help   = argparse.SUPPRESS
        )
# end def



if __name__ == "__main__" :
    description = """\
        This script can be used to check and configure the RA library
        internal functionality. Some examples:

            Enable verbose mode
                RA.py --ra-verbose 0

            Use the PCAP transport backend
                RA.py --ra-backend pcap

    """

    parser = argparse.ArgumentParser \
            ( formatter_class = argparse.RawDescriptionHelpFormatter
            , description = textwrap.dedent (description)
            )

    RA_Args( parser )

    args = parser.parse_args()

    ra = RA( parser, args ) #, False )

    #ra.init( "pcap" )

    #ra.receiving_start()
    #ra.receiving_stop()
    #printf( ra.shutdown() )

    ra.init() #( RA_TL_PCAP )

    for swc_name in ra.get_swc_names() :
        print( "[%s]: %s" % \
        ( ra.get_host_name_of_swc_name( swc_name )
        , swc_name
        ) )

    for rid in range( 200 ) :
        rn = ra.get_runnable_name_of_runnable_id( rid )
        if rn is None :
            break
        print( "%s [= %s] -> %s" % \
        ( rid
        , rn
        , ra.get_swc_name_of_runnable_id( rid )
        ) )

    sys.exit(0)



    ra.receiving_start()

    # reconfiguration of the network
    # IMPORTANT: each call closes the transport backend, re-configures
    #            and opens the transport backend again
    # ra.set_network_config( { "SSH" :       { "ip":   "1.2.3.4" } } )
    # ra.set_network_config( { 3 :           { "port": "1234" } } )
    # ra.set_network_config()

    # re-setting the complete routing configuration
    # to the default routing
    ra.config_routing_reset()
    # setting routing for SWC
    ra.config_routing_swc( 8, RA_CFG_ROUTE_REPLAY )
    # setting routing for Ports
    ra.config_routing_port( 6, "default" )
    ra.config_routing_port( 6, "record" )
    ra.config_routing_swc ( 8, 1 )

    # setting routing config of a specific frame via mode
    ra.config_routing_frame( 123, 0 ) # or "default" or RA_CFG_ROUTE_DEFAULT
    ra.config_routing_frame( 231, "record" )  # or 1 or RA_CFG_ROUTE_RECORD
    ra.config_routing_frame(  23, RA_CFG_ROUTE_REPLAY ) # or 2 or "replay"

    # transmitting the routing config to MotionWise platform
    ra.config_routing_sync()

    # setting the debug IP address on all MotionWise hosts
    ra.config_debug_ip( "10.20.30.40" )
    ra.config_debug_ip( "192.168.1.40" )

    # setting external time synchronization period
    ra.external_time_sync( 50 )
    ra.external_time_sync( 20 )

    # def defences_hook( pfences ) :
    #     pass
    # # end def

    # ra.callback_add( "RA_CtApMapFusion_PpMBFfences_DeFences", defences_hook )


    # setting a log and replay config & di a replay
    if args.ra_backend == "pcap" :

        ra.log_config( "asdf.pcap" )
        ra.log_start()
        ra.log_stop( 1000 )

        ra.replay_config( "trace.pcap", RA_ONLINE )

        ra.replay_start( 10 )

        print( "%s" % ra.gptp_get_zgt() )
        print( "%s" % ra.gptp_get_zgt() )
        print( "%s" % ra.gptp_get_zgt() )

        ra.replay_stop( 1000 )
        time.sleep( 1 )

    ra._verbose( "swc ids:" )
    for swc_id in ra.get_swc_ids() :
        swc_name = ra.get_swc_name_of_swc_id( swc_id )
        frame_ids = ra.get_receive_frame_ids_of_swc_name( swc_name )

        rfid_str = ""
        if frame_ids is not None :
            for frame_id in frame_ids :
                rfid_str = "%s%s, " % ( rfid_str, frame_id )

        frame_ids = ra.get_send_frame_ids_of_swc_name( swc_name )

        sfid_str = ""
        if frame_ids is not None :
            for frame_id in frame_ids :
                sfid_str = "%s%s, " % ( sfid_str, frame_id )

        ra._verbose( "  %-3s: %s | %-30s\nrecv: [ %s ]\nsend: [ %s ]"
                   , swc_id
                   , swc_id == ra.get_swc_id_of_swc_name( swc_name )
                   , swc_name
                   , rfid_str
                   , sfid_str
                   )

    ra._verbose( "frame ids:" )
    for frame_id in ra.get_frame_ids() :
        swc_names = ra.get_receiver_swc_names_of_frame_id( frame_id )

        rsnm_str = ""
        if swc_names is not None :
            for swc_name in swc_names :
                rsnm_str = "%s%s, " % ( rsnm_str, swc_name )

        swc_names = ra.get_sender_swc_names_of_frame_id( frame_id )

        ssnm_str = ""
        if swc_names is not None :
            for swc_name in swc_names :
                ssnm_str = "%s%s, " % ( ssnm_str, swc_name )

        ra._verbose( "  %-3s:\nrecv: [ %s ]\nsend: [ %s ]"
                   , frame_id
                   , rsnm_str
                   , ssnm_str
                   )

    def tracelog( data ) :
        """!
        @brief Trace/log message

        This function allows trace log message data.

        @param data : `list` <br>
        a pointer to the trace/log message data
        """

        msg = ctypes.cast( data, ctypes.POINTER (Ra_TraceLog_Message))[0]
        print( "%s: %s %s %s" % ( msg.entry_type
          , msg.zgt_stamp
          , msg.component_id
          , msg.data ) )

    ra.tracelog_callback_add( tracelog )
#    ra.tracelog_callback_remove()

    # re-configuration of the MotionWise SWC logging
    ra.config_log( 1, LOG_GROUP_1, LOG_ERROR  )
    ra.config_log( 5, LOG_GROUP_5, LOG_INFO   )

    # re-configuration of the MotionWise logging sink
    ra.config_log_sink( "uart" )
    #ra.config_log_sink( "eth" )

    # re-configuration of the MotionWise logging level
    ra.config_log_level( "error" )


    # print( "TRACE 3:" )
    # ra.replay_config( "trace3.pcap", RA_OFFLINE )
    # ra.replay_start( 10 )
    # ra.replay_stop( 0 )


    ra.shutdown()
# end __main__
