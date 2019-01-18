from functools import reduce


def str2num(ch):
    numdict = {
        '1': 1,
        '2': 2,
        '3': 3,
        '4': 4,
        '5': 5,
        '6': 6,
        '7': 7,
        '8': 8,
        '9': 9,
        '0': 0,
    }
    return numdict[ch]


def str2int(a, b):
    return a * 10 + b


def str2float(strNum):
    if '.' in strNum:
        point_index = strNum.index('.')
        intNum = reduce(
            str2int,
            map(str2num, strNum[:point_index] + strNum[point_index + 1:]))

        return intNum / 10**(len(strNum) - point_index - 1)
    else:
        print('input error')


def main():
    print(str2float('123456.7'))


if __name__ == '__main__':
    main()
