def naiveMatching(objStr, modeStr):
    l_obj = len(objStr)
    l_mod = len(modeStr)
    matchCount = 0
    matchStr = []
    i, j = 0, 0
    while i < l_mod and j < l_obj:
        if modeStr[i] == objStr[j]:
            i, j = i + 1, j + 1
        else:
            i, j = 0, j - i + 1
        if i == l_mod:
            matchCount = matchCount + 1
            matchStr.append(objStr[j - i:j - i + l_mod])
            i = 0
    return matchCount, matchStr


def main():
    obj = 'abcaabcbcdabc'
    mod = 'abc'
    c, s = naiveMatching(obj, mod)
    print(c, s)
    first_index = obj.find(mod)
    print(first_index)


if __name__ == '__main__':
    main()
