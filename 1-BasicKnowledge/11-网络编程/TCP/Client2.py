#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Client.py
# @author guokonghui
# @description
# @created Wed Aug 29 2018 20:26:43 GMT+0800 (CST)
# @last-modified Wed Aug 29 2018 20:26:43 GMT+0800 (CST)
#

import socket

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('127.0.0.1', 8004))
d = s.recv(1024)
print(d.decode('utf-8'))
for i in [b'DaMing', b'XiaoHong', b'XiaoGang']:
    s.send(i)
    d = s.recv(1024)
    print(d.decode('utf-8'))
s.send(b'exit')
s.close()
