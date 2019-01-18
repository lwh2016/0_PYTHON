class LNode:
    def __init__(self, elem, next_=None):
        self.elem = elem
        self.next = next_


class LinkedListUnderflow(ValueError):
    pass


class SLList:
    def __init__(self):
        self._head = None  # 表头指针

    def is_empty(self):
        return self._head is None

    # 表前插入一个新的元素,O(1)
    def prepend(self, elem):
        self._head = LNode(elem, self._head)

    # 表前删除一个元素,O(1)
    def pop(self):
        if self._head is None:
            raise LinkedListUnderflow("Empty List")
        e = self._head.elem
        self._head = self._head.next
        return e

    # 表后插入一个新的元素
    def append(self, elem):
        if self._head is None:
            self._head = LNode(elem)
        else:
            p = self._head
            while p.next is not None:
                p = p.next
            p.next = LNode(elem)

    # 表后删除一个元素
    def pop_last(self):
        if self._head is None:
            raise LinkedListUnderflow("Empty List")
        elif self._head.next is None:
            e = self._head.elem
            self._head = None
        else:
            p = self._head
            while p.next.next is not None:
                p = p.next
            e = p.next.elem
            p.next = None
        return e

    def find(self, preb):
        if self._head is None:
            raise LinkedListUnderflow("Empty List")
        else:
            p = self._head
            while p is not None:
                if preb(p.elem):
                    return p.elem
                p = p.next

    def printall(self):
        if self._head is None:
            raise LinkedListUnderflow("Empty List")
        else:
            p = self._head
            while p is not None:
                print(p.elem, end='')
                if p.next is not None:
                    print(', ', end='')
                p = p.next
            print('')

    # 表元素遍历迭代器
    def elements(self):
        if self._head is None:
            raise LinkedListUnderflow("Empty List")
        else:
            p = self._head
            while p is not None:
                yield p.elem
                p = p.next

    # 表元素过滤迭代器
    def filter_elem(self, proc):
        if self._head is None:
            raise LinkedListUnderflow("Empty List")
        else:
            p = self._head
            while p is not None:
                if proc(p.elem):
                    yield p.elem
                p = p.next


# 增加一个指向表尾的指针_rear
class SLListR(SLList):
    def __init__(self):
        SLList.__init__(self)
        self._rear = None

    # 表前插入一个新的元素,O(1)
    def prepend(self, elem):
        if self._head is None:
            self._head = LNode(elem, self._head)
            self._rear = self._head
        else:
            self._head = LNode(elem, self._head)

    # 表后插入一个新的元素
    def append(self, elem):
        if self._head is None:
            self._head = LNode(elem, self._head)
            self._rear = self._head
        else:
            p = self._rear
            p.next = LNode(elem, None)
            self._rear = p.next

    # 表后删除一个元素
    def pop_last(self):
        if self._head is None:
            raise LinkedListUnderflow("Empty List")
        elif self._head.next is None:
            e = self._head.elem
            self._head = None
            self._rear = None
        else:
            e = self._rear.elem
            p = self._head
            while p.next.next is not None:
                p = p.next
            self._rear = p
        return e


# 循环单链表，_head 指针一直指着表尾部
class CSLList(SLList):

    # 表前插入一个新的元素,O(1)
    def prepend(self, elem):
        p = LNode(elem)
        if self._head is None:
            p.next = p
            self._head = p
        else:
            p.next = self._head.next
            self._head.next = p

    # 表前删除一个元素,O(1)
    def pop(self):
        if self._head is None:
            raise LinkedListUnderflow("Empty List")
        p = self._head.next
        if p is self._head:
            self._head = None
        else:
            self._head.next = p.next
        return p.elem

    # 表后插入一个新的元素
    def append(self, elem):
        p = LNode(elem)
        if self._head is None:
            p.next = p
            self._head = p
        else:
            pp = self._head
            p.next = self._head.next
            self._head = p
            pp.next = p

    # 表后删除一个元素
    def pop_last(self):
        if self._head is None:
            raise LinkedListUnderflow("Empty List")
        p = self._head
        if p is self._head.next:  # 只有一个节点
            self._head = None
        else:
            pp = self._head.next
            while pp.next is not self._head:
                pp = pp.next
            pp.next = self._head.next
            self._head = pp
        return p.elem

    # 表元素遍历迭代器
    def elements(self):
        if self._head is None:
            raise LinkedListUnderflow("Empty List")
        elif self._head.next == self._head:
            yield self._head.elem
        else:
            p = self._head.next
            while p is not None:
                yield p.elem
                p = p.next
                if p == self._head.next:
                    break

    # 表元素过滤迭代器
    def filter_elem(self, proc):
        if self._head is None:
            raise LinkedListUnderflow("Empty List")
        else:
            p = self._head.next
            while p is not None:
                if proc(p.elem):
                    yield p.elem
                p = p.next
                if p == self._head.next:
                    break

    # 表元素全打印
    def printall(self):
        if self._head is None:
            raise LinkedListUnderflow("Empty List")
        elif self._head.next == self._head:
            print(self._head.elem, end='')
        else:
            p = self._head.next
            while p is not None:
                print(p.elem, end='')
                p = p.next
                if p == self._head.next:
                    break
                else:
                    print(', ', end='')
            print('')

    # 查找表中第一个满足条件的元素并返回
    def find(self, preb):
        if self._head is None:
            raise LinkedListUnderflow("Empty List")
        else:
            p = self._head.next
            while p is not None:
                if preb(p.elem):
                    return p.elem
                p = p.next
                if p == self._head.next:
                    break


def main():
    # # 简单单链表 测试
    # mList = SLList()
    # # 带表尾指针的单链表 测试
    # mList = SLListR()
    # 循环单链表 测试
    mList = CSLList()
    for i in range(1, 11):
        mList.prepend(i)
    for i in range(11, 20):
        mList.append(i)
    mList.printall()

    # mList.pop()
    # mList.printall()
    # mList.pop_last()
    # mList.printall()
    # for i in mList.elements():
    #     print(i)

    def pr(n):
        return n % 2 == 0

    ll = list(mList.filter_elem(pr))
    print(ll)

    def pr2(n):
        return n > 20 == 0

    select_n = mList.find(pr2)
    print(select_n)


if __name__ == '__main__':
    main()
