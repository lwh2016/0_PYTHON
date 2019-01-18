def lazy_sum(*args):
    def sum():
        s = 0
        for i in args:
            s = s + i
        return s

    return sum


def lazy_fact(n):
    def fact():
        return n**3

    return fact


def main():
    # f = lazy_sum(1, 2, 3, 4, 5)  # 其实这里就可以理解为定义一个函数f，并且在定义f的时候放入了默认参数
    f = lazy_fact(3)
    print(f)
    print(f())


if __name__ == '__main__':
    main()
