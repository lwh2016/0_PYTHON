#!C:\Python27\python.exe

# Copyright (C) 2013 TTTech Computertechnik AG. All rights reserved
# Schoenbrunnerstrasse 7, A--1040 Wien, Austria. office@tttech.com
#
# ++
# Name
#    MotionWise_perf_client.py
#
# Purpose
#    Script for MotionWise runtime measurement
#
# Authors
#    Georg Wiesmann <georg.wiesmann@tttech-automotive.com>
#
# Revision Dates
#    09-Feb-2016 (HLI) taken from zFAS
#
# --

import RA
import re
import csv
import time
import ctypes
import logging
from multiprocessing import Pipe
from MotionWise.pm_measurement import HOSTS as HOST_MAP

logger = logging.getLogger(__name__)


class _Model(object):

    def __init__(self, ra_model):
        self._ifset = ra_model.IFSET
        self.id_to_runnable = ra_model.id_to_runnable
        self.SWCID_Map = ra_model.SWCID_Map
        #self.swc_name_to_swc_id = {v:k for k,v in self.SWCID_Map.iteritems()}
        self._swc_name_to_swc_id = {}
        self._swc_id_to_swc_name = {}

        for key, val in ra_model.SWCID_Map.iteritems() :
            # ignore the init SW-C
            if key == "INIT": continue
            self._swc_name_to_swc_id[ key ] = val
            self._swc_id_to_swc_name[ val ] = key
        
    def get_runnable_name_of_runnable_id(self, rid):
        return self.id_to_runnable.get(rid, rid)
        
    def get_swc_name_of_swc_id(self, swcid):
        #print (swcid)
        JseTest1= self.SWCID_Map.get(swcid, swcid)
        JseTest2= self._swc_id_to_swc_name.get(swcid, swcid)
        #print (JseTest1)
        print (JseTest2)
        return JseTest2

    def get_IFSET(self):
        return self._ifset


class _CsvConnection(object):
    """
    Imitates the behaviour of a multiprocessing.Connection but streams from a
    CSV file.
    """
    
    def __init__(self, csv_file):
        self.reader = None
        self.length = 0
        
        if csv_file:
            with open(csv_file, 'rb') as csvfile: 
                sep = b","
                quote = b"#"
                regex = re.compile(r"#HEADER[ ]*")
                lines = csvfile.readlines()
                start = 0
                
                if lines[0].startswith('sep'):
                    # get seperator 
                    sep = b"{}".format(lines[0].split('=')[-1][0])
                    start = 1
                
                for i, l in enumerate(lines):
                    # find header line
                    if l.startswith("#HEADER"):
                        lines[i] = regex.sub('', l)
                        start = i
                        break
                
                self.length = len(lines[start:])
                self.reader = csv.DictReader(lines[start:], 
                            delimiter=sep, quotechar=quote) 
       
    def poll(self):
        if None == self.reader:
            return False
        else:
            return self.reader.line_num < self.length
            
    def recv(self):
        if None == self.reader or not self.poll():
            raise EOFError
        else:
            d = self.reader.next()
            return d
    
    def send(self, item):
        pass
    
    def close(self):
        pass
 
 
class Proxy(RA.RA):
    """
    Proxy receives the trace events from the RA lib, converts them to a 
    dictionary and sends them to the MotionWise_Perf client. 
    """
    
    def __init__(self, args):
        RA.RA.__init__(self, init = False)
        self.host_id = HOST_MAP[args.host.upper()]['id']
        self.startup_finished = not args.startup
                  
        if not args.csv_file:
            self.parent_conn, self.child_conn = Pipe()
            self.tracelog_callback_add(self._recv_cb)
            self._forward_event = bool(args.pcap_file)
        else: 
            self.parent_conn = _CsvConnection(None)
            self.child_conn = _CsvConnection(args.csv_file)
            self._forward_event = True
        
    def _recv_cb(self, ptr):
        msg = ctypes.cast(ptr, ctypes.POINTER(RA.Ra_TraceLog_Message))[0]
        data = ctypes.cast(msg.data, ctypes.POINTER(RA.Ra_TraceLog_TraceData))

        # copy elements of object to dictionary
        _buffer = {}
        _buffer["host"] = msg.host_id  
        if msg.host_id != self.host_id:
            return 
            
        _buffer["swc"] = msg.component_id
        _buffer["zgt"] = msg.zgt_stamp
        _buffer["count"] = msg.msg_count
        if msg.entry_type == 3:
            _buffer["core"] = data[0].core_id
            _buffer["data"] = data[0].event_data
            _buffer["type"] = data[0].event_type
            
            if not self.startup_finished:
                if _buffer["type"] < 2:
                    rid = (_buffer["data"] >> 48) & 0xFFFF
                    self.startup_finished = not 'INIT' in \
                        self.get_runnable_name_of_runnable_id(rid).upper()
            
        elif msg.entry_type == 1:
            _buffer["core"] = 0
            coding = RA.Ra_TraceLog_LogNotCodedData
            data = ctypes.cast(msg.data, ctypes.POINTER(coding))[0]
            string = data.reconstructed_string
            if string.startswith('$SSH_TM') or string.startswith('$SRH_TM'):
                if string[7] == '':
                    _buffer["data"] = "%s|%s" % (string[0:7], string[8:])
                else:
                    _buffer["data"] = string
                _buffer["type"] = 0xFF
                _buffer["count"]  = ''
            else: return 
        else: return
        
        try:
            if msg.entry_type == 1 or self._forward_event: 
                self.parent_conn.send(_buffer)
        except IOError:
            # is excepted in the case the connection is already closed
            pass  
      
    def get_ra_model(self):
        return _Model(self.ra_model)

    def receiving_start(self, delay=0):
        self._forward_event = False
        RA.RA.receiving_start(self)
        time.sleep(delay)
        self._forward_event = True
        
            
__version__ = "$Revision: 80204 $".split()[1]

if __name__ == '__main__':
    pass
