def num(maxNum):
    n = 2
    while n < maxNum:
        yield n
        n += 1


# 对于这种需要有2个参数输入，但是按照filter语法只能输入一个的函数，可以使用下面这种形式
def isPrime(n):
    def f(x):
        return x % n > 0

    return f
    # 下面这种写法等同于上面
    # return lambda x: x % n != 0


def Prime(maxNum):
    it = num(maxNum)
    while True:
        n = next(it)
        yield n
        it = filter(isPrime(n), it)


def main():
    for i in Prime(20):
        print(i)


if __name__ == '__main__':
    main()
