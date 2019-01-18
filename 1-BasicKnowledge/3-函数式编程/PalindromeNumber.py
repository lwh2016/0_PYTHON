from functools import reduce


def isPalindrome(num):
    strNum = str(num)
    strNumRe = reversed(strNum)
    strNumRe = reduce(lambda a, b: a + b, strNumRe)

    return (num - int(strNumRe) == 0)


def natureNum(maxN):
    n = 0
    while n < maxN:
        yield n
        n += 1


def main():
    it = filter(isPalindrome, natureNum(100))
    for i in it:
        print(i)


if __name__ == '__main__':
    main()
