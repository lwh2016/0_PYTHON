try:
    print('execute Try ...')
    r = 10 / int('a')
    print('result:', r)
except ValueError as e:
    print('execute Except and ValueError:', e)
    raise ValueError()
except ZeroDivisionError as e:
    print('ZeroDivisionError:', e)
finally:
    print('execute Finally...')