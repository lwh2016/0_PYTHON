#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Client.py
# @author guokonghui
# @description
# @created Wed Aug 29 2018 20:26:43 GMT+0800 (CST)
# @last-modified Wed Aug 29 2018 20:26:43 GMT+0800 (CST)
#

import socket

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
addr = ('127.0.0.1', 8004)
for i in [b'Alice', b'Mike', b'Sam']:
    s.sendto(i, addr)
    d = s.recv(1024)
    print(d.decode('utf-8'))
s.sendto(b'exit', addr)
s.close()

# s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# for data in [b'Michael', b'Tracy', b'Sarah']:
#     # 发送数据:
#     s.sendto(data, ('127.0.0.1', 8004))
#     # 接收数据:
#     print(s.recv(1024).decode('utf-8'))
# s.close()
