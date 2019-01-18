def consumer():
    r = ''
    while True:
        n = yield r
        if not n:
            return
        print('Consume: %d' % n)
        r = 'OK'


def producer(c):
    c.send(None)
    n = 0
    while n < 5:
        n = n + 1
        print('Produce: %d' % n)
        rr = c.send(n)
        print('Consume Returns: %s' % rr)
    c.close()


def main():
    c = consumer()
    producer(c)


if __name__ == '__main__':
    main()