from functools import reduce

# map
l = list(range(1, 10))


def fact(n):
    result = 1
    if (1 == n) | (1 == 0):
        result = 1
    else:
        result = n * fact(n - 1)
    return result


# reduce
def addsum(a, b):
    return a + b


# filter
def isOdd(n):
    return n % 2 == 1


def main():
    l_fact = map(fact, l)
    for e in l_fact:
        print(e)
    l_addsum = reduce(addsum, l)
    print(l_addsum)
    l_isOdd = filter(isOdd, l)
    for e in l_isOdd:
        print(e)


if __name__ == '__main__':
    main()
