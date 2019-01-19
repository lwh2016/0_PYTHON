# -*- coding: utf-8 -*-
# HanoiTower.py
# @author guokonghui
# @description
# @created Sat Jan 19 2019 20:57:40 GMT+0800 (CST)
# @last-modified Sat Jan 19 2019 22:21:50 GMT+0800 (CST)
#


def Hanoi(n, sor, mid, des):
    if 1 == n:
        print(sor, '——>', des)
    else:
        Hanoi(n - 1, sor, des, mid)
        print(sor, '——>', des)
        Hanoi(n - 1, mid, sor, des)


def main():
    Hanoi(3, 'A', 'B', 'C')


if __name__ == '__main__':
    main()
