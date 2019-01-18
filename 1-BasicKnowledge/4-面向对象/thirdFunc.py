class Animal(object):
    def run(self):
        print('Animal is running')


class Dog(Animal):
    pass


class Cat(Animal):
    pass


def main():
    mAnimal = Animal()
    mAnimal.run()

    mDog = Dog()
    mDog.run()

    mCat = Cat()
    mCat.run()


if __name__ == '__main__':
    main()
