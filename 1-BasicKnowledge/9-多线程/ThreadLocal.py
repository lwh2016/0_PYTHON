import threading

thread_local_std = threading.local()


def HomeWork(std):
    thread_local_std.std = std
    MathWork()
    ChineseWork()


def HouseWork(std):
    thread_local_std.std = std
    Sweep()
    Clean()


def MathWork():
    std = thread_local_std.std
    print('%s do mathWork in %s' % (std, threading.current_thread().name))


def ChineseWork():
    std = thread_local_std.std
    print('%s do ChineseWork in %s' % (std, threading.current_thread().name))


def Sweep():
    std = thread_local_std.std
    print('%s do Sweep in %s' % (std, threading.current_thread().name))


def Clean():
    std = thread_local_std.std
    print('%s do Clean in %s' % (std, threading.current_thread().name))


def main():
    print('Main Thread: %s  start' % threading.current_thread().name)
    HomeWork_Thread = threading.Thread(
        target=HomeWork, args=('Mike', ), name='MikeHomeWork')
    HouseWork_Thread = threading.Thread(
        target=HouseWork, args=('Sam', ), name='SamHouseWork')
    HomeWork_Thread.start()
    HouseWork_Thread.start()
    HomeWork_Thread.join()
    HouseWork_Thread.join()
    print('Main Thread: %s  end' % threading.current_thread().name)


if __name__ == '__main__':
    main()
