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

import math
import logging
import callback
from constants import EVENT_MAP
from abc import ABCMeta, abstractmethod


STATE_INIT = 0
STATE_RUNNING = 1
STATE_PREEMPTED = 2
STATE_DELAYED = 3
logger = logging.getLogger('MotionWise.pm_instrument.pmcalc')


class Host(object):
    
    def __init__(self, number_of_cores, name):
        self._cores = [Core(i, self) for i in xrange(0, number_of_cores)]
        self._name = name
        self._init_sequence_buffer()
        self._init_zgt_reorder_buffer()
        self._last_time_stamp = None
        self._host_task_id_name_map = {}
        self._max_zgt = 0
        self._zgt_correction = 0
        self._tm_current_cnt = 0
        self._tm_expected_cnt = 0
    
    def process(self, trace_event_in):
        if trace_event_in.is_log: 
            try: 
                if 'task_id_name' == EVENT_MAP[trace_event_in.type]:
                    self._task_name_id_mapping (trace_event_in)
                    trace_event_in.trigger_callback()
            except AttributeError:
                pass
            # don't further process log messages since they have a different
            # sequence counter
            return 
        
        trace_event = self._add_to_sequence_buffer(trace_event_in)
        if trace_event is None: 
            # buffer is not full yet
            return
        
        if trace_event.time == 0xFFFFFFFFFFFF:
            # invalid time stamp detected
            callback.invoke('zgt_error_callback_fun', 
                {'host': self._name
                ,'zgt': trace_event.time
                ,'info': 'invalid ZGT received'})
            logger.warning("invalid ZGT received")
            for c in self._cores: c.reset()
            return
        
        if EVENT_MAP[trace_event.type] == 'zgt_correction':
            # ZGT correction event is not added to ZGT reorder buffer 
            self._zgt_correction = trace_event.zgt_corr_val
            logger.debug("ZGT correction on {}: {}"
                        .format(self._name, self._zgt_correction))
            return
        
        trace_event.time -= self._zgt_correction        
        trace_event = self._add_to_zgt_reorder_buffer(trace_event) 
        if trace_event is None: return 
        
        if self._max_zgt > 0: 
            # check event stream for ZGT jumps
            td = abs(trace_event.time - self._max_zgt)
            if td > 1000000:
                callback.invoke('zgt_error_callback_fun', 
                    {'host': self._name
                    ,'zgt': trace_event.time
                    ,'info': 'ZGT jump'})
                for c in self._cores: c.reset()

        trace_event.trigger_callback()
        self._max_zgt = max(self._max_zgt, trace_event.time)
        if trace_event.sequence_gap > 0:
            self._sequence_error(trace_event.sequence_gap, trace_event.time)
            return
        
        core = self._cores[trace_event.core]
        fun = getattr(core, EVENT_MAP[trace_event.type])
        fun(**{'trace': trace_event, 'time': trace_event.time})

    def _init_sequence_buffer(self):
        self._sequence_cnt_buffer_max = 20
        self._sequence_cnt_ptr = None
        self._sequence_cnt_buffer_size = 0
        self._sequence_cnt_buffer = [None] * 256
        self._sequence_cnt_gap = 0
    # end_def _reinit_sequence_buffer
    
    def _add_to_sequence_buffer(self, trace_event):
        """
        @brief Adds a trace event to a buffer in order to detect gaps in the 
               sequence counter. 
        
        Every trace event comes with a sequence number. These numbers are not
        always in increasing order. Hence it is necessary to buffer events to 
        detect gaps in the counter.
        
        @param trace_event: Trace event to be added to the buffer. 
        @return: Returns the oldest trace event in the buffer or None if the 
                 buffer is not full. The returned trace events have a field 
                 'sequence_gap' indicating the number of lost events since the 
                 last event has been received. If the gap is 0 no events have 
                 been lost. 
        """
        out = None

        if self._sequence_cnt_ptr is None:
            self._sequence_cnt_ptr = trace_event.seq
        
        # write new trace_event event to buffer
        self._sequence_cnt_buffer[trace_event.seq] = trace_event
        
        if self._sequence_cnt_buffer_size < self._sequence_cnt_buffer_max:
            # initialization phase
            self._sequence_cnt_buffer_size += 1
        else:
            # running phase -> check for gaps
            out = self._sequence_cnt_buffer[self._sequence_cnt_ptr]
            self._sequence_cnt_buffer[self._sequence_cnt_ptr] = None

            if out is not None: 
                out.sequence_gap = self._sequence_cnt_gap
                self._sequence_cnt_gap = 0  
            else:
                self._sequence_cnt_gap += 1
            # end_if
                
            self._sequence_cnt_ptr = (self._sequence_cnt_ptr + 1) % 256
        return out
    # end_def _check_frame_seq

    def _init_zgt_reorder_buffer(self):
        self._zgt_buffer = [None] * 300
    
    def _add_to_zgt_reorder_buffer(self, trace_event):
        """
        @brief Adds the trace event to a buffer in which entries are ordered
               according to their time stamp from new to old.
        
        The reorder buffer is used to guarantee that the events are processed
        in monotonically increasing order w.r.p to their time stamps. 
                  
        @param trace_event: Trace event to be added to the reorder buffer
        @return: If the buffer is full and a new element is added the last 
                 element is removed from the buffer and returned. Otherwise 
                 None is returned.
        """
        try:
            idx = (i for i, v in enumerate(self._zgt_buffer) 
                   if not v or trace_event.time >= v.time).next()
        except StopIteration: 
            idx = 1
            self._init_zgt_reorder_buffer()
            callback.invoke('zgt_error_callback_fun', 
                {'host': self._name
                ,'zgt': trace_event.time
                ,'info': 'big time gap'})
            for c in self._cores: c.reset()
            logger.debug("for {} tried to add non increasing time stamp "
                         "to zgt reorder buffer {}"
                         .format(self._name, trace_event.time))
            
        self._zgt_buffer.insert(idx, trace_event)    
        return self._zgt_buffer.pop ()
    # end_def _add_to_zgt_reorder_buffer

    def _sequence_error(self, gap, current_time):
        self.reset()
        callback.invoke('sequence_error_callback_fun', 
                {'host': self._name, 'missing': gap
                , 'zgt': current_time})

    def _task_name_id_mapping (self, trace):
        """
        @brief Parses the provided logging message in order to get the mapping
               between the task IDs and names.
               
        @param logging_msg: logging message containing task ID to name mapping  
        """
        msg = trace.data.split('|')
        if msg[0].endswith("PRE"):
            self._tm_expected_cnt = int(msg[-1])
            self._tm_current_cnt = 0
            return
        
        if trace.data[7] == ' ':
            msg[0] = msg[0].split(' ')[-1]
        else:
            msg = msg[1:]
        for i in xrange(1,len(msg),2):
            self._tm_current_cnt += 1
            callback.invoke('task_id_name_callback_fun', 
                {'host': self._name, 
                 'task_name': msg[i], 
                 'task_id': int(msg[i-1]), 
                 'msg_counter': self._tm_current_cnt,
                 'msg_expected': self._tm_expected_cnt})

    def reset(self):
        for c in self._cores: 
            c.reset()


class Core (object):
       
    def __init__(self, core_id, host):
        self._id = core_id
        self._host = host
        self._active_task = None
        self._active_interrupt = None
        self._entities = \
            { Runnable.TYPE: {'instances': {}, 'class': Runnable}
            , Task.TYPE: {'instances': {}, 'class': Task}
            , Driver.TYPE: {'instances': {}, 'class': Driver}
            , Interrupt.TYPE: {'instances': {}, 'class': Interrupt}}

    def _get_entity(self, entity_id, swc_id, _type):
        e = None
        try:
            e = self._entities[_type]['instances'][entity_id]
        except KeyError:
            e = self._entities[_type]['class'](entity_id, swc_id, self)
            self._entities[_type]['instances'][entity_id] = e
        return e
    
    def reset(self):
        self._active_task = None
        for v in self._entities.itervalues():
            for e in v['instances'].itervalues():
                e.reset()
    
    def start_runnable(self, trace, time, **args):
        r = self._get_entity(trace.rnbl_id, trace.swc_id, Runnable.TYPE)
        r.start(time)
    
    def stop_runnable(self, trace, time, **args):
        r = self._get_entity(trace.rnbl_id, trace.swc_id, Runnable.TYPE)
        r.stop(time)
    
    def task_switch(self, trace, time, **args):
        t_old = self._get_entity(trace.old_task_id, trace.swc_id, Task.TYPE)
        t_new = self._get_entity(trace.new_task_id, trace.swc_id, Task.TYPE)
        t_old.pause(time, t_new._id)
        t_new.resume(time)
        
    def interrupt_task(self, **args):
        pass
         
    def resume_task(self, **args):
        pass
         
    def interrupt_isr(self, **args):
        pass
         
    def resume_irs(self, **args):
        pass
         
    def start_driver(self, trace, time, **args):
        r = self._get_entity(trace.driver_id, trace.swc_id, Driver.TYPE)
        r.start(time)
         
    def stop_driver(self, trace, time, **args):
        r = self._get_entity(trace.driver_id, trace.swc_id, Driver.TYPE)
        r.stop(time)
     
    def state_change(self, **args):
        pass
    
    def checkpoint(self, trace, time, **args):
        callback.invoke('checkpoint_callback_fun', 
            {'host': self._host._name, 'id': trace.checkpt_id, 'zgt': time
            , 'data': trace.checkpt_data})

    def input_signal(self, **args):
        pass

    def pm_stack_peak(self, trace, time, **args):
        callback.invoke('pm_stack_peak_callback_fun', 
            {'host': self._host._name, 'id': trace.task_id, 'zgt': time
            , 'peak': trace.stackval, 'core': self._id})

    def pm_runtime(self, trace, time, **args):
        callback.invoke('pm_runtime_callback_fun',
            { 'host': self._host._name 
            , 'id': trace.rnbl_id
            , 'cnt': trace.cnt
            , 'zgt': time 
            , 'total_rt': trace.total
            , 'max_rt': trace.max
            , 'core': self._id})
    
    def zgt_correction(self, trace, time, **args):
        callback.invoke('zgt_correction_callback_fun',
            {'zgt': time, 'correction_value': trace.zgt_corr_val})

    def state_error(self, time, _type, old_state, event):
        callback.invoke('state_error_callback_fun',
            {'host': self._host._name, 'zgt': time, 'type': _type
            , 'state': old_state, 'event': event})
        self._host.reset()

    def pm_r_nettime(self, trace, time, **args):
        callback.invoke('rnbl_netto_rt_callback_fun',
            { 'host': self._host._name
            , 'id': trace.rnbl_id
            , 'swc': trace.swc_id
            , 'zgt': time
            , 'netto_rt': trace.total
            , 'core': self._id})

class Entity:
    __metaclass__ = ABCMeta
    
    @abstractmethod
    def start(self, time_stamp): 
        pass
    
    @abstractmethod
    def stop(self, time_stamp): 
        pass
    
    @abstractmethod
    def pause(self, time_stamp): 
        pass
    
    @abstractmethod
    def resume(self, time_stamp): 
        pass
    
    @abstractmethod
    def reset(self):
        pass
 
 
class Task (Entity):
    TYPE = 0
    
    def __init__ (self, entity_id, swc_id, core):
        self._id = entity_id
        self._swc_id = swc_id
        self._core = core
        self.reset()
    
    def start (self, time_stamp):
        raise NotImplementedError
    
    def stop (self, time_stamp):
        raise NotImplementedError
    
    def resume (self, time_stamp): 
        active_task = self._core._active_task
        if active_task is not None:
            info = 'resume_task_unexpected_task'
            self._core.state_error \
                (time_stamp, self.__class__.__name__, self._state, info)
            logger.debug("resume task unexpected task: expected {}, found {} "
                         "@{}".format(active_task._id, self._id, time_stamp))
            return
        
        if self._state in [STATE_DELAYED, STATE_RUNNING]:
            # invalid state transitions
            info = 'resume_task'
            self._core.state_error \
                (time_stamp, self.__class__.__name__, self._state, info)
            logger.debug("try to resume running or delayed task {}"
                         .format(self._id))
        elif self._state in [STATE_PREEMPTED, STATE_INIT]:
            if self._active_entities:
                self._active_entities[-1].resume(time_stamp)
            self._last_overhead_sync_event = (self, time_stamp)
            self._state = STATE_RUNNING
            self._time_resumed = time_stamp
            self._core._active_task = self
        
    def pause (self, time_stamp, next_task_id):
        active_task = self._core._active_task
        if active_task and active_task is not self:
            info = 'pause_task_unexpected_task'
            self._core.state_error \
                (time_stamp, self.__class__.__name__, self._state, info)
            logger.debug("pause task unexpected task: expected {}, found {}"
                         .format(active_task._id, self._id))
            return
    
        if self._state in [STATE_PREEMPTED, STATE_DELAYED]:
            # invalid state transitions
            info = 'pause_task'
            self._core.state_error \
                (time_stamp, self.__class__.__name__, self._state, info)
        elif self._state == STATE_INIT:
            pass # self transition after reset
        elif self._state == STATE_RUNNING:
            if self._active_entities:
                self._active_entities[-1].pause(time_stamp)
            if self._last_overhead_sync_event:
                # check if overhead has to be updated
                entity, old_ts = self._last_overhead_sync_event
                if entity != self:
                    # the entity corresponds to runnable
                    if entity._overhead:
                        entity._overhead.append(time_stamp - old_ts)
                        overhead = math.ceil(sum(entity._overhead))
                        callback.invoke('rnbl_overhead_callback_fun', 
                            {'host': entity._core._host._name, 
                             'id': entity._id, 
                             'swc': entity._swc_id, 
                             'zgt': time_stamp, 
                             'overhead': overhead,
                             'task': self._id,
                             'core': entity._core._id})
                    else:
                        # there is no pre-runnable overhead stored. This 
                        # can only happen after an error or at the start of 
                        # a measurement session 
                        pass
                    entity._overhead = []
            self._core._active_task = None
            self._state = STATE_PREEMPTED
            callback.invoke('task_switch_callback_fun',
                   { 'host': self._core._host._name
                   , 'id': self._id
                   , 'swc': self._swc_id
                   , 'zgt': time_stamp 
                   , 'rt': time_stamp - self._time_resumed
                   , 'core': self._core._id
                   , 'next_task': next_task_id})  
             
    def reset(self):
        self._time_resumed = None
        self._active_entities = []
        self._last_overhead_sync_event = None
        self._state = STATE_INIT


class Runnable (Entity):
    TYPE = 1

    def __init__(self, entity_id, swc_id, core):
        self._id = entity_id
        self._swc_id = swc_id
        self._core = core
        self._task = None
        self.reset()
    
    def start(self, time_stamp):
        """
        @brief Receives a runnable-start event and updates the state machine
               accordingly. 
        
        @param time_stamp: Time at which the runnable-start event is received. 
        """   
        active_task = self._core._active_task
        if self._task is None and active_task is not None: 
            self._task = active_task
        
        if active_task is not None and self._task != active_task:
            # runnables always have to run in the context of the same task
            info = 'runnable_task_context'
            self._core.state_error \
                (time_stamp, self.__class__.__name__, self._state, info)
                
        if active_task is None:
            # netto runtime can't be computed since it is not known to
            # which task this driver belongs
            self._no_task_at_start = False
        
        if self._state in [STATE_INIT, STATE_DELAYED]:
            if self._task:
                if self._task._active_entities:
                    self._task._active_entities[-1].pause(time_stamp)
                self._task._active_entities.append(self)

            if self._last_start is not None:
                if self._task and self._task._last_overhead_sync_event:
                    # compute pre-runnbale overhead
                    entity, old_ts = self._task._last_overhead_sync_event
                    dt = time_stamp - old_ts
                    if entity != self._task and entity._overhead:
                        # no task switch event between stop event of last
                        # runnable and start event of this runnable. Over-
                        # head has to be split. 
                        dt = dt / 2.0
                        entity._overhead.append(dt)
                        overhead = math.ceil(sum(entity._overhead))
                        callback.invoke('rnbl_overhead_callback_fun', 
                            {'host': entity._core._host._name, 
                             'id': entity._id, 
                             'swc': entity._swc_id, 
                             'zgt': time_stamp, 
                             'overhead': overhead,
                             'task': entity._task._id, 
                             'core': entity._core._id})
                        entity._overhead = []
                    self._overhead.append(dt)
                period = time_stamp - self._last_start
                callback.invoke('rnbl_activation_callback_fun', 
                     { 'host': self._core._host._name
                     , 'id': self._id
                     , 'swc': self._swc_id
                     , 'zgt': time_stamp 
                     , 'periodic_activation': period
                     , 'core': self._core._id})
                
            self._last_start = time_stamp
            self._resumed.append(time_stamp)
            self._state = STATE_RUNNING
        elif self._state in [STATE_RUNNING, STATE_PREEMPTED]:
            # invalid state transition
            info = 'start_runnable'
            self._core.state_error \
                (time_stamp, self.__class__.__name__, self._state, info)

    def pause(self, time_stamp):
        """
        @brief Receives a runnable-pause event and updates the state machine
               accordingly. 
        
        @param time_stamp: Time at which the runnable-pause event is received. 
        """        
        if self._state in [STATE_INIT, STATE_DELAYED, STATE_PREEMPTED]:
            info = 'pause_runnable'
            self._core.state_error \
                (time_stamp, self.__class__.__name__, self._state, info)
        elif self._state == STATE_RUNNING:
            self._preempted.append(time_stamp)
            self._state = STATE_PREEMPTED

    def resume(self, time_stamp):
        """
        @brief Receives a runnable-resume event and updates the state machine
               accordingly. 
        
        @param time_stamp: Time at which the runnable-resume event is received. 
        """  
        if self._state in [STATE_INIT, STATE_RUNNING, STATE_DELAYED]:
            if False == self._no_task_at_start:
                info = 'resume_runnable'
                self._core.state_error \
                    (time_stamp, self.__class__.__name__, self._state, info)
            else:
                #special case if task to which runnable belongs was not known
                #at start time
                pass
        elif self._state == STATE_PREEMPTED:
            self._resumed.append(time_stamp)
            self._state = STATE_RUNNING
            
    def stop(self, time_stamp):
        """
        @brief Receives a runnable-stop event and updates the state machine
               accordingly. 
        
        @param time_stamp: Time at which the runnable-stop event is received. 
        """ 
        if self._state == STATE_INIT:
            pass # self transition: can happen after reset() is called
        elif self._state == STATE_RUNNING:
            active_task = self._core._active_task
            if (self._task is not None) and (not self._no_task_at_start 
                and self._task != active_task):
                # runnable always has to run in the context of the same task
                info = 'stop_runnable_task_context'
                self._core.state_error \
                    (time_stamp, self.__class__.__name__, self._state, info)
                return
            
            if self._task:
                self._task._last_overhead_sync_event = (self, time_stamp)
                if self._task._active_entities:
                    if self._task._active_entities.pop() is not self:
                        # unexpected runnable detected
                        info = 'stop_runnable_unexpected_runnable'
                        self._core.state_error(time_stamp, 
                            self.__class__.__name__, self._state, info)
                        return
                    elif self._task._active_entities:
                        self._task._active_entities[-1].resume(time_stamp)

            self._preempted.append(time_stamp)
            net_rt = [a-b for (a,b) in zip(self._preempted, self._resumed)]
            callback.invoke('rnbl_gross_rt_callback_fun',
                { 'host': self._core._host._name
                , 'id': self._id
                , 'swc': self._swc_id
                , 'zgt': time_stamp 
                , 'gross_rt': time_stamp - self._last_start
                , 'core': self._core._id})
            
            if False == self._no_task_at_start:
                callback.invoke('rnbl_netto_rt_callback_fun',
                    { 'host': self._core._host._name
                    , 'id': self._id
                    , 'swc': self._swc_id
                    , 'zgt': time_stamp 
                    , 'netto_rt': sum(net_rt)
                    , 'core': self._core._id})
            self._preempted = []
            self._resumed = []
            self._state = STATE_DELAYED
             
        elif self._state in [STATE_DELAYED, STATE_PREEMPTED]:
            info = 'stop_runnable'
            self._core.state_error \
                (time_stamp, self.__class__.__name__, self._state, info)

    def reset(self):
        self._state = STATE_INIT
        self._last_start = None
        self._preempted = []
        self._resumed = []
        self._overhead = []
        self._no_task_at_start = False


class Driver (Entity):
    TYPE = 2
    
    def __init__ (self, entity_id, swc_id, core):
        self._id = entity_id
        self._swc_id = swc_id
        self._core = core
        self._task = None
        self.reset()

    def start (self, time_stamp):
        active_task = self._core._active_task
        if self._task is None and active_task is not None: 
            self._task = active_task
            
        if active_task is not None and self._task != active_task:
            # drivers always have to run in the context of the same task
            info = 'driver_task_context_start_event'
            self._core.state_error \
                (time_stamp, self.__class__.__name__, self._state, info)
         
        if active_task is None:
            # netto runtime can't be computed since it is not known to
            # which task this driver belongs
            self._no_task_at_start = True
                
        if self._state in [STATE_INIT, STATE_DELAYED]:
            if self._task:
                if self._task._active_entities:
                    self._task._active_entities[-1].pause(time_stamp)
                self._task._active_entities.append(self)

            if self._last_start is not None:
                period = time_stamp - self._last_start
                callback.invoke('driver_activation_callback_fun', 
                     { 'host': self._core._host._name
                     , 'id': self._id
                     , 'swc': self._swc_id
                     , 'zgt': time_stamp 
                     , 'periodic_activation': period
                     , 'core': self._core._id})
            
            self._last_start = time_stamp
            self._resumed.append(time_stamp)
            self._state = STATE_RUNNING
        elif self._state in [STATE_RUNNING, STATE_PREEMPTED]:
            # invalid state transition
            info = 'start_driver'
            self._core.state_error \
                (time_stamp, self.__class__.__name__, self._state, info)
    
    def pause (self, time_stamp):
        """
        @brief Receives a driver-pause event and updates the state machine
               accordingly. 
        
        @param time_stamp: Time at which the driver-pause event is received. 
        """        
        if self._state in [STATE_INIT, STATE_DELAYED, STATE_PREEMPTED]:
            info = 'pause_driver'
            self._core.state_error \
                (time_stamp, self.__class__.__name__, self._state, info)
        elif self._state == STATE_RUNNING:
            self._preempted.append(time_stamp)
            self._state = STATE_PREEMPTED

    def resume (self, time_stamp): 
        """
        @brief Receives a driver-resume event and updates the state machine
               accordingly. 
        
        @param time_stamp: Time at which the driver-resume event is received. 
        """  
        if self._state in [STATE_INIT, STATE_RUNNING, STATE_DELAYED]:
            if False == self._no_task_at_start:
                info = 'resume_driver'
                self._core.state_error \
                    (time_stamp, self.__class__.__name__, self._state, info)
            else:
                #special case if task to which runnable belongs was not known
                #at start time
                pass
        elif self._state == STATE_PREEMPTED:
            self._resumed.append(time_stamp)
            self._state = STATE_RUNNING
    
    def stop (self, time_stamp):
        """
        @brief Receives a driver-stop event and updates the state machine
               accordingly. 
        
        @param time_stamp: Time at which the driver-stop event is received. 
        """ 
        if self._state == STATE_INIT:
            pass # self transition: can happen after reset() is called
        elif self._state == STATE_RUNNING:
            active_task = self._core._active_task
            if (self._task is not None) and (not self._no_task_at_start 
                and self._task != active_task):
                # runnable always has to run in the context of the same task
                info = 'driver_task_context_stop_events'
                self._core.state_error \
                    (time_stamp, self.__class__.__name__, self._state, info)
                return
            
            # valid state transition 
            if self._task:
                if self._task._active_entities.pop() is not self:
                    # unexpected runnable detected
                    info = 'unexpected_driver_stop_event'
                    self._core.state_error \
                        (time_stamp, self.__class__.__name__, self._state, info)
                    return 
                elif self._task._active_entities:
                    self._task._active_entities[-1].resume(time_stamp)
                                
            self._preempted.append(time_stamp)
            net_rt = [a-b for (a,b) in zip(self._preempted, self._resumed)]
            callback.invoke('driver_gross_rt_callback_fun',
                { 'host': self._core._host._name
                , 'id': self._id
                , 'swc': self._swc_id
                , 'zgt': time_stamp 
                , 'gross_rt': time_stamp - self._last_start
                , 'core': self._core._id})
    
            if False == self._no_task_at_start:
                callback.invoke('driver_netto_rt_callback_fun',
                    { 'host': self._core._host._name
                    , 'id': self._id
                    , 'swc': self._swc_id
                    , 'zgt': time_stamp 
                    , 'netto_rt': sum(net_rt)
                    , 'core': self._core._id})
    
            self._preempted = []
            self._resumed = []
            self._no_task_at_start = False
            self._state = STATE_DELAYED
             
        elif self._state in [STATE_DELAYED, STATE_PREEMPTED]:
            info = 'stop_driver'
            self._core.state_error \
                (time_stamp, self.__class__.__name__, self._state, info)
    
    def reset(self):
        self._state = STATE_INIT
        self._last_start = None
        self._no_task_at_start = False
        self._overhead = []
        self._preempted = []
        self._resumed = []


class Interrupt (Entity):
    TYPE = 3
 
    def __init__ (self, entity_id, swc_id, core_id):
        pass

    def start (self, time_stamp):
        pass
    
    def stop (self, time_stamp):
        pass
    
    def pause (self, time_stamp):
        pass

    def resume (self, time_stamp): 
        pass
    
    def reset(self):
        pass
 
 
__version__ = "$Revision: 80204 $".split()[1]   


if __name__ == '__main__':
    pass
