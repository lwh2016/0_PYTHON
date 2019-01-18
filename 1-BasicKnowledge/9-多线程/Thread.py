# 多线程和多进程最大的不同在于，多进程中，同一个变量，各自有一份拷贝存在于每个进程中，互不影响，而多线程中，所有变量都由所有线程共享
import threading
import time


def loop():
    st = time.time()
    print('Current Thread named %s' % threading.current_thread().name)
    for i in range(5):
        print('Current Thread named %s >>> %d' %
              (threading.current_thread().name, i))
    print('Current Thread  %s ended' % threading.current_thread().name)
    et = time.time()
    print('Current Thread  %s cost %f' % (threading.current_thread().name,
                                          (et - st)))


def main():
    st = time.time()
    t = threading.Thread(target=loop, name='LoopThread')
    print('Current Thread named %s' % threading.current_thread().name)
    t.start()
    t.join()
    print('Current Thread  %s ended' % threading.current_thread().name)
    et = time.time()
    print('Current Thread  %s cost %f' % (threading.current_thread().name,
                                          (et - st)))


if __name__ == '__main__':
    main()
