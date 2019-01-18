from multiprocessing import Process
import os


def func(args):
    print('I am Child Prcess named %s and my id is %s my Parent id is %s' %
          (args, os.getpid(), os.getppid()))


def main():
    print('Program is started')
    print('I am Parent Process %s' % os.getpid())
    cp = Process(target=func, args=('Cp Process', ))
    print('Child Process is started')
    cp.start()
    cp.join()
    print('Child Process is ended')


if __name__ == '__main__':
    main()
