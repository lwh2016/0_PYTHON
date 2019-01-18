from types import MethodType


class Student(object):
    pass


def set_age(self, age):
    self.age = age


def set_score(self, score):
    self.score = score


def main():
    s = Student()
    s.name = 'Bart'  # 给对象绑定一个方法
    print(s.name)

    s.set_age = MethodType(set_age, s)  # 给对象绑定一个方法。该方法只对这个对象起作用
    s.set_age(25)
    print(s.age)

    Student.set_score = set_score  # 给 类 绑定一个方法。该方法只对类的所有对象都起作用
    s.set_score(90)
    print(s.score)


if __name__ == '__main__':
    main()
