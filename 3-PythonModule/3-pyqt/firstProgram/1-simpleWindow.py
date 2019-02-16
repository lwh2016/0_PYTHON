# -*- coding: utf-8 -*-
# @filename simpleWindow.py
# @author guokonghui
# @description
# @created Mon Jan 21 2019 13:46:53 GMT+0800 (中国标准时间)
# @last-modified Mon Jan 21 2019 14:52:42 GMT+0800 (中国标准时间)
#

import sys
from PyQt5 import QtWidgets

if __name__ == '__main__':

    # 创建一个 application 对象app , sys.argv参数是一个来自命令行的参数列表
    app = QtWidgets.QApplication(sys.argv)
    # Qwidget组件是PyQt5中所有用户界面类的基础类
    w = QtWidgets.QWidget()
    # resize()方法调整了widget组件的大小
    w.resize(350, 250)
    # move()方法移动widget组件到一个位置，这个位置是屏幕上x=300,y=300的坐标
    w.move(300, 300)
    # 设置了我们窗口的标题
    w.setWindowTitle('Simple')
    # show()方法在屏幕上显示出widget。一个widget对象在这里第一次被在内存中创建，并且之后在屏幕上显示
    w.show()

    sys.exit(app.exec_())
