# 定义的score是可读可写的权限
class Student(object):
    @property
    def score(self):
        return self.__score

    @score.setter
    def score(self, value):
        if not isinstance(value, int):
            raise ValueError('score value must be int type')
        if value < 0 and value > 100:
            raise ValueError('score value must be in 0~100')
        self.__score = value


class Child(object):
    # 定义year的可读权限
    @property
    def year(self):
        return self.__year

    # 定义year的可写权限
    @year.setter
    def year(self, value):
        if not isinstance(value, int):
            raise ValueError('score value must be int type')
        self.__year = value

    # 定义age的可读权限
    @property
    def age(self):
        return 2018 - self.__year


def main():
    s = Student()
    # print(s.score)
    s.score = 60
    print(s.score)

    c = Child()
    c.year = 1992
    print(c.year)
    print(c.age)


if __name__ == '__main__':
    main()
