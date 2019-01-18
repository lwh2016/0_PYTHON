def getnext(pattern):
    nextList = list(range(len(pattern)))
    nextList[0] = -1
    k = -1
    j = 0
    while j < len(pattern) - 1:
        if (k == -1) or (pattern[j] == pattern[k]):
            j += 1
            k += 1
            if pattern[j] == pattern[k]:
                nextList[j] = nextList[k]
            else:
                nextList[j] = k
        else:
            k = nextList[k]
    return nextList


def kmpMatch(pattern, target, nextList):
    len_p = len(pattern)
    len_t = len(target)
    matchCount = 0
    matchStr = []
    i = 0
    j = 0
    while i < len_t and j < len_p:
        if (target[i] == pattern[j]) or (j == -1):
            i += 1
            j += 1
        else:
            j = nextList[j]
        if j == len_p:
            matchCount += 1
            matchStr.append(target[i - len_p:i])
    return matchCount, matchStr


def main():
    modeStr = 'abbcabcaabbcaa'
    nextList = getnext(modeStr)
    print(nextList)

    # obj = 'ababcabcacbab'
    # mod = 'abcac'
    # nextList = getnext(mod)
    # c, s = kmpMatch(mod, obj, nextList)
    # print(c, s)


if __name__ == '__main__':
    main()
