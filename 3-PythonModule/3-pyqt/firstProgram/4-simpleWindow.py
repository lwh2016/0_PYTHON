import sys
from PyQt5 import QtWidgets as QW
# from PyQt5 import QtGui as QG
from PyQt5 import QtCore as QC


class Example(QW.QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        qbtn = QW.QPushButton('Quit', self)
        qbtn.clicked.connect(QC.QCoreApplication.instance().quit)
        qbtn.resize(qbtn.sizeHint())
        qbtn.move(50, 50)

        self.setGeometry(300, 300, 300, 300)
        self.setWindowTitle('Quit Button')
        self.show()


if __name__ == "__main__":
    app = QW.QApplication(sys.argv)
    ex = Example()
    sys.exit(app.exec_())
