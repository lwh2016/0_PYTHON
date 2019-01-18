from multiprocessing.managers import BaseManager
import queue

task_queue = queue.Queue()
result_queue = queue.Queue()


class QueueManger(BaseManager):
    pass


QueueManger.register('get_task_queue', callable=lambda: task_queue)
QueueManger.register('get_result_queue', callable=lambda: result_queue)

master_manger = QueueManger(address=('', 5000), authkey=b'12345')
master_manger.start()
queue_task = master_manger.get_task_queue()
queue_result = master_manger.get_result_queue()

for i in range(10):
    print('Put task (%d) to queue_task' % i)
    queue_task.put(i)

for i in range(10):
    print('Get result (%d) from queue_result' % i)
    r = queue_result.get(timeout=20)
    print('The result of task (%d) is %s' % (i, r))

master_manger.shutdown()
