class DLNode:
    def __init__(self, elem, prev=None, next_=None):
        self.elem = elem  # 本节点的元素值
        self.prev = prev  # 本节点指向其上一个相邻节点的指针
        self.next = next_  # 本节点指向下一个相邻节点的指针


class LinkedListUnderflow(ValueError):
    pass


class DLList(object):
    def __init__(self):
        self._head = None  # 表头指针
        self._rear = None

    def is_empty(self):
        return self._head is None

    def prepend(self, elem):
        p = DLNode(elem, None, self._head)
        if self._head is None:
            self._rear = p
        else:
            self._head.prev = p
        self._head = p

    def pop(self):
        if self._head is None:
            raise LinkedListUnderflow("Empty List")
        e = self._head.elem
        self._head = self._head.next
        if self._head is not None:
            self._head.prev = None
        return e

    def append(self, elem):
        p = DLNode(elem, self._rear, None)
        if self._head is None:
            self._head = p
        else:
            self._rear.next = p
        self._rear = p

    def pop_last(self):
        if self._head is None:
            raise LinkedListUnderflow("Empty List")
        e = self._rear.elem
        self._rear = self._rear.prev
        if self._rear is not None:
            self._rear.next = None
        else:
            self._head = None
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


class CDLList(DLList):  # 此处尾指针rear并没有什么用处，只要一个头指针head就够了
    def prepend(self, elem):
        p = DLNode(elem)
        if self._head is None:
            p.next = p
            p.prev = p
        else:
            p.prev = self._head.prev
            p.next = self._head
            self._head.prev.next = p
            self._head.prev = p
        self._head = p

    def pop(self):
        if self._head is None:
            raise LinkedListUnderflow("Empty List")
        e = self._head.elem
        self._head = self._head.next
        if self._head is self._head.prev:  # 只有一个节点
            self._head = None
        else:
            self._head.prev.prev.next = self._head
            self._head.prev = self._head.prev.prev
        return e

    def append(self, elem):
        p = DLNode(elem)
        if self._head is None:
            p.next = p
            p.prev = p
            self._head = p
        else:
            self._head.prev.next = p
            p.prev = self._head.prev
            p.next = self._head
            self._head.prev = p

    def pop_last(self):
        if self._head is None:
            raise LinkedListUnderflow("Empty List")
        else:
            e = self._head.prev.elem
            if self._head is self._head.prev:  # 只有一个节点
                self._head = None
            else:
                self._head.prev.prev.next = self._head
                self._head.prev = self._head.prev.prev

    # 表元素遍历迭代器
    def elements(self):
        if self._head is None:
            raise LinkedListUnderflow("Empty List")
        else:
            p = self._head
            while p is not None:
                yield p.elem
                if p is self._head.prev:
                    break
                p = p.next

    def printall(self):
        if self._head is None:
            raise LinkedListUnderflow("Empty List")
        else:
            p = self._head
            while p is not None:
                print(p.elem, end='')
                if p is not self._head.prev:
                    print(', ', end='')
                else:
                    break
                p = p.next
            print('')

    def find(self, preb):
        if self._head is None:
            raise LinkedListUnderflow("Empty List")
        else:
            p = self._head.next
            while p is not self._head:
                if preb(p.elem):
                    return p.elem
                p = p.next

    # 表元素过滤迭代器
    def filter_elem(self, proc):
        if self._head is None:
            raise LinkedListUnderflow("Empty List")
        else:
            p = self._head.next
            while p is not self._head:
                if proc(p.elem):
                    yield p.elem
                p = p.next


def main():
    # # 带首尾指针的双链表
    # mdList = DLList()
    # mdList.prepend(0)
    # mdList.append(99)
    # mdList.printall()
    # for i in range(11, 20):
    #     mdList.prepend(i)
    # for i in range(11):
    #     mdList.append(i)

    # ee = mdList.pop()
    # print(ee)
    # e = mdList.pop_last()
    # print(e)
    # print(list(mdList.elements()))

    # def pr(n):
    #     return n % 2 == 0

    # ll = mdList.find(pr)
    # print(ll)

    # ll = list(mdList.filter_elem(pr))
    # print(ll)

    # # 带头指针的循环双链表
    mcdList = CDLList()
    for i in range(11):
        mcdList.append(i)
    mcdList.prepend(99)
    # print(list(mcdList.elements()))

    mcdList.pop()
    mcdList.pop_last()
    mcdList.printall()

    def pr(n):
        return n % 2 == 0

    print(list(mcdList.elements()))
    n = mcdList.find(pr)
    print(n)
    ll = list(mcdList.filter_elem(pr))
    print(ll)


if __name__ == '__main__':
    main()
