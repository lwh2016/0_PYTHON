import os

print('Process %s is running' % os.getpid())
pid = os.fork()
if pid == 0:
    print('I am Child Process %s is created by Father Process %s' %
          (os.getpid(),
           os.getppid()))  # getpid()返回当前进程的id，getppid()返回当前进程的父进程的id，
else:
    print(
        'I am Father Process %s created Child Process %s' % (os.getpid(), pid))
