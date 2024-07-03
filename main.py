from PyQt5.QtWidgets import QApplication
from ui import Vibration_Test_UI
import sys

if __name__ == '__main__':
    app = QApplication(sys.argv)
    myApp = Vibration_Test_UI()
    myApp.show()
    sys.exit(app.exec_())