class Doctor(object):
    def __init__(self, department, education):
        self.__department = department
        self.__education = education

    def print_allmsg(self):
        print(self.__class__.__name__)
        print('%s %s' % (self.__department, self.__education))

    def setEdu(self, education):
        self.__education = education


def main():
    Zhang = Doctor('Internal', 'Master')
    Zhang.print_allmsg()

    Wang = Doctor('external', 'Master')
    Wang.print_allmsg()
    Wang.setEdu('Doctor')
    Wang.print_allmsg()


if __name__ == '__main__':
    main()
