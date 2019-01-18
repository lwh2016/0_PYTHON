# 生成n以内的斐波那契数列
def fib(n):
    a = 1
    b = 1
    if n < 1:
        print('input number error')
    elif n < 3:
        yield b
    else:
        yield a
        while b < n:
            yield b
            c = a
            a = b
            b = b + c


# 生成斐波那契数列的前m项
def fibonacci(m):
    a = 1
    b = 1
    number = 0
    yield a
    number += 1
    while number < m:
        yield b
        number += 1
        c = a
        a = b
        b = b + c


def main():
    for i in fibonacci(10):
        print(i)


if __name__ == '__main__':
    main()
