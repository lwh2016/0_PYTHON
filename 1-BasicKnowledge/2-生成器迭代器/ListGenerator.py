# 列表生成式，生成的是一个列表
l = list(range(20))
ll = [x * x for x in l if 0 == x % 2]
print(ll)

# 列表生成器，生成的是一个生成器

lg = (x * x for x in l if 0 == x % 2)
print(lg)
