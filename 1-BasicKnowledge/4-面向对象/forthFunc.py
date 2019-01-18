class Animal(object):
    def run(self):
        print('Animal is running')


class Dog(Animal):
    def run(self):
        print('Dog is running')


class Cat(Animal):
    def run(self):
        print('Cat is running')


def run_twice(animal):
    animal.run()
    animal.run()


def main():
    mAnimal = Animal()
    mAnimal.run()
    run_twice(mAnimal)

    mDog = Dog()
    mDog.run()
    run_twice(mDog)

    mCat = Cat()
    mCat.run()
    run_twice(mCat)

    print(dir(mDog))
    print('****************')
    if hasattr(mDog, 'run'):
        mDog.run()


if __name__ == '__main__':
    main()