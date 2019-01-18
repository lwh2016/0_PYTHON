#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Server.py
# @author guokonghui
# @description
# @created Wed Aug 29 2018 20:01:07 GMT+0800 (CST)
# @last-modified Wed Aug 29 2018 20:01:07 GMT+0800 (CST)
#

import socket
import threading
import time

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

s.bind(('127.0.0.1', 8004))
s.listen(5)


def tcplink(sock, addr):
    print('Accept a new connect from %s:%s...' % addr)
    sock.send(b'Welcome!')
    while True:
        data = sock.recv(1024)
        time.sleep(1)
        if not data or data.decode('utf-8') == 'exit':
            break
        sock.send(('Hello, %s!' % data.decode('utf-8')).encode('utf-8'))
    sock.close()
    print('Connect from %s:%s is closed' % addr)


while True:
    sock, addr = s.accept()
    t = threading.Thread(target=tcplink, args=(sock, addr))
    t.start()
