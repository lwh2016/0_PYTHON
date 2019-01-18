#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Server.py
# @author guokonghui
# @description
# @created Wed Aug 29 2018 20:01:07 GMT+0800 (CST)
# @last-modified Wed Aug 29 2018 20:01:07 GMT+0800 (CST)
#

import socket

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

s.bind(('127.0.0.1', 8004))

while True:
    data, addr = s.recvfrom(1024)
    print('Received from %s:%s.' % addr)
    s.sendto(('Hello, %s!' % data.decode('utf-8')).encode('utf-8'), addr)
