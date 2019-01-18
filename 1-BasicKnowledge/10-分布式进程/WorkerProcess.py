#!/usr/bin/python3
# -*- coding: utf-8 -*-
from multiprocessing.managers import BaseManager
import time
import queue


def do_task(n):
    return n * n


class QueueManger(BaseManager):
    pass


QueueManger.register('get_task_queue')
QueueManger.register('get_result_queue')

master_addr = '127.0.0.1'

worker_manger = QueueManger(address=(master_addr, 5000), authkey=b'12345')
worker_manger.connect()

queue_task = worker_manger.get_task_queue()
queue_result = worker_manger.get_result_queue()

for i in range(10):
    try:
        print('get task (%d) from queue_task' % i)
        t = queue_task.get(timeout=1)
        r = do_task(t)
        print('Put result of task (%s) : %s to queue_result' % (t, r))
        time.sleep(1)
        queue_result.put(r)

    except Queue.Empty:
        print('Queue is Empty')
