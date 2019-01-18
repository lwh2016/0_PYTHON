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
