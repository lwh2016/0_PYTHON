import threading
import time

balance = 0
lock = threading.Lock()


def change_it(n):
    global balance
    balance = balance + n
    balance = balance - n


def run(n):
    for i in range(100000):
        change_it(n)


def run_lock(n):
    for i in range(10000):
        lock.acquire()
        try:
            change_it(n)
        finally:
            lock.release()


def main():
    st = time.time()
    t1 = threading.Thread(target=run_lock, args=(5, ))
    t2 = threading.Thread(target=run_lock, args=(8, ))
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    print(balance)
    et = time.time()
    print('cost time: ', et - st)


if __name__ == '__main__':
    main()
