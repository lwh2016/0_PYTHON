class Student(object):
    __slots__ = ('name', 'age')  # 用tuple定义允许绑定的属性名称


# 使用__slots__要注意，__slots__定义的属性仅对当前类实例起作用，对继承的子类是不起作用的
class GraduateStudent(Student):
    pass


# 如果子类中也定义了__slots__，那么子类对象可以绑定的属性就是父类和子类中__slots__规定的属性
class LittleStudent(Student):
    __slots__ = ('score')


def main():
    s = Student()
    s.name = 'Bart'
    s.age = 9
    # s.score = 60  # score不在__slots__中，所以不能绑定到对象

    gs = GraduateStudent()
    gs.score = 78  # __slots__定义的属性不会对子类起作用
    print(gs.score)

    ls = LittleStudent()
    ls.name = 'Sam'
    ls.age = 9
    ls.score = 98
    # ls.weight = 70 # weight不在父类和子类的__slots__中，所以不能绑定到对象


if __name__ == '__main__':
    main()
