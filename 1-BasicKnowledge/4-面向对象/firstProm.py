class Student(object):
    def __init__(self, name, score):
        self.name = name
        self.score = score

    def print_score(self):
        print(self.score)


def main():
    Sam = Student('Sam', 90)
    Mike = Student('Mike', 98)
    Sam.age = 9  # 可以给实例对象绑定属性
    print(Sam.age)
    Sam.print_score()
    Mike.print_score()


if __name__ == '__main__':
    main()