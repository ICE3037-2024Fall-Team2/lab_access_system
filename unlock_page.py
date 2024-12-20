from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget
)
from PyQt5.QtGui import QFont

class UnlockWindow(QMainWindow):
    def __init__(self, lab_id, lab_name, user_id):
        super().__init__()
        self.setWindowTitle("Unlock")
        self.showFullScreen()
        self.setGeometry(100, 100, 720, 1080)

        self.lab_id = lab_id 
        self.lab_name = lab_name
        self.user_id = user_id

        # Main Widget
        self.main_widget = QWidget(self)
        self.setCentralWidget(self.main_widget)


        # Title Label
        self.title_label = QLabel("Unlocked", self.main_widget)
        self.title_label.setFont(QFont("Arial", 45, QFont.Bold))
        self.title_label.setStyleSheet(" margin-bottom: 10px;")
        self.title_label.setAlignment(Qt.AlignCenter)

        # Welcome Label
        self.welcome_label = QLabel(f"<br>Welcome to<br> {self.lab_name},<br><br>{self.user_id}!", self.main_widget)
        self.welcome_label.setFont(QFont("Arial", 40, QFont.Bold))
        self.welcome_label.setStyleSheet(" margin-bottom: 10px;")
        self.welcome_label.setAlignment(Qt.AlignCenter)

        # Back to Homepage Button
        self.back_button = QPushButton("Go back to homepage", self.main_widget)
        self.back_button.setStyleSheet("""
            font-size: 16px;
            text-decoration: underline;
            color: #006d2e;
            border: none; 
            background: transparent; 
        """)
        self.back_button.clicked.connect(self.go_back)


        main_layout = QVBoxLayout(self.main_widget)
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.title_label)
        main_layout.addWidget(self.welcome_label)
        main_layout.addWidget(self.back_button, alignment=Qt.AlignCenter)

    def go_back(self):
        from main import MainWindow
        self.main_window = MainWindow(self.lab_id, self.lab_name)
        self.main_window.show()
        self.close()

