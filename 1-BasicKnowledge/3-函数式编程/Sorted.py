def by_score(t):
    return t[1]


def main():
    L = [('Bob', 75), ('Adam', 92), ('Bart', 66), ('Lisa', 88)]
    sort_by_score = sorted(L, key=by_score)
    print(sort_by_score)


if __name__ == '__main__':
    main()
