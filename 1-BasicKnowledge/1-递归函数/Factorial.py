# -*- coding: utf-8 -*-
# Factorial.py
# @author guokonghui
# @description
# @created Fri Jan 18 2019 17:08:52 GMT+0800 (中国标准时间)
# @last-modified Fri Jan 18 2019 20:16:44 GMT+0800 (中国标准时间)
#


def factorial(n):
    result = 1
    if n < 0:
        print("Negative numbers cannot carry out factorial operations.")
        result = 0
    elif (1 == n) | (0 == n):
        result = 1
    else:
        result = n * factorial(n - 1)
    return result


def main():
    r = factorial(5)
    print(r)


if __name__ == '__main__':
    main()
