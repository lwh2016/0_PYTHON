from enum import Enum, unique
month = Enum('mouth', ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug',
                       'Sep', 'Oct', 'Nov', 'Dec'))
print(month.Jan.value)


@unique
class weekday(Enum):
    Sun = 0
    Mon = 1
    Tue = 2
    Wed = 3
    Thu = 4
    Fri = 5
    Sat = 6


day0 = weekday.Sun
print(day0)
print(weekday.Wed)
print(weekday.Fri.value)
