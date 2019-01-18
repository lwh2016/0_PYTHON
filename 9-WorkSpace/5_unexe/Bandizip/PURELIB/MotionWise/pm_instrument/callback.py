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
#    23-May-2015 (GWI) Creation
# --

__version__ = "$Revision: 43500 $".split()[1]


class Callback(object):
    task_id_name_callback_fun = [] 
    sequence_error_callback_fun = []
    checkpoint_callback_fun = []
    pm_stack_peak_callback_fun = []
    pm_runtime_callback_fun = []
    state_error_callback_fun = []
    rnbl_gross_rt_callback_fun = []
    rnbl_netto_rt_callback_fun = []
    rnbl_activation_callback_fun = []
    rnbl_overhead_callback_fun = []
    driver_gross_rt_callback_fun = []
    driver_netto_rt_callback_fun = []
    driver_activation_callback_fun = []
    task_switch_callback_fun = []
    event_received_callback_fun = []
    zgt_correction_callback_fun = []
    zgt_error_callback_fun = []


def invoke(name, signal):
    for func in Callback.__dict__[name]:
        try: 
            func(**signal)
        except TypeError, e:
            if "ARGUMENT" in e.message.upper():
                func(signal)
            else:
                raise


def attach(name, fun):
    if not fun in Callback.__dict__[name]:
        Callback.__dict__[name].append(fun)


if __name__ == '__main__':
    pass