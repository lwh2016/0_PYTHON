import os
# rootDir = '/home/igs/Backup/Test/libtest'
# ll = os.listdir(rootDir)
# # print(ll)

# rootFile = '/home/igs/Backup/Test/libtest/main.cpp'
# name = os.path.split(rootFile)
# # print(name)

# result = []


# def search(path=".", name=""):
#     for item in os.listdir(path):
#         item_path = os.path.join(path, item)
#         if os.path.isdir(item_path):
#             search(item_path, name)
#         elif os.path.isfile(item_path):
#             if name in item:
#                 global result
#                 result.append(item_path + ";")
#                 print(item_path + ";")


# search(rootDir, 'libworld.so')
# print(os.listdir(rootDir))
# s1 = {1,2,3,4,5,6,76,8}
# s2 = {4,5,6,7,8,9,11,12,13}
# s2 = s1 | s2
# print(s2)
path = '123'
name = '234.pb.txt'
# dd = os.path.join(path,name)
# print(dd)

l = (name.split("."))
print(l)
l.pop()
print(l)
# temName = ""
# for ele in l:
#     temName = temName + str(ele) + "."
# print(temName)
#print("The %s file not in this path %s" % (name,path))