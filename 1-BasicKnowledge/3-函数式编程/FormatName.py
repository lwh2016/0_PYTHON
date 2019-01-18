def normalize(name):
    if isinstance(name, str):
        name = name.lower()
    else:
        print("It not a string type name")
    name = name[0].upper() + name[1:]
    return name


l1 = ['adam', 'LISA', 'barT']


def main():
    ll = map(normalize, l1)
    for n in ll:
        print(n)


if __name__ == '__main__':
    main()
