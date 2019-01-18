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

import trace
import pmcalc
import constants
import callback
import logging
import threading 
import traceback

__version__ = "$Revision: 80204 $".split()[1]
__all__ = [ 'receive_event_callback_add'
          , 'receive_event'
          , 'task_map_callback_add'
          , 'sequence_error_callback_add'
          , 'runnable_activation_callback_add'
          , 'runnable_netto_rt_callback_add'
          , 'runnable_gross_rt_callback_add'
          , 'driver_activation_callback_add'
          , 'driver_netto_rt_callback_add'
          , 'driver_gross_rt_callback_add'
          , 'task_switch_callback_add'
          , 'state_error_callback_add'
          , 'pm_stack_peak_callback_add'
          , 'checkpoint_callback_add'
          , 'pm_runtime_callback_add'
          , 'zgt_correction_callback_add'
          , 'zgt_error_callback_add'
          , 'runnable_overhead_callback_add'
          , 'reset'
          , 'version']


lock = threading.Lock()
logger = logging.getLogger('MotionWise.pm_instrument.interface')
hosts = { 1: pmcalc.Host(3, 'APH')
        , 2: pmcalc.Host(8, 'SSH')
        , 3: pmcalc.Host(8, 'SRH')}


def version():
    batch = max([ trace.__version__
                , pmcalc.__version__
                , constants.__version__
                , callback.__version__
                , __version__])
    return '0.0.{}'.format(batch)


def reset():
    hosts[1] = pmcalc.Host(3, 'APH')
    hosts[2] = pmcalc.Host(8, 'SSH')
    hosts[3] = pmcalc.Host(8, 'SRH')


def receive_event(event_data):
    """
    @brief Receives a logging/tracing message and passes its on to the 
           instrumentation module 
    
    @param event_data: Next event of the trace stream. Can be in raw format as 
           provided by the RA lib or a dictionary. In the case of a dictionary 
           following fields are required: count, core, data, swc, zgt, host, 
           type
    """
    with lock:
        event = None
        if isinstance(event_data, dict):
            event = trace.DictTrace (event_data)
        else:
            event = trace.RawTrace (event_data)
        try:    
            hosts[event.host].process(event)
        except KeyError: 
            logger.exception(traceback.format_exc())
            logger.warning("wrong host ID received: {}".format(event.host))


def receive_event_callback_add(fun):
    """
    @brief Registers a callback function. Callback is triggered every time
           an event is received.
    
    @param fun: Unary function accepting a dictionary as argument. The 
                dictionary has the following fields: count, core, data
                swc, zgt, host, type
    """
    callback.attach('event_received_callback_fun', fun)


def task_map_callback_add(fun):
    """
    @brief Registers a callback function. Callback is triggered every time
           a logging frame is received which contains task ID to name mapping.
    
    @param fun: Unary function accepting a dictionary as argument. The 
                dictionary has the following fields: host, mapping
    """
    callback.attach('task_id_name_callback_fun', fun)
    
    
def sequence_error_callback_add(fun):
    callback.attach('sequence_error_callback_fun', fun)
 
 
def state_error_callback_add(fun):
    """
    @brief Registers a callback function. Callback is triggered every time 
           a tracing state error is detected. 
           
    @param fun: Unary function accepting a dictionary as argument. The 
                dictionary has the following fields: host, zgt, type, state
                event    
    """
    callback.attach('state_error_callback_fun', fun)
   
    
def zgt_error_callback_add(fun):
    callback.attach('zgt_error_callback_fun', fun)


def interrupt_callback_add(fun):
    callback.attach('interrupt_callback_fun', fun)
	

def runnable_activation_callback_add(fun):
    callback.attach('rnbl_activation_callback_fun', fun)
    
    
def runnable_netto_rt_callback_add(fun):
    callback.attach('rnbl_netto_rt_callback_fun', fun)

    
def runnable_gross_rt_callback_add(fun):
    callback.attach('rnbl_gross_rt_callback_fun', fun)
    
 
def runnable_overhead_callback_add(fun):
    callback.attach('rnbl_overhead_callback_fun', fun)

    
def driver_activation_callback_add(fun):
    callback.attach('driver_activation_callback_fun', fun)
    
    
def driver_netto_rt_callback_add(fun):
    callback.attach('driver_netto_rt_callback_fun', fun)

    
def driver_gross_rt_callback_add(fun):
    callback.attach('driver_gross_rt_callback_fun', fun)
    
    
def task_switch_callback_add(fun):
    callback.attach('task_switch_callback_fun', fun)


def task_activation_callback_add(fun):
    callback.attach('task_activation_callback_fun', fun)


def task_netto_rt_callback_add(fun):
    callback.attach('task_netto_rt_callback_fun', fun)


def task_gross_rt_callback_add(fun):
    callback.attach('task_gross_rt_callback_fun', fun)
	

def pm_stack_peak_callback_add(fun):
    callback.attach('pm_stack_peak_callback_fun', fun)
    
    
def pm_heap_callback_add(fun):
    callback.attach('pm_heap_callback_fun', fun)
	

def pm_runtime_callback_add(fun):
    callback.attach('pm_runtime_callback_fun', fun)
  
  
def zgt_correction_callback_add(fun):
    callback.attach('zgt_correction_callback_fun', fun)
    
    
def checkpoint_callback_add(fun):
    callback.attach('checkpoint_callback_fun', fun)
  
  
def state_changed_callback_add(fun):
    callback.attach('state_changed_callback_fun', fun)
    
