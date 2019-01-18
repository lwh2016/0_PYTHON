# 类属性
class Student(object):
    name = 'Student'


def main():
    s = Student()
    print(s.name)
    s.name = 'Bart'  # 给对象s绑定一个属性
    print(s.name)  # 打印对象s的属性
    print(Student.name)  # 打印Student类属性，上面改变了对象s的属性，但是Student的类属性并没有改变


if __name__ == '__main__':
    main()
