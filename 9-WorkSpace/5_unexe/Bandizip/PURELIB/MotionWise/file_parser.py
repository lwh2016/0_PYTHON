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
#    23-June-2015 (GWI) Creation
# --

import re
import csv
import xml.etree.ElementTree as ET


def parse_entity_sw_layers(sw_layers_file):
    sep = b","
    quote = b"#"
    regex = re.compile(r"#HEADER[ ]*")
    out = {'APH': {}, 'SSH': {}, 'SRH': {}}
    
    with open(sw_layers_file, 'rb') as csvfile: 
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
        
        reader = csv.DictReader(lines[start:], delimiter=sep, quotechar=quote)    
        for row in reader: out[row['Host']][row['Entity_name']] = row
     
    return out


def parse_schedule_generation_info_file(info_file):
    """
    @brief Parses a schedule generation info file
    
    Parses a schedule generation info file which is provided by the task 
    scheduling tool. It contains runnable related data such as WCET, period
    jitter and the name of the owner task. Returns a map with runnable names
    as keys. 
    
    @param info_file: path to schedule generation info file
    @return: map with runnable names as keys  
    """
    sep=b';'
    quote=b'#'
    out = {}

    try:
        csvfile = open(info_file, 'rb')
    except:
        pass
    else:
        with csvfile:
            cid = None
            cores = {}
            lines = csvfile.readlines()
            
            for (i,l) in enumerate(lines): 
                if l.upper().startswith('CORE'):
                    cid = int(l.split(':')[1].strip(' '))
                    cores[cid] = {}
                if 'macrotick' in l: 
                    cores[cid]['macrotick'] = int(l.split(';')[2])
                if l.startswith('SWC'):
                    cores[cid]['start'] = i
                if l.startswith('---load---'): 
                    cores[cid]['end'] = i
            
            for (c, v) in cores.items():
                reader = csv.DictReader(lines[v['start']:v['end']]
                            , delimiter=sep, quotechar=quote)  
                for row in reader:
                    mt = float(v['macrotick'])
                    wcet = float(row['wcet[ticks]'].replace(',','.'))
                    rnbl = out.get(row['runnable'],{})
                    rnbl['wcet'] = wcet * mt
                    rnbl['task'] = row['task_name']
                    rnbl['period'] = float(row['period[ticks]']) * mt
                    rnbl['core'] = int(c)
                    out[row['runnable']] = rnbl 
    return out

def get_core_model_pattern(os_types_file):
    core_model_enum_name = "ApplicationType"  # enum name in Os_Types_Lcfg.h file
    enum_found = False
    pattern_found = False

    with open(os_types_file, 'r') as f:
        s = f.readlines()
        # reverse file for easier enum parsing
        s.reverse()
        for line in s:
            if core_model_enum_name in line:
                enum_found = True
            if enum_found:
                # relevant info always before OS_APPID_COUNT member in enum
                if "count" in line.lower():
                    pattern_found = True
                elif pattern_found:
                    # remove everything that isn't the members name
                    pattern = line.replace(' ', '').split('=', 1)[0].rsplit("_", 1)[0]
                    break
    f.close()
    return pattern

def get_core_model_pattern(os_types_file):
    core_model_enum_name = "ApplicationType"  # enum name in Os_Types_Lcfg.h file
    enum_found = False
    pattern_found = False

    with open(os_types_file, 'r') as f:
        s = f.readlines()
        # reverse file for easier enum parsing
        s.reverse()
        for line in s:
            if core_model_enum_name in line:
                enum_found = True
            if enum_found:
                # relevant info always before OS_APPID_COUNT member in enum
                if "count" in line.lower():
                    pattern_found = True
                elif pattern_found:
                    # remove everything that isn't the members name
                    pattern = line.replace(' ', '').split('=', 1)[0].rsplit("_", 1)[0]
                    break
    f.close()
    return pattern


def load_aph_task_map(task_id_file, arxml_file):
    # Input argument has been changed by IECU-244
    out = {}            # output dict
    OsCore_list = []    # OsCore container
    # Define patterns
    ptr1 = re.compile(r'^(Task|IdleTask).*=.*[0-9]')  # pattern of regex
    ptr2 = re.compile(r'^(Task|IdleTask).*')  # pattern of regex
    OsCore_pattern = get_core_model_pattern(task_id_file)
    ptr3 = re.compile(r'^'+OsCore_pattern+'.*')  # pattern of OsCore 

    # parsing task id from file
    with open(task_id_file, 'r') as f:
        for line in f:
            m = re.match(ptr1, line.replace(' ', ''))
            if m:
                task_id = m.group().replace(' ', '').split('=')
                out[int(task_id[-1])] = {}
                out[int(task_id[-1])][task_id[0]] = None

    # parsing core assignment
    tree = ET.ElementTree()
    # define namesapce
    ns = {"ns": "http://autosar.org/schema/r4.0"}
    tree.parse(arxml_file)

    for node in tree.findall('.//ns:ECUC-CONTAINER-VALUE', namespaces=ns):
        # check OsCore container
        OsCore = node.find('./ns:SHORT-NAME', namespaces=ns).text
        m = re.match(ptr3, OsCore)
        if m:
            OsCore_list.append(OsCore)  # append OsCore name to list to verify
            for task_node in node.findall('.//ns:VALUE-REF', namespaces=ns):
                task_name = task_node.text.split('/')[-1]
                m = re.match(ptr2, task_name)
                if m:
                    # mapping core to task name
                    for k, v in out.iteritems():
                        if v.keys()[0] == task_name:
                            out[k] = {'core': int(OsCore[-1:]), 'name': task_name}

    # OsCore info. check in ApplicationHost_Os_ecuc.arxml
    if not len(OsCore_list):
        # show error if there is no matched pattern for OsCore in ApplicationHost_Os_ecuc.arxml
        print ('[Error] OsCore name({pattern}) is not found in {arxml}'.format(pattern=OsCore_pattern, arxml=arxml_file))
    return out


def load_driver_name_map(driver_map_file):
    out = {}
    try:
        f = open(driver_map_file, 'rb')
    except:
        raise
    else:
        with f:
            lines = f.readlines()
            for l in lines:
                l.strip(' ')
                elm = l.split(' ')
                try: 
                    if elm[1].startswith("DRVID_"):
                        out[int(elm[-1])] = elm[1][6:]
                except IndexError:
                    pass
    return out


__version__ = "$Revision: 38070 $".split()[1]
    
if __name__ == '__main__':
    cmp_map = parse_entity_sw_layers("..\\scripts\\entity_sw_layers.csv")
    print("")
