# -*- coding: iso-8859-15 -*-
# Copyright (C) 2012 TTTech Computertechnik AG. All rights reserved
# Schoenbrunnerstrasse 7, A--1040 Wien, Austria. office@tttech.com
#
# ++
# Name
#
# Purpose
#
# Revision Dates
#    09-Feb-2016 (HLI) taken from zFAS
#
# --

import logging
import ctypes
import callback
from MotionWise import RA
from constants import EVENT_MAP
from abc import ABCMeta

__version__ = "$Revision: 80204 $".split()[1]

ENTRY_TYPE_LOG_TEXT  = 1
ENTRY_TPYE_LOG_CODED = 2
ENTRY_TYPE_TRACE     = 3

logger = logging.getLogger('MotionWise.pm_instrument.trace')


class Trace:
    __metaclass__ = ABCMeta
    
    def _start_runnable(self, data):
        self.rnbl_id = (data >> 48) & 0xFFFF        
    
    def _stop_runnable(self, data):
        self.rnbl_id = (data >> 48) & 0xFFFF
    
    def _task_switch(self, data):
        self.new_task_id = data & 0xFFFFFFFF
        self.old_task_id = (data >> 32) & 0xFFFFFFFF
    
    def _interrupt(self, data):
        self.duration = data & 0xFFFFFFFF
        self.isr_id = (data >> 32) & 0xFFFFFFFF
    
    def _start_driver(self, data):
        self.driver_id = (data >> 56) & 0xFF
    
    def _stop_driver(self, data):
        self.driver_id = (data >> 56) & 0xFF

    def _state_change(self, data):
        self.host_id = (data >> 56) & 0xFF
        self.old_state = (data >> 48) & 0xFF
        self.new_state = (data >> 40) & 0xFF
    
    def _checkpoint(self, data):
        self.checkpt_id = (data >> 48) & 0xFFFF
        self.checkpt_data = (data >> 16) & 0xFFFF

    def _input_signal(self, data):
        self.sig_id = (data >> 56) & 0xFF

    def _zgt_correction(self, data):
        self.zgt_corr_val = ctypes.c_int64(data).value
    
    def _pm_stack_peak(self, data):
        self.task_id = (data >> 32) & 0xFFFFFFFF
        self.stackval = data & 0xFFFFFFFF

    def _pm_runtime(self, data):
        self.rnbl_id = (data >> 48) & 0xFFFF
        self.cnt = (data >> 40) & 0xFF
        self.max = (data >> 20) & 0xFFFFF
        self.total = data & 0xFFFFF

    def _pm_heap(self, data):
        self.task_id = (data >> 32) & 0xFFFFFFFF
        self.heapval = data & 0xFFFFFFFF

    def _pm_r_nettime(self, data):
        self.rnbl_id = (data >> 48) & 0xFFFF
        self.total = (data >> 16) & 0xFFFFFFFF

    def trigger_callback(self):
        callback.invoke('event_received_callback_fun', 
            { 'swc': self.swc_id, 'host': self.host, 'zgt':self.time
            , 'count':self.seq, 'type':self.type, 'core':self.core
            , 'data':self.data, 'rid':self.__dict__.get('rnbl_id', '')})


class RawTrace (Trace):
    
    def __init__(self, _buffer):
        msg = ctypes.cast(_buffer, ctypes.POINTER(RA.Ra_TraceLog_Message))[0]
        data = ctypes.cast(msg.data, ctypes.POINTER(RA.Ra_TraceLog_TraceData))
        self.host = msg.host_id
        self.swc_id = msg.component_id
        self.time = msg.zgt_stamp
        self.seq = msg.msg_count
        self.is_trace = msg.entry_type == ENTRY_TYPE_TRACE
        self.is_log = not self.is_trace
        
        if self.is_trace:
            # is a tracing frame
            self.type = data[0].event_type
            self.core = data[0].core_id
            self.data = data[0].event_data
            
            # initialize trace object according to event_type 
            getattr(self, '_{}'.format(EVENT_MAP[self.type]))(self.data)
        else:
            if msg.entry_type == ENTRY_TYPE_LOG_TEXT:
                self.core = 0
                coding = RA.Ra_TraceLog_LogNotCodedData
                data = ctypes.cast(msg.data, ctypes.POINTER(coding))[0]
                string = data.reconstructed_string
                logger.debug('not coded log message: {}'.format(string))
                if string.startswith('$SSH_TM') or string.startswith('$SRH_TM'):
                    self.data = string.replace(',','|')
                    self.type = 0xFF
                    self.seq  = ''
                else: return
            else: return


class DictTrace (Trace):
    
    def __init__(self, _buffer):
        self.swc_id = int(_buffer["swc"])
        self.host = int(_buffer["host"])
        self.time = int(_buffer["zgt"])
        self.type = int(_buffer["type"])
        self.core = int(_buffer["core"])
        self.is_trace = self.type  != 0xFF
        self.is_log = not self.is_trace

        if self.is_trace:
            if type(_buffer["data"]) == str: 
                self.data = int(_buffer["data"], 0)
            else:
                self.data = int(_buffer["data"])
            self.seq = int(_buffer["count"])
            getattr(self, '_{}'.format(EVENT_MAP[self.type]))(self.data)
        else:
            self.seq = 0
            self.data = _buffer["data"]


if __name__ == '__main__':
    pass
