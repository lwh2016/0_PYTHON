from multiprocessing import Pool
import os
import time
import random


def long_time_func(ProcessName):
    print('%s Child Process %s start' % (ProcessName, os.getpid()))
    start_time = time.time()
    time.sleep(random.random() * 10)
    end_time = time.time()
    print('%s Child Process (%s) cost (%f)s' % (ProcessName, os.getpid(),
                                                end_time - start_time))


def main():
    print('Main Process %s start' % os.getpid())
    st = time.time()
    p = Pool(5)
    # for i in range(5):
    #     p.apply_async(long_time_func, args=(i, ))

    # p.apply_async(long_time_func, args=(0, ))
    # p.apply_async(long_time_func, args=(1, ))
    # p.apply_async(long_time_func, args=(2, ))
    # p.apply_async(long_time_func, args=(3, ))
    # p.apply_async(long_time_func, args=(4, ))
    p.map(long_time_func, range(5))
    print('Waiting for all child Process done')
    p.close()
    p.join()
    print('All Child Process is done')
    et = time.time()
    print('Main Process cost %f' % (et - st))


if __name__ == '__main__':
    main()
