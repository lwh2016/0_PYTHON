#!C:\Python27\python.exe

# Copyright (C) 2013 TTTech Computertechnik AG. All rights reserved
# Schoenbrunnerstrasse 7, A--1040 Wien, Austria. office@tttech.com
#
# ++
# Name
#    MotionWise_Perf.py
#
# Purpose
#    Script for MotionWise runnable runtime measurement
#
# Authors
#    Thomas Fabian <extern.thomas.fabian@tttech-automotive.com>
#    Georg Wiesmann <georg.wiesmann@tttech-automotive.com>
#
# Revision Dates
#    09-Feb-2016 (HLI) taken from zFAS
#    18-Feb-2016 (HLI) removed srh
#    23-Jun-2016 (JDU) [MotionWise-3874] support for SRH (hard-coded filenames)
#    28-Jun-2016 (JDU) [MotionWise-3874] support for SRH (hard-coded filenames)
#    29-Jun-2016 (JDU) [MotionWise-3972] support for SRH (hard-coded filenames)
#    03-Oct-2017 (SKW) [IECU-244] Os_ECU*.htm is not created with a new SIP
# --

import os
import sys
import time
import signal
import logging
import textwrap
import argparse
import multiprocessing

parent_dir  = os.path.join(os.path.dirname(os.path.abspath (__file__)), "..")
if not os.path.exists (os.path.join (parent_dir, 'MotionWise')):
    parent_dir = os.path.join (parent_dir, "lib", "site-packages")
    APH_DRIVER_ID = os.path.join \
        (parent_dir, "MotionWise", "data", "PerfMeas_DriverIDs.h") 
    APH_TASKMAP1 = os.path.join(parent_dir
        , "MotionWise", "data", "Os_Types_Lcfg.h")
    APH_TASKMAP2 = os.path.join(parent_dir
        , "MotionWise", "data", "ApplicationHost_Os_ecuc.arxml")
    APH_SCHED_INFO = os.path.join(parent_dir
        , "MotionWise", "data", "generation_info_schedule_APH.csv")
    SSH_SCHED_INFO = os.path.join(parent_dir
        , "MotionWise", "data", "generation_info_schedule_SSH.csv")
    SRH_SCHED_INFO = os.path.join(parent_dir
        , "MotionWise", "data", "generation_info_schedule_SRH.csv")
    SW_LAYERS_MAP = os.path.join(parent_dir
        , "MotionWise", "data", "entity_sw_layers.csv")
else:
    root = os.path.join (parent_dir, "..", "..", "..") 
    APH_DRIVER_ID = os.path.join \
        ( root, "0210_BasicSoftware", "PerfMeas", "03_src"
        , "PerfMeas_DriverIDs.h"
        )
    APH_TASKMAP1 = os.path.join \
        ( root, "..", "0700_GenData", "01_Platform"
        , "APH", "System", "BSW", "Os", "Os_Types_Lcfg.h"
        )
    APH_TASKMAP2 = os.path.join \
        ( root, "..", "0200_Platform", "0240_ApplicationHost"
        , "System", "Config", "ECUC", "ApplicationHost_Os_ecuc.arxml"
        )
    APH_SCHED_INFO = os.path.join \
        ( root, "..", "0700_GenData","01_Platform", "APH", "System", "Schedule"
        , "generation_info_schedule_APH.csv"
        )
    SSH_SCHED_INFO = os.path.join \
        ( root, "..", "0700_GenData","01_Platform", "SSH", "System", "Schedule"
        , "generation_info_schedule_SSH.csv"
        )
    SRH_SCHED_INFO = os.path.join \
        ( root, "..", "0700_GenData","01_Platform", "SRH", "System", "Schedule"
        , "generation_info_schedule_SRH.csv"
        )
    SW_LAYERS_MAP = os.path.join \
        ( root, "0230_Tools", "public", "MotionWise_PyTools", "MotionWise", "data" 
        , "entity_sw_layers.csv"
        )
sys.path.insert(0, parent_dir)

from MotionWise import pm_instrument
from MotionWise import file_parser as FP
from MotionWise.MotionWise_perf_proxy import Proxy 
from MotionWise.RA import __version__ as ra_ver
from MotionWise import pm_measurement
from MotionWise.log_proc import QueueHandler, log_listener
from MotionWise.MotionWise_perf_client import Client, TIME_STAMP

HOST_CFG_ID = {"APH" : 0, "SSH" : 0x40, "SRH" : 0x80}
logger      = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def version():
    """
    @brief Retrieves the MotionWise_Perf version string
    
    The function returns the version of the MotionWise_Perf script. The verison 
    string consists of major version, minor version and SVN revision. 
    
    @return MotionWise_Perf version as string
    """
    from MotionWise.log_proc import __version__ as log_ver
    from MotionWise.pm_measurement import __version__ as pm_ver
    from MotionWise.MotionWise_perf_proxy import __version__ as proxy_ver 
    from MotionWise.MotionWise_perf_client import __version__ as client_ver 
    
    ver = "$Revision: 80204 $".split()[1]
    batch = max([ pm_instrument.version().split('.')[-1], log_ver
                , ver, pm_ver, proxy_ver, client_ver, FP.__version__])
    return "3.0.{}".format(batch)


def _get_trace_config(ra_model, enabled_rnbls, rnbl_to_task_mapping):
    """
    @brief Creates the trace config dictionary
    
    Creates a dictionary which contains all names of runnables or tasks for 
    which tracing shall be enabled. 
     
    """
    config = {'tasks': [], 'runnables': [], 'task_name_id': {}}
    if 'all' in enabled_rnbls:
        config['tasks'] = ['all']
        config['runnables'] = ['all']
    else:
        for r in enabled_rnbls:
            try:
                int(r)
                r = ra_model.get_runnable_name_of_runnable_id(int(r))
                if r is None:
                    logger.warning('invalid runnable ID {}'.format(r))
                    continue
            except ValueError:
                if r not in rnbl_to_task_mapping.keys():
                    logger.warning('invalid runnable name "{}"'.format(r))    
                    continue
            config['runnables'].append(r)
            config['tasks'].append(rnbl_to_task_mapping[r]['task'])

    if not config['runnables']:
        logger.warning('tracing disabled for all runnables')
    return config


def _app_trace_config(proxy, host_str, config, meas_driver):
    # disable tracing for all except monitored host
    for k,v in HOST_CFG_ID.iteritems():
        if k != host_str: proxy.config_trace(False, v)

    if config['task_name_id']:
        # get name of idle tasks
        idle_tasks = [name for name in config['task_name_id'].iterkeys() 
                      if pm_measurement.IDLE_TASK_PATTERN[host_str] in name]
        logger.debug("Names of idle tasks: {}".format(idle_tasks))
        if 'all' not in config['tasks']:
            # idle tasks shall always be enabled in order to be able to 
            # measure CPU load. 
            config['tasks'].extend(idle_tasks)
    else: 
        config['tasks'] = ['all']
        logger.warning("no task name to task ID mapping available")
    
    # enable stack peak event
    proxy.config_trace_event(10, True, HOST_CFG_ID[host_str])
    
    # enable driver start stop events    
    if meas_driver:
        proxy.config_trace_driver(0xFFFF, True, HOST_CFG_ID[host_str])
        config['tasks'].extend([name for name in 
                      config['task_name_id'].iterkeys() 
                      if 'TASK_SCHM_' in name.upper()])
        proxy.config_trace_event(7, True, HOST_CFG_ID[host_str])
        proxy.config_trace_event(8, True, HOST_CFG_ID[host_str])
        
    # enable task switch events for traced tasks
    if 'all' in config['tasks']:
        proxy.config_trace_task(0xFFFFFFFF, True, HOST_CFG_ID[host_str])
        logger.info('tracing enabled for all task')
    else:
        proxy.config_trace_task(0xFFFFFFFF, False, HOST_CFG_ID[host_str])
        for task in config['tasks']:
            tid = config['task_name_id'][task]
            proxy.config_trace_task(tid, True, HOST_CFG_ID[host_str])
            logger.info('tracing enabled for task {}'.format(task))
    proxy.config_trace_event(2, True, HOST_CFG_ID[host_str])
    
    # enable runnable start stop events
    if 'all' in config['runnables']:
        proxy.config_trace_runnable(0xFFFF, True, HOST_CFG_ID[host_str])
        logger.info('tracing enabled for all runnables')
    else:
        proxy.config_trace_runnable(0xFFFF, False, HOST_CFG_ID[host_str])
        for rid,rname in proxy.ra_model.id_to_runnable.iteritems():
            if rname in config['runnables']:
                proxy.config_trace_runnable(rid, True, HOST_CFG_ID[host_str])
                logger.info('tracing enabled for runnable {}'.format(rname))
    proxy.config_trace_event(0, True, HOST_CFG_ID[host_str])
    proxy.config_trace_event(1, True, HOST_CFG_ID[host_str])
    proxy.config_trace_event(13, True, HOST_CFG_ID[host_str])
    
    
def _req_task_name_id_mapping(proxy, host_str):
    out = {}
    
    def _task_map_cb(host, task_id, task_name, **signal):
        if not host_str == host: return
        out[task_name] = task_id
        logger.debug("{} - {}".format(task_id, task_name))

    proxy.config_log_sink('eth') 
    proxy.config_log_level(["info"])
    proxy.config_log(0xfe, 1, 'info')
    proxy.log_callback_add(pm_instrument.receive_event)
    pm_instrument.task_map_callback_add(_task_map_cb)
    proxy.receiving_start()
    proxy.config_trace_set_trigger(0x01, HOST_CFG_ID[host_str])
    
    # XXX wait here until all whole mapping is received 
    time.sleep(2)
    
    # reset logging
    proxy.config_log_sink('uart') 
    proxy.config_log_level(["error", "warning", "info"])
    proxy.log_callback_remove()
    return out
  

def _clean_up(proxy, host_str, csv_file):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    proxy.tracelog_callback_remove()  
    proxy.receiving_stop()
    proxy.parent_conn.send("EOF")
    proxy.parent_conn.close()  
    if not csv_file:
        proxy.config_trace(False, HOST_CFG_ID[host_str])
        proxy.config_trace_event(13, False, HOST_CFG_ID[host_str])
        proxy.config_trace_driver(0xFFFF, False, HOST_CFG_ID[host_str])
        proxy.config_trace_event(7, False, HOST_CFG_ID[host_str])
        proxy.config_trace_event(8, False, HOST_CFG_ID[host_str])
        proxy.config_trace_task(0xFFFFFFFF, False, HOST_CFG_ID[host_str])
        proxy.config_trace_event(2, False, HOST_CFG_ID[host_str])
        proxy.config_trace_runnable(0xFFFF, True, HOST_CFG_ID[host_str])
        proxy.config_trace_event(0, True, HOST_CFG_ID[host_str])
        proxy.config_trace_event(1, True, HOST_CFG_ID[host_str])			
        for v in HOST_CFG_ID.itervalues():
            proxy.config_trace(True, v)


def _configure_logging(queue, root_path):
    h = QueueHandler(queue) # Just the one handler needed
    root = logging.getLogger()
    root.addHandler(h)
    root.setLevel(logging.DEBUG)     
    log_path = os.path.join(root_path, 'log')
    
    try: 
        if not os.path.isdir(log_path): 
            os.mkdir(log_path)
        log_file_path = log_path + "\\" + TIME_STAMP + "_MotionWise-PMT-log"
    except:    
        log_file_path = None # invalid path
    
    return log_file_path

    
def main(args):
    try:
        try:
            pred = lambda x: 'log' in x and args.__getattribute__(x)
            log_level = [a[4:].upper() for a in args.__dict__ if pred(a)][0]
        except IndexError: 
            log_level = 'WARN'
        log_level = getattr(logging, log_level)
        queue = multiprocessing.Queue(-1)
        log_file_path = _configure_logging(queue, args.out_path)
        log_proc = multiprocessing.Process(target=log_listener, 
                    args=(queue, log_level, log_file_path,))
        log_proc.start()
        if not os.path.isdir(args.out_path): 
            logger.error("$output folder is not a valid directory\n")
            return 
        if args.pcap_file and not os.path.isfile(args.pcap_file): 
            logger.error('$pcap file not found')
            return
        
        host_str = args.host.upper()
        proxy  = Proxy(args)
        logger.info("$cv{}, IF-Set {}".format(args.version, proxy.get_IFSET()))
        logger.info("$f{}".format(' '.join(sys.argv)))
        if args.list_runnables:
            host_full = pm_measurement.HOSTS[args.host.upper()]['name']
            m = proxy.ra_model
            rnbls = [v for k,v in m.id_to_runnable.iteritems() if 
                     m.swc_to_host.get(m.runnable_to_swc[k],'') == host_full]
            for r in sorted(rnbls): print (r)
            return
              
        ra_model = proxy.get_ra_model()
        client = Client(ra_model, proxy.child_conn, args, queue)
        rnbl_task_map = FP.parse_schedule_generation_info_file \
            (args.__dict__["{}_sched_info".format(host_str.lower())])
        config = _get_trace_config(ra_model, args.runnables, rnbl_task_map)
        if host_str == 'APH':
            # for APH static task id to name mapping is available
            for k, v in FP.load_aph_task_map(args.aph_taskmap1, args.aph_taskmap2).iteritems():
                config['task_name_id'][v['name']] = k
         
        if args.csv_file:
            client.start()
        else:
            proxy.init()
            if args.pcap_file is not None: 
                # replay the given pcap file
                proxy.replay_config(args.pcap_file, "offline")
                client.start()
                proxy.replay_start(0)
            else:
                if args.store_pcap:  
                    pcap_path = os.path.join(args.out_path, "pcap")
                    if not os.path.isdir(pcap_path): os.mkdir(pcap_path)
                    pcap_path = os.path.join(pcap_path, '{}_MotionWise-PMT_{}.pcap'.
                                             format(TIME_STAMP, host_str))
                    proxy.log_config(pcap_path)
                
                logger.info("$cremote-access started")
                if not args.startup:
                    # if not in startup mode - disable tracing for all hosts 
                    # to silence them during subsequent configuration of 
                    # tracing framework
                    for k,i in HOST_CFG_ID.iteritems():
                        logger.debug("disabled tracing for {}({})".format(k,i))
                        proxy.config_trace(False, i)
                        proxy.config_trace_set_trigger(0x00, i)
                        
                proxy.receiving_start(0.5)
                if args.store_pcap: proxy.log_start()
                
                if args.startup:
                    time.sleep(0.1) # wait to see if MotionWise is already running
                    if proxy.startup_finished: 
                        logger.error("$cMotionWise is already running: "
                            "no startup measurement possible")
                        client.flush_pipe() # flushes the pipe
                        raise KeyboardInterrupt    
                    logger.info("$cstartup mode: power up the MotionWise")
                      
                    # wait for startup to be over before configure tracing
                    wait_start = time.time()
                    while not proxy.startup_finished:
                        if (time.time() - wait_start) > 40:
                            logger.error("$cno events received")
                            return 
                        time.sleep(0.1)

                client.start()
                 
                m = _req_task_name_id_mapping(proxy, host_str)
                for k,v in m.iteritems(): 
                    config['task_name_id'][k] = v
 
                _app_trace_config(proxy, host_str, config, args.trace_drivers)
                proxy.config_trace(True, HOST_CFG_ID[host_str])
 
            while True:
                if proxy.parent_conn.poll():
                    cmd = proxy.parent_conn.recv()
                    if cmd == "EOF": break
                else:
                    time.sleep(0.1)     
    except KeyboardInterrupt:
        pass
    finally: 
        if 'proxy' in locals():
            if args.store_pcap: proxy.log_stop(1)
            if args.pcap_file: proxy.replay_abort()
            _clean_up(proxy, host_str, args.csv_file or args.list_runnables)
        if 'client' in locals():
            if client.is_alive():
                client.join()
            logger.info("$clog file written to %s\\log" % args.out_path)
        queue.put_nowait(None)
        log_proc.join()


__all__ = []
__version__ = version()
__doc__ = """Script for MotionWise performance measurement"""


if __name__ == "__main__" :

    description = """\
This script computes several performance indicators for a specified host by  
instrumenting the tracing output of the MotionWise. As output it generates multiple 
CSV-files, one for each monitored entity, containing following measurements:

+------------------------+------------------------+---------------------------+
|                        |  Provided Measurement  |          Entities         |
|       Indicator        +------+-----+-----+-----+------------+------+-------+
|                        | Min  | Max | Avg | Cnt | Runnable   | Task | Other |
|                        |      |     |     |     | and Driver |      |       |
+------------------------+------+-----+-----+-----+------------+------+-------+
|Cyclic activation time  |   x  |  x  |  x  |  x  |      x     |      |       |
+------------------------+------+-----+-----+-----+------------+------+-------+
|Netto CPU time          |   x  |  x  |  x  |  x  |      x     |      |       |
+------------------------+------+-----+-----+-----+------------+------+-------+
|Gross CPU time          |   x  |  x  |  x  |  x  |      x     |      |       |
+------------------------+------+-----+-----+-----+------------+------+-------+
|Netto CPU usage         |   x  |  x  |  x  |  x  |      x     |   x  |       |
+------------------------+------+-----+-----+-----+------------+------+-------+
|Netto CPU budget usage  |   x  |  x  |  x  |  x  |      x     |      |       |
+------------------------+------+-----+-----+-----+------------+------+-------+
|RAM stack usage         |      |  x  |     |  x  |            |   x  |       |
+------------------------+------+-----+-----+-----+------------+------+-------+
|Checkpoint timing       |      |     |     |     |            |      |   x   |
+------------------------+------+-----+-----+-----+------------+------+-------+

Indicators:
- Netto CPU time: amount of time for which the CPU was used for processing a 
  runnable. The time is measured in us. Note that the provided time does not  
  exclude preemptions due to interrupt routines. 
- Gross CPU time: amount of time a runnable needed to finish with its execution. 
  It includes the time the runnable was preempted by other executables. The time 
  is measured in us.  
- Cylic activation time (period): time between to consecutive activations of the 
  same runnable. The time is measured in us.
- Netto CPU usage: netto CPU time as percentage of CPU's capacity.
- Netto CPU budget usage: netto CPU time as percentage of the runnable's 
  scheduled time budget.
- RAM stack usage: the peak size a task's stack in bytes.
- Checkpoint timing: list of received checkpoint events during startup and
  shutdown. 

Measurements:
- cnt: number of observed in a measurement session
- min: minimum of observed value in a measurement session
- max: maximum of observed value in a measurement session
- avg: average over all observed values in a measurement session

For every measurement session a log file and an aggregated CSV-file is created, 
which, in addition to an overview of the CPU load of the individual cores, 
provides information about the number of lost tracing events, detected trace 
event errors and ZGT errors. If the total number of lost events is high try to 
disable tracing for runnable which do not need to be measured. 

The script supports an on-line as well as an off-line mode. In the off-line mode 
a recorded pcap-file can be replayed. 

For more information please take a look in the arguments description below. The
following examples outline the basic usage of this script:

    Measure Application Host with drivers:
        MotionWise_Perf.py --host APH --trace-drivers
        
    Disable tracing for all runnables but ROBFmain and RMBFmain:
        MotionWise_Perf.py --host SSH --r ROBFmain RMBFmain 
        
    Measure startup on SRH and force MS-Excel compatibility of output files:
        MotionWise_Perf.py --host SRH --startup --msexcel-compat
    """
    
    parser = argparse.ArgumentParser \
        (formatter_class=argparse.RawDescriptionHelpFormatter
        , description=textwrap.dedent(description))
    required = parser.add_argument_group('required arguments')
    required.add_argument \
        ("--host"
        , dest="host"
        , required=True 
        , choices=["SSH", "ssh", "SRH", "srh", "APH", "aph"]
        , help="name of MotionWise-host for which the performance shall be measured")
    parser.add_argument \
        ("-v", "--version"
        , action="version"
        , version="MotionWise_Perf.py v{}, RA.py v{}".format(version(), ra_ver))
    parser.add_argument \
        ("--pcap-file" 
        , help="path to pcap-file which shall be replayed. The tool is started "
          "in an offline mode. No connection to the MotionWise is needed")
    parser.add_argument("--csv-file"
        , help=argparse.SUPPRESS)
    parser.add_argument \
        ("-o", "--output-dir"
        , dest="out_path"
        , default=os.path.dirname(os.path.abspath (__file__))
        , help="directory in which the folders for the generated files are "
          "located. If non is defined output will be written to %(default)s\\ "
          "[output|log]")
    parser.add_argument \
        ("--aph-taskmap1"
         , dest="aph_taskmap1"
         , default=APH_TASKMAP1
         , help="Path to Os_Types_Lcfg.h file containing for task IDs to task name "
                "names for APH. If none is given mapping is loaded from "
                "%(default)s")
    parser.add_argument \
        ("--aph-taskmap2"
         , dest="aph_taskmap2"
         , default=APH_TASKMAP2
         , help="Path to ApplicationHost_Os_ecuc.arxml file containing mapping for task name to OsCore "
                "names for APH. If none is given mapping is loaded from "
                "%(default)s")
    parser.add_argument \
        ( "--runnables"
        , "-r"
        , default=["all"]
        , nargs="+"
        , dest="runnables"
        , help="Select the runnables for which tracing shall be enabled. "
          "Runnables can be defined by giving their name or numeric identifier."
          " Using 'all' selects all SW-Cs. Default value is [%(default)s].")
    parser.add_argument  \
        ("--output-trace-events-off" 
        , action="store_true"
        , help="file output/YYYY-MM-DD_HH-MM-SS_MotionWise-PMT_trace-events.csv "
          "will not be created")
    parser.add_argument \
        ("--startup"
        , action='store_true'
        , help='Measure startup: 1) stop the MotionWise 2) start MotionWise_Perf.py '
          '3) wait until message "startup mode: power up the MotionWise" is '
          'displayed and proceed as indicated')
    parser.add_argument \
        ("--trace-drivers"
        , action='store_true'
        , help="enables trace-events for driver measurements. Default value "
          "is [%(default)s].")
    parser.add_argument \
        ("--msexcel-compat"
        , action="store_true"
        , help="Output CSV files will be saved with additional meta-"
          "information for facilitating automatic import in Microsoft Excel.")
    parser.add_argument \
        ("--trace-statistics"
        , action="store_true"
        , help="In addition to statistical analysis summary files, statistical "
          "analysis trace files will be created for tasks, runnables and "
          "drivers. Each contains a trace of statistical measurements computed "
          "at a regular interval of one second.")
    parser.add_argument \
        ("--store-pcap" 
        , action="store_true"
        , help="The measurement session is recorded to a pcap file. The "
          "file is stored in the output directory in the subfolder pcap.")
    parser.add_argument \
        ("--list-runnables", "-lr"
        , action="store_true"
        , help=argparse.SUPPRESS)
    parser.add_argument \
        ( "--aph-driver-ids"
        , dest="aph_driver_ids"
        , default= APH_DRIVER_ID
        , help=argparse.SUPPRESS)
    parser.add_argument \
        ( "--aph-sched-info"
        , dest="aph_sched_info"
        , default= APH_SCHED_INFO
        , help=argparse.SUPPRESS)
    parser.add_argument \
        ( "--ssh-sched-info"
        , dest="ssh_sched_info"
        , default= SSH_SCHED_INFO
        , help=argparse.SUPPRESS)
    parser.add_argument \
        ( "--srh-sched-info"
        , dest="srh_sched_info"
        , default = SRH_SCHED_INFO
        , help    = argparse.SUPPRESS
        )
    parser.add_argument \
        ( "--sw-layers"
        , default = SW_LAYERS_MAP
        , help=argparse.SUPPRESS)
    group2 = parser.add_mutually_exclusive_group()
    group2.add_argument("--log-error"
        , action="store_true"
        , help="sets the log level of the MotionWise_Perf script to 'error'. Only "
          "fatal errors are logged which cause the tool to crash. Note that "
          "this option does not set the log level of the MotionWise logging "
          "framework.")
    group2.add_argument("--log-warning"
        , action="store_true"
        , help="sets the log level of the MotionWise_Perf script to 'warning'. Same "
          "as log level 'error' but additionally logs anomalies which does not "
          "impede the correct execution of the script. This is the default log " 
          "level. Note that this option does not set the log level of the MotionWise "
          "logging framework.")
    group2.add_argument("--log-info"
        , action="store_true"
        , help="sets log level of the MotionWise_Perf script to 'info'. Same as log "
          "level 'warning' but additionally logs messages printed by the "
          "program and internal information which is not otherwise provided in "
          "other output. Note that this option does not set the log level of "
          "the MotionWise logging framework.")
    group2.add_argument("--log-debug"
        , action="store_true"
        , help="sets log level to 'debug'. Maximum verbosity to be used for "
          "development and debugging purposes. Note that this option does not "
          "set the log level of the MotionWise logging framework.")
    args = parser.parse_args() 
    args.__dict__['version'] = version()
    main(args)
