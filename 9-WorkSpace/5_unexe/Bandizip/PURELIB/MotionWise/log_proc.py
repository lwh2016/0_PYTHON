#!C:\Python27\python.exe

# Copyright (C) 2013 TTTech Computertechnik AG. All rights reserved
# Schoenbrunnerstrasse 7, A--1040 Wien, Austria. office@tttech.com
#
# ++
# Name
#    queue_handler.py
#
# Purpose
#    Script for MotionWise runtime measurement
#
# Authors
#
# Revision Dates
# --

import sys
import signal
import logging


class ConsoleFilter(logging.Filter):
    """
    Filters log events.
    """
    
    def filter(self, record):
        if record.msg[0:2] == '$c':
            record.msg = record.msg[2:]
            return True
        return False


def log_listener(queue, level, out_file):
    """
    This is the listener process top-level loop: wait for logging events
    (LogRecords)on the queue and handle them, quit when you get a None for a 
    LogRecord.
    """
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    detailed = logging.Formatter(datefmt='%Y-%m-%d,%H:%M:%S', 
        fmt='%(asctime)s.%(msecs)03d - [%(levelname)s]: %(message)s')
    console = logging.Formatter('[MotionWise_Perf]: %(message)s')
    root = logging.getLogger()
    
    # stream handler with console filter has to be added first since filter
    # changes record.msg
    sh = logging.StreamHandler(stream=sys.stdout)
    sh.addFilter(ConsoleFilter())
    sh.setFormatter(console)
    root.addHandler(sh)
    
    if out_file is not None: 
        fh = logging.FileHandler(out_file, 'a')
        fh.setFormatter(detailed)
        root.addHandler(fh)
    
    while True:
        try:
            record = queue.get()
            # We send this as a sentinel to tell the listener to quit.
            if record is None: 
                break
            logger = logging.getLogger(record.name)
            
            # $c -> record is written to console and file, level is ignored
            # $f -> record is written to file, level is ignored
            record.msg = str(record.msg)
            if record.levelno >= level or (record.msg[0:2] in ['$c', '$f']):
                if record.msg[0:2] == '$f':
                    record.msg = record.msg[2:]
                logger.handle(record) 
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            import traceback
            traceback.print_exc(file=sys.stderr)


class QueueHandler(logging.Handler):
    """
    This is a logging handler which sends events to a multiprocessing queue.
    
    The plan is to add it to Python 3.2, but this can be copy pasted into
    user code for use with earlier Python versions.
    """

    def __init__(self, queue):
        """
        Initialise an instance, using the passed queue.
        """
        logging.Handler.__init__(self)
        self.queue = queue
        
    def emit(self, record):
        """
        Emit a record.
        Writes the LogRecord to the queue.
        """
        try:
            ei = record.exc_info
            if ei:
                dummy = self.format(record) # just to get traceback text into record.exc_text
                record.exc_info = None  # not needed any more
            self.queue.put_nowait(record)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


__version__ = "$Revision: 80204 $".split()[1]

if __name__ == '__main__':
    pass
