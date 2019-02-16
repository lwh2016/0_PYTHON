import sys
from PyQt5 import QtWidgets as QW
from PyQt5 import QtGui as QG


class Example(QW.QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        # 类的静态成员函数,设置提示框的字体字号
        QW.QToolTip.setFont(QG.QFont('SansSerif', 10))

        # 为窗口本身设置提示框信息
        self.setToolTip('This is a <b>QWidget<b> widget')
        # 创建一个Button对象, "Button"是显示在按钮上的内容,第二个参数是放置按钮的组件
        btn = QW.QPushButton('Button', self)
        # 为btn设置提示框信息
        btn.setToolTip('This is a <b>QPushButton<b> widget')
        btn.resize(btn.sizeHint())
        btn.move(50, 50)

        self.setGeometry(300, 300, 300, 220)
        self.setWindowTitle('ToolTips')
        self.setWindowIcon(QG.QIcon('3-PythonModule\\3-pyqt\\Test.ico'))
        self.show()


if __name__ == "__main__":
    app = QW.QApplication(sys.argv)
    ex = Example()
    sys.exit(app.exec_())
