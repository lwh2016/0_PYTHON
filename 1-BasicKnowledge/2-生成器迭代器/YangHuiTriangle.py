def triangle(rows):
    l = [1]
    ll = [1, 1]
    yield l
    r = 1
    while r < rows:
        yield ll
        tmp_l = ll
        ll = [1, 1]
        for i in range(len(tmp_l) - 1):
            ll.insert(i + 1, tmp_l[i] + tmp_l[i + 1])
        r += 1


def main():
    for l in triangle(10):
        print(l)


if __name__ == '__main__':
    main()
