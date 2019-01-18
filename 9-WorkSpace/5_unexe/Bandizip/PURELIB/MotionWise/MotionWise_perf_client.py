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
#    10-Jul-2015 (GWI) initial creation
#    03-Oct-2017 (SKW) [IECU-244] Os_ECU*.htm is not created with a new SIP
# --

import os
import sys
import time
import signal
import logging
import traceback
import file_parser as FP
from MotionWise import pm_instrument
from multiprocessing import Process
from MotionWise import pm_measurement as PM
from MotionWise.log_proc import QueueHandler

TIME_STAMP = "{}".format(time.strftime("%Y-%m-%d_%H-%M-%S"))
logger = logging.getLogger(__name__)


class KeyboardInterruptGuard(object):
    """
    Delays a received KeyboardInterrupt for the duration of a with block
    """

    def _handler(self, signal, frame):
        self.signal_received = (signal, frame)
    
    def __enter__(self):
        self.signal_received = False
        self._old_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, self._handler)

    def __exit__(self, _type, value, traceback):
        signal.signal(signal.SIGINT, self._old_handler)
        if self.signal_received:
            self._old_handler(*self.signal_received)

            
class Client(Process):
    """
    Client receives trace events over a pipe connection. It computes the 
    statistical values and writes the output files.
    """
    
    def __init__(self, ra_model, pipe_conn, args, log_queue):
        super(Client, self).__init__()
        self._is_process = not args.csv_file
        self._log_queue = log_queue
        self._host = args.host.upper()
        self._pipe_conn = pipe_conn
        self._event_cnt = 0
        self._lost_events = 0
        self._lost_frames = 0
        self._timeout = 0.5 if (args.csv_file or args.pcap_file) else 10
        self._out_path = args.out_path
        self._args = args
        self._ra_model = ra_model
        fn = args.__dict__["{}_sched_info".format(args.host.lower())]
        self._gen_info = FP.parse_schedule_generation_info_file(fn)
        self._budget = {k: v['wcet'] for (k,v) in self._gen_info.iteritems()} 
        self._periods = {k: v['period'] for (k,v) in self._gen_info.iteritems()}
        self._sw_layers = FP.parse_entity_sw_layers(args.sw_layers)[self._host]
        if False == self._is_process: 
            # In order to prevent the starting method to spawn a new process
            # it is overridden with the run method. 
            self.start = self.run
        else:
            pass

    def _sequence_error_cb(self, host, missing, **signal):
        self._lost_events += missing
        self._lost_frames += (missing / 69)
        logger.warning("host: {}, missing events: {}@{}".format(host, missing, signal['zgt']))
      
    def _formatter(self, raw_cnt):
        """
        Transforms a counter value to a formatted string
        """
        if raw_cnt >= 1e6:
            return "{0:.2f}M".format(raw_cnt / 1e6)
        elif raw_cnt >= 1e3:
            return "{}k".format(int(raw_cnt / 1e3))
        else:
            return "{}".format(raw_cnt)   
    
    def _status(self):
        return 'received trace events: {}, lost trace events: {}   ' \
                .format(self._formatter(self._event_cnt), self._lost_events) 
            
    def _flush(self):
        while self._pipe_conn.poll():
            cmd = self._pipe_conn.recv()
            if cmd == "EOF": break
        self._pipe_conn.close()
    
    def _create_listeners(self):
        """
        @brief Creates listeners for performance measurement instrumentation
        """
        out = {}
        sep_str = ''
        op = os.path.join(self._out_path, 'output')
        if not os.path.isdir(op): 
            os.mkdir(op)
            
        if self._args.msexcel_compat: 
            sep_str = 'sep={}\n'.format(PM.DELIMITER)
        
        ver_str = "MotionWise_Perf.py v{}, IF-Set {}".format(self._args.version, 
                    self._ra_model.get_IFSET())
        
        pre = "{}_MotionWise-PMT".format(TIME_STAMP)
        s_pre = pre + "_statistical-analysis-summary_"   
        t_pre = pre + "_statistical-analysis-trace_" 
        
        if not (self._args.output_trace_events_off or self._args.csv_file):
            fh = open(os.path.join(op, pre + '_trace_events.csv'), 'w+')
            fh.write('{}#generated with {}\n'.format(sep_str, ver_str))
            out['trace_log'] = PM.TraceListener(self._host, file_handler = fh)
        
        fh = open(os.path.join(op, s_pre + 'checkpoint.csv'), 'w+')
        fh.write('{}#generated with {}\n'.format(sep_str, ver_str))
        out['chkpoint_summary'] = PM.NonOsListener(self._host, 
            file_handler = fh)
        
        fh = open(os.path.join(op, s_pre + 'runnable.csv'), 'w+')
        fh.write('{}#generated with {}\n'.format(sep_str, ver_str))
        out['rnbl_summary'] = PM.RunnableListenerSummary(self._host, 
            self._ra_model, file_handler = fh, budget = self._budget, 
            periods = self._periods, sw_layers = self._sw_layers)
        
        fh = open(os.path.join(op, s_pre + 'task.csv'), 'w+')
        fh.write('{}#generated with {}\n'.format(sep_str, ver_str))
        out['task_summary'] = PM.TaskListenerSummary(self._host, 
            sw_layers = self._sw_layers, file_handler = fh)
        out['task_summary'].load_aph_task_map(self._args.aph_taskmap1, self._args.aph_taskmap2)
        
        fh = open(os.path.join(op, s_pre + 'sw_layer.csv'), 'w+')
        fh.write('{}#generated with {}\n'.format(sep_str, ver_str))
        out['sw_layer_summary'] = PM.SwLayerListenerSummary(self._host, 
            sw_layers = self._sw_layers, file_handler=fh)
        out['sw_layer_summary'].load_aph_task_map(self._args.aph_taskmap1, self._args.aph_taskmap2)
        
        fh = open(os.path.join(op, s_pre + 'aggregated.csv'), 'w+')
        fh.write('{}#generated with {}\n'.format(sep_str, ver_str))
        out['aggr_summary'] = PM.AggregatedListener(self._host, 
            file_handler=fh)
        out['aggr_summary'].load_aph_task_map(self._args.aph_taskmap1, self._args.aph_taskmap2)
        
        if self._args.trace_statistics:
            fh = open(os.path.join(op, t_pre + 'runnable.csv'), 'w+')
            fh.write('{}#generated with {}\n'.format(sep_str, ver_str))
            out['rnbl_trace'] = PM.RunnableListenerTrace(self._host, 
                self._ra_model, file_handler = fh, budget = self._budget, 
                periods = self._periods, sw_layers = self._sw_layers)
            
            fh = open(os.path.join(op, t_pre + 'task.csv'), 'w+')
            fh.write('{}#generated with {}\n'.format(sep_str, ver_str))
            out['task_trace'] = PM.TaskListenerTrace(self._host, 
                sw_layers = self._sw_layers, file_handler = fh)
            out['task_trace'].load_aph_task_map(self._args.aph_taskmap1, self._args.aph_taskmap2)
        
        if self._args.trace_drivers:
            driver_map = FP.load_driver_name_map(self._args.aph_driver_ids)
            if not driver_map:
                logger.warning('could not load driver ID to name mapping '
                               'file {}'.format(self._args.aph_driver_ids))
                               
            fh = open(os.path.join(op, s_pre + 'driver.csv'), 'w+')
            fh.write('{}#generated with {}\n'.format(sep_str, ver_str))
            out['driver_summary'] = PM.DriverListenerSummary(self._host, 
                file_handler=fh, driver_map = driver_map)
                
            if self._args.trace_statistics:
                fh = open(os.path.join(op, t_pre + 'driver.csv'), 'w+')
                fh.write('{}#generated with {}\n'.format(sep_str, ver_str))
                out['driver_summary'] = PM.DriverListenerTrace(self._host, 
                    file_handler = fh, driver_map = driver_map)    
        
        
        return out
    
    def _wait_for_EOF(self, pipe):
        """
        @brief Polls pipe until 'EOF' is received 
        """
        item = ''
        while item != 'EOF': 
            if pipe.poll():
                item = pipe.recv()

    def _configure_logging(self):#
        if self._is_process:
            # configure root logger only if client runs in an own process
            h = QueueHandler(self._log_queue)
            root = logging.getLogger()
            root.addHandler(h)
            root.setLevel(logging.DEBUG)
    
    def flush_pipe(self):
        self.run = self._flush
        self.start()

    def run(self):
        try:  
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            pm_instrument.sequence_error_callback_add(self._sequence_error_cb)
            self._configure_logging()
            last_poll = time.time()
            pipe = self._pipe_conn
            guard = KeyboardInterruptGuard()   
            listener = self._create_listeners()
            logger.info("$cpress Ctrl-C to stop and write output files")
            time.sleep(0.01) # XXX wait for loc_proc to write last line
            sys.stdout.write('[MotionWise_Perf]: %s\r' % self._status())
            
            # start loop which to poll for trace events
            with guard: 
                while True: 
                    if pipe.poll():
                        last_poll = time.time()
                        item = pipe.recv()
                        if item != 'EOF':
                            pm_instrument.receive_event(item)
                            self._event_cnt += 1
                            if not self._event_cnt % 1000:
                                sys.stdout.write('[MotionWise_Perf]: %s\r' 
                                                 % self._status())
                        else: 
                            break # No more data to be received. 
                    else:
                        if (time.time() - last_poll) > self._timeout:
                            # If no event where received during the last x 
                            # seconds the termination signal is raised
                            guard.signal_received = True
                                
                    if guard.signal_received:
                        # termination of program requested 
                        guard.signal_received = False
                        if False == self._is_process: 
                            # Client runs in the context of main process. It 
                            # exits the while loop to terminate program.
                            break 
                        else: 
                            # Client runs as own process. It notifies the main 
                            # process that it wants to terminate. 
                            try: 
                                pipe.send('EOF')
                            except IOError: 
                                pass
        except Exception: 
            # XXX exchange with logging call
            logger.error("$cscript has been terminated due to an exception")
            logger.exception(traceback.format_exc())
            pipe.send('EOF')
            self._wait_for_EOF(pipe)
        finally:
            pipe.close()
            if 'listener' in locals():
                for l in listener.itervalues():
                    try: 
                        l.write()
                    except AttributeError:
                        pass
                    except NotImplementedError:
                        pass
                    l.close() 
                logger.info('$c%s' % self._status())
                logger.info("$coutput files written to %s\\output" % self._out_path)


__version__ = "$Revision: 80204 $".split()[1]

if __name__ == '__main__':
    pass
