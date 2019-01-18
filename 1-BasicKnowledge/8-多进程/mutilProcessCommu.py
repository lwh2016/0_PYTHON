from multiprocessing import Process, Queue
import os
import time
import random


def p_write(q):
    print('Process Write %s start' % os.getpid())
    for value in range(5):
        print('Write %s to Queue' % value)
        q.put(value)
        time.sleep(random.random())


def p_read(q):
    print('Process Read %s start' % os.getpid())
    while not q.empty():
        value = q.get(True)
        print('Read value %s from Queue' % value)


def main():
    Q = Queue()
    st = time.time()
    pw = Process(target=p_write, args=(Q, ))
    pr = Process(target=p_read, args=(Q, ))
    pw.start()
    pw.join()
    pr.start()
    pr.join()
    et = time.time()
    print('Main Process cost %f seconds' % (et - st))


if __name__ == '__main__':
    main()
