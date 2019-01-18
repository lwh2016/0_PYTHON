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
#    03-Oct-2017 (SKW) [IECU-244] Os_ECU*.htm is not created with a new SIP
#
# --

from __future__ import division

import RA
import csv
import re
import sys
import time
import logging
import threading
import pm_instrument
import file_parser as FP


logger = logging.getLogger('MotionWise.pm_measurement')

DELIMITER = ','
IDLE_TASK_PATTERN = {'APH': 'Task_Idle', 'SSH': 'tIdleTask', 'SRH': '#@!$'} 
HOSTS = {'APH': {'name': 'ApplicationHost', 'id': 1, 'cores': 3}
        ,'SRH': {'name': 'SurroundHost', 'id': 3, 'cores': 8}
        ,'SSH': {'name': 'SensorSystemHost', 'id': 2, 'cores': 8}}


def _div(dividend, divisor, op='int'):
    out = ''
    try: 
        dividend = float(dividend)
        divisor = float(divisor)
        
        if op == 'int':
            out = "{}".format(int(dividend // divisor))
        else:
            out = '{0:2.6f}'.format((dividend / divisor) * 100)
    except:
        pass
    return out


def _overrides(interface_class):
    def overrider(method):
        assert(method.__name__ in dir(interface_class))
        return method
    return overrider


class Sampler(object):
    
    def __init__(self, host_str, callback_fun, sample_rate = 1000000):
        self._host = HOSTS[host_str]['id']
        self._last_update_time = None
        self._sample_rate = sample_rate
        self._callback_fun = callback_fun
        pm_instrument.receive_event_callback_add(self._event_received_cb)
        
    def _event_received_cb(self, host, zgt, **signal):
        if host != self._host: return
        if self._last_update_time is None:
            self._last_update_time = zgt
        dt = zgt - self._last_update_time
        if dt >= self._sample_rate:
            self._callback_fun(self._last_update_time, dt)
            self._last_update_time = zgt


class TraceListener(object):
    
    def __init__(self, host_short, file_handler=sys.stdout):
        self._lock = threading.Lock()
        self._first_event_received = False
        self._file_handler = file_handler
        self._host = HOSTS[host_short]['id']
        self._file_handler.write("#HEADER ")    
        self._file_handler.write(DELIMITER.join(
            [ 'zgt', 'count', 'host', 'core', 'type'
            , 'swc', 'rid', 'data']))
        self._file_handler.write("\n")
        self.pattern = '{{zgt}}{d}{{count}}{d}{{host}}{d}{{core}}{d}{{type}}'\
                       '{d}{{swc}}{d}{{rid}}{d}{{data}}\n'.format(d=DELIMITER)
        pm_instrument.receive_event_callback_add(self._event_received_cb)

    def _event_received_cb(self, host, data, **signal):
        if host != self._host: 
            return
        with self._lock:
            if not self._file_handler.closed:
                if not type(data) is str:
                    data = '0x{:x}'.format(data)
                string = (self.pattern.format(host=host, data=data, **signal))
                self._file_handler.write(string)

    def close(self):
        with self._lock:
            if sys.stdout != self._file_handler:
                self._file_handler.close()


class SwcListener(object):
    
    def __init__(self, csv_file):
        pass


class RunnableListenerSummary(object):
    
    def __init__( self, host_str, ra, budget = {}, periods = {}
                , sw_layers = {}, file_handler=sys.stdout):
        
        self._ra = ra
        self._host_str = host_str
        self._file_handler = file_handler
        self._runnable_measurements = {}
        self._budget = budget
        self._periods = periods
        self._driver_name_map = {}
        self._sw_layers = sw_layers
        pm_instrument.runnable_netto_rt_callback_add(self._rnbl_netto_rt_cb)
        pm_instrument.runnable_gross_rt_callback_add(self._rnbl_gross_rt_cb)
        pm_instrument.runnable_activation_callback_add(self._rnbl_period_cb)
        pm_instrument.runnable_overhead_callback_add(self._rnbl_overhead_cb)

    def _get_runnable(self, _id):
        try: 
            self._runnable_measurements[_id];
        except KeyError:
            self._runnable_measurements[_id] = \
                { 'swc': '', 'core': ''
                , 'period': {'cnt':0, 'max': '', 'min': '', 'sum': ''}
                , 'netto': {'cnt':0, 'max': '', 'min': '', 'sum': ''}
                , 'gross': {'cnt':0, 'max': '', 'min': '', 'sum': ''}
                , 'overhead': {'cnt':0, 'max': '', 'min': '', 'sum': ''}}
        return self._runnable_measurements[_id] 
        
    def _rnbl_period_cb(self, host, periodic_activation, **signal):
        if host != self._host_str: return
        meas = self._get_runnable(signal['id'])['period']
        if 0 == meas['cnt']:
            meas['max'] = periodic_activation
            meas['min'] = periodic_activation
            meas['sum'] = periodic_activation
        else:
            meas['sum'] += periodic_activation
            meas['max'] = max(periodic_activation, meas['max'])
            meas['min'] = min(periodic_activation, meas['min'])
        meas['cnt'] += 1
        name = self._ra.get_runnable_name_of_runnable_id(signal['id'])
        period = float(self._periods.get(name, periodic_activation))
        if (periodic_activation / period) > 2:
            logger.info("time between periodic activation of runnable {} is "
                        "greater than two times the scheduled period @{zgt}"
                        .format(name, **signal))

    def _rnbl_gross_rt_cb(self, host, core, swc, gross_rt, **signal):
        if host != self._host_str: return
        meas = self._get_runnable(signal['id'])['gross']
        if 0 == meas['cnt']:
            meas['max'] = gross_rt
            meas['min'] = gross_rt
            meas['sum'] = gross_rt
            self._get_runnable(signal['id'])['swc'] = swc
            self._get_runnable(signal['id'])['core'] = core
        else:
            meas['sum'] += gross_rt
            meas['max'] = max(gross_rt, meas['max'])
            meas['min'] = min(gross_rt, meas['min'])
        meas['cnt'] += 1

    def _rnbl_netto_rt_cb(self, host, netto_rt, **signal):
        if host != self._host_str: return
        meas = self._get_runnable(signal['id'])['netto']
        if 0 == meas['cnt']:
            meas['max'] = netto_rt
            meas['min'] = netto_rt
            meas['sum'] = netto_rt
        else:
            meas['sum'] += netto_rt
            meas['max'] = max(netto_rt, meas['max'])
            meas['min'] = min(netto_rt, meas['min'])
        meas['cnt'] += 1
        
        name = self._ra.get_runnable_name_of_runnable_id(signal['id'])
        rt_diff = int(netto_rt - self._budget.get(name,netto_rt))
        if rt_diff > 0:
            logger.info('runtime of runnable {} exceeded the budget by '
                        '{}us @{zgt}'.format(name, rt_diff, **signal))
        
    def _rnbl_overhead_cb(self, host, overhead, **signal):
        if host != self._host_str: return
        meas = self._get_runnable(signal['id'])['overhead']
        if 0 == meas['cnt']:
            meas['max'] = overhead
            meas['min'] = overhead
            meas['sum'] = overhead
        else:
            meas['sum'] += overhead
            meas['max'] = max(overhead, meas['max'])
            meas['min'] = min(overhead, meas['min'])
        meas['cnt'] += 1        
        
    def _pm_runtime_cb(self, host, max_rt, total_rt, **signal):
        if host != self._host_str: return
        meas = self._get_runnable(signal['id'])['netto']
        if 0 == meas['cnt']:
            meas['max'] = max_rt
            meas['sum'] = total_rt
        else:
            meas['sum'] += total_rt
            meas['max'] = max(max_rt, meas['max'])
        meas['cnt'] += 1

    def _meas_to_dict(self, r, m):
        d = {}
        d['entity'] = 'RUNNABLE'
        d['core'] = m['core']
        d['swc'] = self._ra.get_swc_name_of_swc_id(m['swc'])
        d['name'] = self._ra.get_runnable_name_of_runnable_id(r) 
        if d['name'] == None: d['name'] = '{}'.format(r) 
        budget = self._budget.get(d['name'], '')  
        d['avg_netto'] = _div(m['netto']['sum'], m['netto']['cnt'])
        d['avg_gross'] = _div(m['gross']['sum'], m['gross']['cnt'])
        d['avg_period'] = _div(m['period']['sum'], m['period']['cnt'])
        d['avg_overhead'] = _div(m['overhead']['sum'], m['overhead']['cnt'])
        d['min_netto'] = m['netto']['min']
        d['max_netto'] = m['netto']['max']
        d['cnt_netto'] = m['netto']['cnt']
        d['cnt_cpu'] = ''
        d['min_cpu'] = _div(m['netto']['min'], d['avg_period'], op='float')
        d['avg_cpu'] = _div(d['avg_netto'], d['avg_period'], op='float')
        d['max_cpu'] = _div(m['netto']['max'], d['avg_period'], op='float')
        d['min_budget'] = _div(m['netto']['min'], budget, op='float')
        d['avg_budget'] = _div(d['avg_netto'], budget, op='float')
        d['max_budget'] = _div(m['netto']['max'], budget, op='float')
        d['cnt_gross'] = m['gross']['cnt']
        d['min_gross'] = m['gross']['min']
        d['max_gross'] = m['gross']['max']
        d['cnt_period'] = m['period']['cnt']
        d['min_period'] = m['period']['min']
        d['max_period'] = m['period']['max']
        d['cnt_overhead'] = m['overhead']['cnt']
        d['min_overhead'] = m['overhead']['min']
        d['max_overhead'] = m['overhead']['max']
        d['cnt_stack'] = ''
        d['max_stack'] = ''
        
        try: 
            d['SW_layer'] = self._sw_layers[d['name']]['SW_layer']
        except KeyError:
            d['SW_layer'] = ''
            
        return d

    def _write_header(self):
        self._file_handler.write("#HEADER ")
        self._file_handler.write(DELIMITER.join(
            [ 'core', 'swc', 'runnable', 'netto_CPU_time_cnt'
            , 'netto_CPU_time_min[us]', 'netto_CPU_time_avg[us]'
            , 'netto_CPU_time_max[us]', 'gross_CPU_time_cnt'
            , 'gross_CPU_time_min[us]', 'gross_CPU_time_avg[us]'
            , 'gross_CPU_time_max[us]', 'cyclic_activation_cnt'
            , 'cyclic_activation_min[us]', 'cyclic_activation_avg[us]'
            , 'cyclic_activation_max[us]', 'netto_CPU_usage_min[%]'
            , 'netto_CPU_usage_avg[%]', 'netto_CPU_usage_max[%]'
            , 'netto_budget_usage_min[%]', 'netto_budget_usage_avg[%]'
            , 'netto_budget_usage_max[%]', 'overhead_time_cnt'
            , 'overhead_time_min[us]', 'overhead_time_avg[us]'
            , 'overhead_time_max[us]', 'SW_layer'
            ]))
        self._file_handler.write("\n")        

    def write(self):
        self._write_header()
        func = lambda y: y[1]['core']
        for (k, v) in sorted(self._runnable_measurements.items(), key=func): 
            if v['swc'] is not None:
                self._file_handler.write(DELIMITER.join(
                    [ '{core}', '{swc}', '{name}', '{cnt_netto}'
                    , '{min_netto}', '{avg_netto}', '{max_netto}'
                    , '{cnt_gross}', '{min_gross}', '{avg_gross}'
                    , '{max_gross}', '{cnt_period}', '{min_period}'
                    , '{avg_period}', '{max_period}', '{min_cpu}'
                    , '{avg_cpu}', '{max_cpu}', '{min_budget}'
                    , '{avg_budget}', '{max_budget}', '{cnt_overhead}'
                    , '{min_overhead}', '{avg_overhead}', '{max_overhead}'
                    , '{SW_layer}'])
                    .format(**self._meas_to_dict(k, v)))
                self._file_handler.write("\n")

    def close(self):
        if sys.stdout != self._file_handler:
            self._file_handler.close()


class RunnableListenerTrace(RunnableListenerSummary):
    
    def __init__( self, host_str, ra, budget = {}, periods = {}
                , sw_layers = {}, file_handler = sys.stdout):
        
        RunnableListenerSummary.__init__(self, host_str, ra, budget, 
                                         periods, sw_layers, file_handler)
        self._sampler = Sampler(host_str, self._update_measurement)
        self._write_header()

    def _update_measurement(self, zgt, dt):
        for r, m in self._runnable_measurements.iteritems():
            d = RunnableListenerSummary._meas_to_dict(self, r, m)  
            d['zgt'] = zgt 
            self._append_runnable(d)       
            m['period'] = {'cnt':0, 'max': '', 'min': '', 'sum': ''}
            m['netto'] = {'cnt':0, 'max': '', 'min': '', 'sum': ''}
            m['gross'] = {'cnt':0, 'max': '', 'min': '', 'sum': ''}

    def _append_runnable(self, data_dict):
        self._file_handler.write(DELIMITER.join(
            [ '{zgt}', '{core}', '{swc}', '{name}', '{cnt_netto}'
            , '{min_netto}', '{avg_netto}', '{max_netto}', '{cnt_gross}'
            , '{min_gross}', '{avg_gross}', '{max_gross}', '{cnt_period}'
            , '{min_period}', '{avg_period}', '{max_period}', '{min_cpu}'
            , '{avg_cpu}', '{max_cpu}', '{min_budget}', '{avg_budget}'
            , '{max_budget}', '{SW_layer}']).format(**data_dict))
        self._file_handler.write("\n")

    @_overrides(RunnableListenerSummary)
    def _write_header(self):
        self._file_handler.write("#HEADER ")
        self._file_handler.write(DELIMITER.join(
            [ 'zgt', 'core', 'swc', 'runnable', 'netto_CPU_time_cnt'
            , 'netto_CPU_time_min[us]', 'netto_CPU_time_avg[us]'
            , 'netto_CPU_time_max[us]', 'gross_CPU_time_cnt'
            , 'gross_CPU_time_min[us]', 'gross_CPU_time_avg[us]'
            , 'gross_CPU_time_max[us]', 'cyclic_activation_cnt'
            , 'cyclic_activation_min[us]', 'cyclic_activation_avg[us]'
            , 'cyclic_activation_max[us]', 'netto_CPU_usage_min[%]'
            , 'netto_CPU_usage_avg[%]', 'netto_CPU_usage_max[%]'
            , 'netto_budget_usage_min[%]', 'netto_budget_usage_avg[%]'
            , 'netto_budget_usage_max[%]', 'SW_layer'
            ]))
        self._file_handler.write("\n") 
        
    @_overrides(RunnableListenerSummary)
    def write(self):
        raise NotImplementedError


class TaskListenerSummary(object):

    def __init__(self, host_str, sw_layers = {}, file_handler=sys.stdout):
        self._host_str = host_str
        self._task_name_map = {}
        self._file_handler = file_handler
        self._aph_task_to_core_map = {}
        self._task_name_map = {}
        self._task_measurements = {}
        self._sw_layers = sw_layers
        self._error_cnt_sample = [0, 0, 0]
        self._sampler = Sampler(host_str, self._update_measurement)
        self._rate_range = 0.1 * self._sampler._sample_rate
        self._sample_cnt = 0
        
        pm_instrument.pm_stack_peak_callback_add(self._pm_stack_peak_cb)
        pm_instrument.task_map_callback_add(self._task_map_callback)
        pm_instrument.task_switch_callback_add(self._task_switch_callback)
        pm_instrument.state_error_callback_add(self._state_error_cb)
        pm_instrument.sequence_error_callback_add(self._sequence_error_cb)
        pm_instrument.zgt_error_callback_add(self._zgt_error_cb)
        pm_instrument.runnable_overhead_callback_add(self._rnbl_overhead_cb)
        for i in xrange(0, HOSTS[self._host_str]['cores']):
            self._task_name_map[0xFFFFFFFF+i] = \
                'non_traced_tasks_C{:02d}'.format(i)

    def _get_task(self, _id):
        try: 
            self._task_measurements[_id]
        except KeyError:
            self._task_measurements[_id] = \
                {'core': '', 'stack_cnt': 0, 'stack_peak': '',
                 'runtime': {'cnt':0, 'min':0, 'max':0, 'sum':0, 'sample':0},
                 'overhead': {'cnt':0, 'min':0, 'max':0, 'sum':0, 'sample':0}}
        return self._task_measurements[_id] 
   
    def _update_measurement(self, zgt, dt):
        # a measurement is considered valid iff no errors were detected
        # during the sampling period and the length of the period does not 
        # exceed the sampling rate by more than 10%. 
        rate_OK = abs(dt - self._sampler._sample_rate) <= self._rate_range
        error_OK = not sum(self._error_cnt_sample)
        self._error_cnt_sample = [0, 0, 0]
        self._sample_cnt += error_OK and rate_OK
        
        if not rate_OK:
            logger.debug("invalid sample rate {} @{}".format(dt, zgt))
        
        def update(meas):
            # update statistical values for given metric
            if meas['sample'] > 0:
                load = (meas['sample'] / float(dt))
                if meas['cnt'] > 0:
                    meas['min'] = min(meas['min'], load)
                    meas['max'] = max(meas['max'], load)
                    meas['sum'] += load
                else:
                    meas['min'] = load
                    meas['max'] = load
                    meas['sum'] = load
                meas['cnt'] += 1
        
        # for each known task updated the measurement
        for m in self._task_measurements.itervalues():
            if error_OK and rate_OK:
                update(m['runtime']) 
                update(m['overhead']) 
            m['runtime']['sample'] = 0
            m['overhead']['sample'] = 0 
    
    def _rnbl_overhead_cb(self, host, overhead, **signal):
        if host != self._host_str: return
        task = self._get_task(signal['task'])
        task['overhead']['sample'] += overhead
        
    def _task_switch_callback(self, host, core, rt, **signal):
        if host != self._host_str: return
        if signal['id'] == 0xFFFFFFFF:
            task = self._get_task(0xFFFFFFFF + core)
        else:
            task = self._get_task(signal['id'])
        task['runtime']['sample'] += rt
        task['core'] = core
    
    def _task_map_callback(self, host, task_id, task_name, **signal):
        if host != self._host_str: return
        self._task_name_map[task_id] = task_name

    def _pm_stack_peak_cb(self, host, peak, core, **signal):
        if host != self._host_str: return
        task = self._get_task(signal['id'])
        if 0 < task['stack_cnt']:
            task['stack_peak'] = max(task['stack_peak'], peak)
        else:
            task['stack_peak'] = peak 
        if not task['core']:
            if self._host_str == 'APH':
                # XXX ATTENTION: core information on APH is wrong
                core = self._aph_task_to_core_map.get(signal['id'],'')
            task['core'] = core
        task['stack_cnt'] += 1

    def _state_error_cb(self, host, **signal):
        if host != self._host_str: return
        self._error_cnt_sample[0] += 1
        
    def _sequence_error_cb(self, host, missing, **signal):
        if host != self._host_str: return
        self._error_cnt_sample[1] += missing

    def _zgt_error_cb(self, **signal):
        self._error_cnt_sample[2] += 1

    def _meas_to_dict(self, k, m):
        d = {}
        d['entity'] = 'TASK'
        d['core'] = m['core']
        d['name'] = '{}'.format(self._task_name_map.get(k, k))
        
        if m['runtime']['cnt'] == 0:
            d['cnt_cpu'] = 0
            d['min_cpu'] = ''
            d['avg_cpu'] = ''
            d['max_cpu'] = ''
        else:
            d['cnt_cpu'] = self._sample_cnt
            if self._sample_cnt != m['runtime']['cnt']:
                d['min_cpu'] = 0
            else:
                d['min_cpu'] = _div(m['runtime']['min'], 1, op='float')
            
            d['avg_cpu'] = _div(m['runtime']['sum'], d['cnt_cpu'], op='float')
            d['max_cpu'] = _div(m['runtime']['max'], 1, op='float')
        
        if m['overhead']['cnt'] == 0:
            d['cnt_ovh'] = 0
            d['min_ovh'] = ''
            d['avg_ovh'] = ''
            d['max_ovh'] = ''
        else:
            d['cnt_ovh'] = self._sample_cnt
            if self._sample_cnt != m['overhead']['cnt']:
                d['min_ovh'] = 0
            else:
                d['min_ovh'] = _div(m['overhead']['min'], 1, op='float')
            d['avg_ovh'] = _div(m['overhead']['sum'], d['cnt_ovh'], op='float')
            d['max_ovh'] = _div(m['overhead']['max'], 1, op='float')
        
        d['cnt_stack'] = m['stack_cnt']
        d['max_stack'] = m['stack_peak']
        
        try: 
            d['SW_layer'] = self._sw_layers[d['name']]['SW_layer']
        except KeyError:
            d['SW_layer'] = ''
        
        return d

    def _write_header(self):
        self._file_handler.write("#HEADER ")
        self._file_handler.write(DELIMITER.join(
            ['core', 'name', 'netto_CPU_usage_cnt', 'netto_CPU_usage_min[%]', 
             'netto_CPU_usage_avg[%]', 'netto_CPU_usage_max[%]', 
             'overhead_cnt', 'overhead_min[%]', 'overhead_avg[%]', 
             'overhead_max[%]', 'RAM_stack_usage_cnt', 
             'RAM_stack_usage_max[Byte]', 'SW_layer']))
        self._file_handler.write("\n")

    def load_aph_task_map(self, task_id_file, arxml_file):
        for k,v in FP.load_aph_task_map(task_id_file, arxml_file).iteritems():
            self._aph_task_to_core_map[k] = v['core']
            self._task_name_map[k] = v['name']

    def write(self):
        self._write_header()
        func = lambda y: y[1]['core']
        for (k, m) in sorted(self._task_measurements.items(), key=func):
            self._file_handler.write(DELIMITER.join(
                [ '{core}', '{name}', '{cnt_cpu}', '{min_cpu}'
                , '{avg_cpu}', '{max_cpu}', '{cnt_ovh}', '{min_ovh}'
                , '{avg_ovh}', '{max_ovh}', '{cnt_stack}','{max_stack}'
                , '{SW_layer}']).format(**self._meas_to_dict(k, m)))
            self._file_handler.write('\n')

    def close(self):
        if sys.stdout != self._file_handler:
            self._file_handler.close()


class TaskListenerTrace(TaskListenerSummary):
    
    def __init__(self, host_str, sw_layers = {}, file_handler=sys.stdout):
        TaskListenerSummary.__init__(self, host_str, sw_layers, file_handler)
        self._write_header()
    
    def _append_task(self, data_dict):
        self._file_handler.write(DELIMITER.join(
            [ '{zgt}', '{core}', '{name}', '{cnt_cpu}', '{min_cpu}'
            , '{avg_cpu}', '{max_cpu}', '{cnt_stack}', '{max_stack}'])
            .format(**data_dict))
        self._file_handler.write("\n")
    
    @_overrides(TaskListenerSummary)
    def _update_measurement(self, zgt, dt):
        TaskListenerSummary._update_measurement(self, zgt, dt)
        for t, m in self._task_measurements.iteritems():
            d = self._meas_to_dict(t, m)  
            d['zgt'] = zgt
            self._append_task(d) 
            self._task_measurements[t] = \
                {'core': '', 'stack_cnt': 0, 'stack_peak': '',
                 'runtime': {'cnt':0, 'min':0, 'max':0, 'sum':0, 'sample':0},
                 'overhead': {'cnt':0, 'min':0, 'max':0, 'sum':0, 'sample':0}}

    @_overrides(TaskListenerSummary)
    def _write_header(self):
        self._file_handler.write("#HEADER ")
        self._file_handler.write(DELIMITER.join(
            [ 'zgt', 'core', 'name', 'netto_CPU_usage_cnt'
            , 'netto_CPU_usage_min[%]', 'netto_CPU_usage_avg[%]'
            , 'netto_CPU_usage_max[%]', 'RAM_stack_usage_cnt'
            , 'RAM_stack_usage_max[Byte]']))
        self._file_handler.write("\n")
    
    @_overrides(TaskListenerSummary)   
    def _meas_to_dict(self, k, m):
        d = {}
        d['entity'] = 'TASK'
        d['core'] = m['core']
        d['name'] = '{}'.format(self._task_name_map.get(k, k))
        d['cnt_cpu'] = m['runtime']['cnt']
        
        if m['runtime']['cnt'] > 0:
            d['min_cpu'] = _div(m['runtime']['min'], 1, op='float')
            d['avg_cpu'] = _div(m['runtime']['sum'], d['cnt_cpu'], op='float')
            d['max_cpu'] = _div(m['runtime']['max'], 1, op='float')
        else: 
            d['min_cpu'] = ''
            d['avg_cpu'] = ''
            d['max_cpu'] = ''
        
        d['cnt_ovh'] = m['overhead']['cnt']
        if m['overhead']['cnt'] > 0:
            d['min_ovh'] = _div(m['overhead']['min'], 1, op='float')
            d['avg_ovh'] = _div(m['overhead']['sum'], d['cnt_ovh'], op='float')
            d['max_ovh'] = _div(m['overhead']['max'], 1, op='float')
        else: 
            d['min_ovh'] = ''
            d['avg_ovh'] = ''
            d['max_ovh'] = ''
            
        d['cnt_stack'] = m['stack_cnt']
        d['max_stack'] = m['stack_peak']
        
        try: 
            d['SW_layer'] = self._sw_layers[d['name']]['SW_layer']
        except KeyError:
            d['SW_layer'] = ''
        
        return d
        
    @_overrides(TaskListenerSummary)
    def write(self):
        raise NotImplementedError
        

class SwLayerListenerSummary(TaskListenerSummary):

    def __init__(self, host_str, sw_layers = {}, file_handler=sys.stdout):
        TaskListenerSummary.__init__(self, host_str, sw_layers, file_handler)
        self._sw_layer_measurement = {}
        for i in xrange(0, HOSTS[self._host_str]['cores']):
            self._sw_layer_measurement[i] = {}

    def _get_sw_layer(self, layer, core):
        try:
            self._sw_layer_measurement[core][layer]
        except KeyError:
            self._sw_layer_measurement[core][layer] = \
                {'core': '', 'runtime': {'cnt':0, 'min':'', 'max':'', 
                 'sum':'', 'sample':0}, 'overhead': {'cnt':0, 'min':'', 
                 'max':'', 'sum':'', 'sample':0}}
        return self._sw_layer_measurement[core][layer]

    @_overrides(TaskListenerSummary)
    def _update_measurement(self, zgt, dt):
        # a measurement is considered valid iff no errors were detected
        # during the sampling period and the length of the period does not 
        # exceed the sampling rate by more than 10%. 
        rate_OK = abs(dt - self._sampler._sample_rate) <= self._rate_range
        error_OK = not sum(self._error_cnt_sample)
        self._error_cnt_sample = [0, 0, 0]
        
        if not rate_OK:
            logger.debug("invalid sample rate {} @{}".format(dt, zgt))

        # for each known task updated the measurement
        for k,m in self._task_measurements.iteritems():
            # get the SW layer to which this task belongs
            n = self._task_name_map.get(k, k)
            sw_layer = self._sw_layers.get(n, None)
            if sw_layer is not None:
                sw_layer = self._get_sw_layer(sw_layer['SW_layer'], m['core'])
            else: 
                sw_layer = self._get_sw_layer(None, m['core'])
            sw_layer['runtime']['sample'] += m['runtime']['sample']
            sw_layer['overhead']['sample'] += m['overhead']['sample']
            m['runtime']['sample'] = 0 
            m['overhead']['sample'] = 0

        def update(meas):
            # update statistical values for given metric
            if meas['sample'] > 0:
                load = (meas['sample'] / float(dt))
                if meas['cnt'] > 0:
                    meas['min'] = min(meas['min'], load)
                    meas['max'] = max(meas['max'], load)
                    meas['sum'] += load
                else:
                    meas['min'] = load
                    meas['max'] = load
                    meas['sum'] = load
                meas['cnt'] += 1
 
        # for each known SW layer updated the measurement
        for c in self._sw_layer_measurement.itervalues():
            for k,m in c.iteritems():
                if error_OK and rate_OK:
                    update(m['runtime']) 
                    update(m['overhead']) 
                m['runtime']['sample'] = 0
                m['overhead']['sample'] = 0 

    @_overrides(TaskListenerSummary)
    def _write_header(self):
        self._file_handler.write("#HEADER ")
        self._file_handler.write(DELIMITER.join(
            [ 'core', 'SW_layer', 'netto_CPU_usage_cnt'
            , 'netto_CPU_usage_min[%]', 'netto_CPU_usage_avg[%]'
            , 'netto_CPU_usage_max[%]', 'overhead_cnt', 'overhead_min[%]'
            , 'overhead_avg[%]', 'overhead_max[%]']))
        self._file_handler.write("\n")

    @_overrides(TaskListenerSummary)
    def _meas_to_dict(self, k, m):
        d = {}
        d['core'] = m['core']
        d['sw_layer'] = k
        d['cnt_cpu'] = m['runtime']['cnt']
        d['min_cpu'] = _div(m['runtime']['min'], 1, op='float')
        d['avg_cpu'] = _div(m['runtime']['sum'], d['cnt_cpu'], op='float')
        d['max_cpu'] = _div(m['runtime']['max'], 1, op='float')
        d['cnt_ovh'] = m['overhead']['cnt']
        d['min_ovh'] = _div(m['overhead']['min'], 1, op='float')
        d['avg_ovh'] = _div(m['overhead']['sum'], d['cnt_cpu'], op='float')
        d['max_ovh'] = _div(m['overhead']['max'], 1, op='float')
        return d

    @_overrides(TaskListenerSummary)
    def write(self):
        self._write_header()
        for c,v in self._sw_layer_measurement.iteritems():
            for k,m in v.iteritems():
                if k is not None:
                    m['core'] = c
                    self._file_handler.write(DELIMITER.join(
                        [ '{core}', '{sw_layer}', '{cnt_cpu}', '{min_cpu}'
                        , '{avg_cpu}', '{max_cpu}', '{cnt_ovh}', '{min_ovh}'
                        , '{avg_ovh}', '{max_ovh}'])
                        .format(**self._meas_to_dict(k, m)))
                    self._file_handler.write('\n')


class NonOsListener(object):

    desc = { 'APH': { 0: 'Set 0 of drivers initialization finished'
                    , 5: 'Finished BIST'
                    , 1: 'Set 1 of drivers initialization finished'
                    , 4: 'Init runnables have finished execution'
                    , 2: 'Set 2 of drivers initialization finished'
                    , 8: 'Starts SSH and SRH by releasing their reset lines'
                    , 6: 'FlexRay Trcv is set to NORMAL mode'
                    , 7: 'FlexRay Trcv is synchronized'
                    , 16: 'Persistency unit triggered to write the data to NVM'
                    , 17: 'Persistency unit finished writing data to NVM'
                    , 18: 'FlexRay Trcv is set to SLEEP mode'
                    , 19: 'Shutdown BIST is triggered'
                    , 20: 'Shutdown BIST is finished'}
           , 'SSH': { 0x01: 'Basic I//O - OS drivers - ZGT and tracing '
                            'framework are available'
                    , 0x02: 'Flashing over FTP - file system(s) - switch '
                            'driver - networking - gPTP and LIN are available'
                    , 0x07: 'First part of the platform init finished - '
                            'start of platform SWC initialization '
                    , 0x08: 'Starting initialization of the next SWC batch '
                    , 0x09: 'All SWCs including application SWCs are '
                            'initialized'
                    , 0x0b: 'ZGT is synchronized'
                    , 0x0c: 'Init runnables have finished execution'
                    , 0x0d: 'Periodic time-triggered schedule started'}
           , 'SRH': { 0x200: 'Total execution time of init runnables [us]'}}


    def __init__(self, host_str, file_handler=sys.stdout):
        self._host_str = host_str
        self._file_handler = file_handler
        self._checkpoints = []
        self._zgt_correction = None
        pm_instrument.zgt_correction_callback_add(self._zgt_correction_cb)
        pm_instrument.checkpoint_callback_add(self._checkpoint_cb)

    def _zgt_correction_cb(self, host, **signal):
        if host != self._host_str: return
        self._zgt_correction_cb = signal

    def _checkpoint_cb(self, host, **signal):
        if host != self._host_str: return
        self._checkpoints.append(signal)

    def write(self):
        self._file_handler.write("#HEADER ")
        self._file_handler.write(DELIMITER.join(
            ['abs_time[us]', 'rel_time[us]', 'id', 'description']))
        self._file_handler.write("\n")
        old_t = self._checkpoints[0]['zgt'] if self._checkpoints else 0         
        for c in self._checkpoints:
            self._file_handler.write(DELIMITER.join \
                ([ "{}".format(c['zgt'])
                 , "{}".format(c['zgt'] - old_t)
                 , "{}".format(c['id'])
                 , "{}".format(self.desc[self._host_str].get(c['id'],'tbd'))]))
            self._file_handler.write('\n')
            old_t = c['zgt']

    def close(self):
        if sys.stdout != self._file_handler:
            self._file_handler.close()


class AggregatedListener(TaskListenerSummary):
    
    def __init__(self, host_str, file_handler=sys.stdout):
        TaskListenerSummary.__init__(self, host_str, {}, file_handler)
        self._core_overhead = {}
        self._state_error = 0
        self._sequence_error = 0
        self._zgt_error = 0
        self._event_cnt = 0
        self._start_time = 0
        self._current_time = 0
        pm_instrument.receive_event_callback_add(self._event_received_cb)
    
    def _is_idle_task(self, task_id):
        return IDLE_TASK_PATTERN[self._host_str] \
            in self._task_name_map.get(task_id, 'no')
    
    def _event_received_cb(self, zgt, **signal):
        self._event_cnt += 1
        if self._start_time == 0:
            self._start_time = zgt
        self._current_time = zgt
    
    def _get_core(self, _id):
        try: 
            return self._core_overhead[_id]
        except KeyError:
            self._core_overhead[_id] = \
                {'cnt':0, 'min':0, 'max':0, 'sum':0, 'sample':0}
        return self._core_overhead[_id]
    
    @_overrides(TaskListenerSummary)
    def _update_measurement(self, zgt, dt):
        for m in self._task_measurements.itervalues():
            c = self._get_core(m['core'])
            c['sample'] += m['overhead']['sample']
            
        rate_OK = abs(dt - self._sampler._sample_rate) <= self._rate_range
        error_OK = not sum(self._error_cnt_sample)
        TaskListenerSummary._update_measurement(self, zgt, dt)
        
        # updated overhead statistics for cores
        for i in xrange(0, HOSTS[self._host_str]['cores']):  
            meas = self._get_core(i)
            if rate_OK and error_OK and meas['sample'] > 0:
                load = (meas['sample'] / float(dt))
                if meas['cnt'] > 0:
                    meas['min'] = min(meas['min'], load)
                    meas['max'] = max(meas['max'], load)
                    meas['sum'] += load
                else:
                    meas['min'] = load
                    meas['max'] = load
                    meas['sum'] = load
                meas['cnt'] += 1
            meas['sample'] = 0
    
    @_overrides(TaskListenerSummary)
    def _state_error_cb(self, host, **signal):
        if host != self._host_str: return
        TaskListenerSummary._state_error_cb(self, host, **signal)
        self._state_error += 1
    
    @_overrides(TaskListenerSummary)
    def _sequence_error_cb(self, host, missing, **signal):
        if host != self._host_str: return
        TaskListenerSummary._sequence_error_cb(self, host, missing, **signal)
        self._sequence_error += missing
    
    @_overrides(TaskListenerSummary)
    def _zgt_error_cb(self, host, **signal):
        if host != self._host_str: return
        TaskListenerSummary._zgt_error_cb(self, **signal)
        self._zgt_error += 1

    @_overrides(TaskListenerSummary)
    def _write_header(self):
        self._file_handler.write("#HEADER host{}".format(DELIMITER))
        for i in xrange(0, HOSTS[self._host_str]['cores']):
            self._file_handler.write(DELIMITER.join(
                ['total_CPU_usage_core_{}_cnt'.format(i) 
                , 'total_CPU_usage_core_{}_min[%]'.format(i)
                , 'total_CPU_usage_core_{}_avg[%]'.format(i)
                , 'total_CPU_usage_core_{}_max[%]'.format(i)
                , 'overhead_core_{}_cnt'.format(i) 
                , 'overhead_core_{}_min[%]'.format(i)
                , 'overhead_core_{}_avg[%]'.format(i)
                , 'overhead_core_{}_max[%]{}'.format(i, DELIMITER)]))
        self._file_handler.write(DELIMITER.join(
            [ 'lost_tracing_events', 'zgt_errors', 'trace_event_errors'
            , 'measurement_session_length[us]']))
        self._file_handler.write("\n")

    @_overrides(TaskListenerSummary)
    def write(self):
        self._write_header()
        if self._event_cnt == 0: 
            return

        # for each core get the corresponding idle task
        idle_tasks = {v['core']: v for (k, v) in 
            self._task_measurements.iteritems() 
            if self._is_idle_task(k)}

        self._file_handler.write("{}{}".format(self._host_str, DELIMITER))
        for i in xrange(0,HOSTS[self._host_str]['cores']):
            try:
                m = idle_tasks[i]['runtime']
            except KeyError:
                m = {'cnt': 0, 'max': '', 'min': '', 'sum': ''}
            c = self._get_core(i)
            min_load = 1 - m['max'] if m['max'] != '' else ''
            max_load = 1 - m['min'] if m['min'] != '' else ''
            avg_load = _div(m['sum'], m['cnt'], op='float')
            if avg_load != '': 
                avg_load = '{0:2.2f}'.format(100 - float(avg_load))
            self._file_handler.write(DELIMITER.join(
                [ '{}'.format(m['cnt']) 
                , '{}'.format(_div(min_load, 1, op='float'))
                , '{}'.format(avg_load)
                , '{}'.format(_div(max_load, 1, op='float'))
                , '{}'.format(c['cnt']) 
                , '{}'.format(_div(c['min'], 1, op='float'))
                , '{}'.format(_div(c['sum'], c['cnt'], op='float'))
                , '{}{}'.format(_div(c['max'], 1, op='float'), DELIMITER)]))
        
        self._file_handler.write(DELIMITER.join(
            [ '{}'.format(self._sequence_error)
            , '{}'.format(self._zgt_error)
            , '{}'.format(self._state_error)
            , '{}'.format(self._current_time - self._start_time)]))


class DriverListenerSummary(object):
    
    def __init__(self, host_str, driver_map = {}, file_handler=sys.stdout):
        self._host_str = host_str
        self._file_handler = file_handler
        self._driver_measurements = {}
        self._driver_name_map = driver_map
        pm_instrument.driver_netto_rt_callback_add(self._driver_netto_rt_cb)
        pm_instrument.driver_gross_rt_callback_add(self._driver_gross_rt_cb)
        pm_instrument.driver_activation_callback_add(self._driver_period_cb)    

    def _get_driver(self, _id):
        try: 
            self._driver_measurements[_id];
        except KeyError:
            self._driver_measurements[_id] = \
                { 'core': ''
                , 'period': {'cnt':0, 'max': '', 'min': '', 'sum': ''}
                , 'netto': {'cnt':0, 'max': '', 'min': '', 'sum': ''}
                , 'gross': {'cnt':0, 'max': '', 'min': '', 'sum': ''}}
        return self._driver_measurements[_id] 

    def _driver_period_cb(self, host, periodic_activation, **signal):
        if host != self._host_str: return
        meas = self._get_driver(signal['id'])['period']
        if 0 == meas['cnt']:
            meas['max'] = periodic_activation
            meas['min'] = periodic_activation
            meas['sum'] = periodic_activation
        else:
            meas['sum'] += periodic_activation
            meas['max'] = max(periodic_activation, meas['max'])
            meas['min'] = min(periodic_activation, meas['min'])
        meas['cnt'] += 1

    def _driver_gross_rt_cb(self, host, core, swc, gross_rt, **signal):
        if host != self._host_str: return
        meas = self._get_driver(signal['id'])['gross']
        if 0 == meas['cnt']:
            meas['max'] = gross_rt
            meas['min'] = gross_rt
            meas['sum'] = gross_rt
            self._get_driver(signal['id'])['core'] = core
        else:
            meas['sum'] += gross_rt
            meas['max'] = max(gross_rt, meas['max'])
            meas['min'] = min(gross_rt, meas['min'])
        meas['cnt'] += 1

    def _driver_netto_rt_cb(self, host, netto_rt, **signal):
        if host != self._host_str: return
        meas = self._get_driver(signal['id'])['netto']
        if 0 == meas['cnt']:
            meas['max'] = netto_rt
            meas['min'] = netto_rt
            meas['sum'] = netto_rt
        else:
            meas['sum'] += netto_rt
            meas['max'] = max(netto_rt, meas['max'])
            meas['min'] = min(netto_rt, meas['min'])
        meas['cnt'] += 1

    def _meas_to_dict(self, r, m):
        d = {}
        d['entity'] = 'DRIVER'
        d['core'] = m['core']
        d['swc'] = ''
        d['name'] = self._driver_name_map.get(r, r)
        d['avg_netto'] = _div(m['netto']['sum'], m['netto']['cnt'])
        d['avg_gross'] = _div(m['gross']['sum'], m['gross']['cnt'])
        d['avg_period'] = _div(m['period']['sum'], m['period']['cnt'])
        d['min_netto'] = m['netto']['min']
        d['max_netto'] = m['netto']['max']
        d['cnt_netto'] = m['netto']['cnt']
        d['cnt_cpu'] = ''
        d['min_cpu'] = _div(m['netto']['min'], d['avg_period'], op='float')
        d['avg_cpu'] = _div(d['avg_netto'], d['avg_period'], op='float')
        d['max_cpu'] = _div(m['netto']['max'], d['avg_period'], op='float')
        d['cnt_gross'] = m['gross']['cnt']
        d['max_gross'] = m['gross']['max']
        d['min_gross'] = m['gross']['min']
        d['cnt_period'] = m['period']['cnt']
        d['min_period'] = m['period']['min']
        d['max_period'] = m['period']['max']
        d['min_budget'] = ''
        d['avg_budget'] = ''
        d['max_budget'] = ''
        d['cnt_stack'] = ''
        d['max_stack'] = ''
        return d

    def _write_header(self):
        self._file_handler.write("#HEADER ")
        self._file_handler.write(DELIMITER.join(
            [ 'core', 'driver', 'netto_CPU_time_cnt'
            , 'netto_CPU_time_min[us]', 'netto_CPU_time_avg[us]'
            , 'netto_CPU_time_max[us]', 'gross_CPU_time_cnt'
            , 'gross_CPU_time_min[us]', 'gross_CPU_time_avg[us]'
            , 'gross_CPU_time_max[us]', 'cyclic_activation_cnt'
            , 'cyclic_activation_min[us]', 'cyclic_activation_avg[us]'
            , 'cyclic_activation_max[us]', 'netto_CPU_usage_min[%]'
            , 'netto_CPU_usage_avg[%]', 'netto_CPU_usage_max[%]']))
        self._file_handler.write("\n") 

    def write(self):
        self._write_header()
        func = lambda y: y[1]['core']
        for (k, v) in sorted(self._driver_measurements.items(), key=func): 
            self._file_handler.write(DELIMITER.join(
                [ '{core}', '{name}', '{cnt_netto}'
                , '{min_netto}', '{avg_netto}', '{max_netto}'
                , '{cnt_gross}', '{min_gross}', '{avg_gross}'
                , '{max_gross}', '{cnt_period}', '{min_period}'
                , '{avg_period}', '{max_period}', '{min_cpu}'
                , '{avg_cpu}', '{max_cpu}'])
                .format(**self._meas_to_dict(k, v)))
            self._file_handler.write("\n")

    def close(self):
        if sys.stdout != self._file_handler:
            self._file_handler.close()


class DriverListenerTrace(DriverListenerSummary):
    
    def __init__(self, host_str, driver_map = {}, file_handler=sys.stdout):
        DriverListenerSummary.__init__(self, host_str, driver_map, file_handler)
        self._sampler = Sampler(host_str, self._update_measurement)
        self._write_header()

    def _update_measurement(self, zgt, dt):
        for k, m in self._driver_measurements.iteritems():
            d = DriverListenerSummary._meas_to_dict(self, k, m)  
            d['zgt'] = zgt
            self._append_to_file(d) 
            m['period'] = {'cnt':0, 'max': '', 'min': '', 'sum': ''}
            m['netto'] = {'cnt':0, 'max': '', 'min': '', 'sum': ''}
            m['gross'] = {'cnt':0, 'max': '', 'min': '', 'sum': ''}

    def _append_to_file(self, data_dict):
        self._file_handler.write(DELIMITER.join(
            [ '{zgt}', '{core}', '{name}', '{cnt_netto}'
            , '{min_netto}', '{avg_netto}', '{max_netto}', '{cnt_gross}'
            , '{min_gross}', '{avg_gross}', '{max_gross}', '{cnt_period}'
            , '{min_period}', '{avg_period}', '{max_period}', '{min_cpu}'
            , '{avg_cpu}', '{max_cpu}']).format(**data_dict))
        self._file_handler.write("\n")

    @_overrides(DriverListenerSummary)
    def _write_header(self):
        self._file_handler.write("#HEADER ")
        self._file_handler.write(DELIMITER.join(
            [ 'zgt', 'core', 'swc', 'runnable', 'netto_CPU_time_cnt'
            , 'netto_CPU_time_min[us]', 'netto_CPU_time_avg[us]'
            , 'netto_CPU_time_max[us]', 'gross_CPU_time_cnt'
            , 'gross_CPU_time_min[us]', 'gross_CPU_time_avg[us]'
            , 'gross_CPU_time_max[us]', 'cyclic_activation_cnt'
            , 'cyclic_activation_min[us]', 'cyclic_activation_avg[us]'
            , 'cyclic_activation_max[us]', 'netto_CPU_usage_min[%]'
            , 'netto_CPU_usage_avg[%]', 'netto_CPU_usage_max[%]']))
        self._file_handler.write("\n") 
        
    @_overrides(DriverListenerSummary)
    def write(self):
        raise NotImplementedError


__version__ = "$Revision: 80204 $".split()[1]
__all__ = [ 'SwcListener', 'RunnableListenerSummary', 'TaskListenerSummary'
          , 'NonOsListener', 'AggregatedListener', 'RunnableListenerTrace'
          , 'TaskListenerTrace', 'DriverListenerTrace' ]


if __name__ == '__main__':

    def _csv_mode (csv_file):
        sep = b","
        quote = b"#"
        regex = re.compile(r"#HEADER[ ]*")
        has_header = False
    
        with open(csv_file, 'rb') as csvfile:
            lines = csvfile.readlines()
            
            for i, l in enumerate(lines):
                if l.startswith("#HEADER"):
                    lines[i] = regex.sub('', l)
                    has_header = True
                    break
        
            if not has_header:
                sys.stderr.write("header not defined");
                return
        
            reader = csv.DictReader(lines, delimiter=sep, quotechar=quote)  
            for row in reader:
                pm_instrument.receive_event(row)
                # rtcalc.process(tr)
        return 
    # end_def _csv_mode
    
    start_time = time.time()
    ra = RA.RA(init=False)
    pm_rnbl = RunnableListenerSummary(1, ra)

    try:
        _csv_mode("..\\scripts\\smaller.csv")
    except:
        raise # do nothing
    
    pm_rnbl.write()
    print("\n--- %s seconds ---" % (time.time() - start_time))
    
