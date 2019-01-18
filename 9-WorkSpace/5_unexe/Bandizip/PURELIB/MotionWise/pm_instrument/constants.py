'''
Created on May 23, 2015

@author: wiesmann
'''

__version__ = "$Revision: 44475 $".split()[1]

EVENT_MAP = { 0: 'start_runnable', 1: 'stop_runnable', 2: 'task_switch'
            , 3: 'interrupt', 4: 'start_driver', 5: 'stop_driver'
            , 6: 'state_change', 7: 'checkpoint', 8: 'input_signal'
            , 9: 'zgt_correction', 10: 'pm_stack_peak', 11: 'pm_runtime'
            , 12: 'pm_heap', 13: 'pm_r_nettime', 0xFF: 'task_id_name' }

