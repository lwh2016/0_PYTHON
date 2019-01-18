class Student(object):
    def __init__(self, name):
        self.name = name

    def __getattr__(self, attr):
        if attr == 'score':
            return 99
        if attr == 'age':
            return lambda: 25


class Fib(object):
    def __init__(self):
        self.a = 0
        self.b = 1

    def __iter__(self):
        return self

    def __next__(self):
        self.a, self.b = self.b, self.a + self.b
        if self.a > 20:
            raise StopIteration()
        return self.a

    def __getitem__(self, n):
        for i in range(n):
            self.a, self.b = self.b, self.a + self.b
        return self.b


def main():
    s = Student('Bart')
    # print(dir(s))
    print(s.score)
    print(s.age)
    print(s.age())

    # for i in Fib():
    #     print(i)

    # for i in range(5):
    #     print(Fib()[i])


if __name__ == '__main__':
    main()
