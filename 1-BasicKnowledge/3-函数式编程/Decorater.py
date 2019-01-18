import functools


def log(func):
    def wrapper(*args, **kw):
        print('calls %s()' % func.__name__)
        return func()

    return wrapper


def log0(text):
    def decorator(func):
        def wrapper(*args, **kw):
            print('%s %s()' % (text, func.__name__))
            return func(*args, **kw)

        return wrapper

    return decorator


def log1(func):
    @functools.wraps(func)
    def wrapper(*args, **kw):
        print('calls %s()' % func.__name__)
        return func()

    return wrapper


def log2(text):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            print('%s %s()' % (text, func.__name__))
            return func(*args, **kw)

        return wrapper

    return decorator


# @log
# @log0('execute')
@log1
def f():
    return f.__name__


def main():
    print(f())


if __name__ == '__main__':
    main()
