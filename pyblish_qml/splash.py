import os
from .vendor.Qt import QtWidgets, QtCore, QtGui


MODULE_DIR = os.path.dirname(__file__)
SPLASH_PATH = os.path.join(MODULE_DIR, "splash.png")


class Splash(QtWidgets.QWidget):
    """Splash screen for loading QML via subprocess

    Loading pyblish-qml may take some time, so when loading
    from within an existing interpreter, such as Maya, this
    splash screen can keep the user company during that time.

    """

    def __init__(self, parent=None):
        super(Splash, self).__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setWindowFlags(
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.FramelessWindowHint
        )

        pixmap = QtGui.QPixmap(SPLASH_PATH)
        image = QtWidgets.QLabel()
        image.setPixmap(pixmap)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(image)

        label = QtWidgets.QLabel(self)
        label.move(20, 170)
        label.show()

        self.count = 0
        self.label = label

        self.setStyleSheet("""
            QLabel {
                color: white
            }
        """)

        loop = QtCore.QTimer()
        loop.timeout.connect(self.animate)
        loop.start(330)

        self.loop = loop

        self.animate()
        self.resize(200, 200)

    def animate(self):
        self.label.setText("loading" + "." * self.count)
        self.count = (self.count + 1) % 4
