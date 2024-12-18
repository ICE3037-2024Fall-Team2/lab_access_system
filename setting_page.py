from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QMainWindow, QLabel, QLineEdit, QPushButton, QVBoxLayout, QGridLayout, QMessageBox, QWidget, QFrame, QHBoxLayout
)

from PyQt5.QtGui import QFont
from aws_connect import connect_to_rds 
from custom_button import CustomButton2


class LAbSetWindow(QMainWindow):
    def __init__(self, lab_id=None, lab_name=None):
        super().__init__()
        self.setWindowTitle("Lab Setting")
        self.showFullScreen()
        self.setGeometry(100, 100, 720, 1080)

        self.lab_id = lab_id if lab_id else None
        self.lab_name = lab_name if lab_name else None

        # Main Widget
        self.main_widget = QWidget(self)
        self.setCentralWidget(self.main_widget)

        # Center Frame for Login Form
        self.form_frame = QFrame(self.main_widget)
        self.form_frame.setStyleSheet("""
            background-color: #2e7d32;
            border-radius: 10px;
            padding: 20px;
        """)
        self.form_frame.setFixedSize(400,300)

        # Title Label
        self.title_label = QLabel("Lab Setting", self.form_frame)
        self.title_label.setFont(QFont("Arial", 40, QFont.Bold))
        self.title_label.setStyleSheet(" margin-bottom: 10px;")
        self.title_label.setAlignment(Qt.AlignCenter)

        # Lab ID Input
        self.lab_label = QLabel("Enter Lab ID:", self.form_frame)
        self.lab_label.setStyleSheet("font-size: 16px; color: white; margin-bottom: 2px; padding: 5px;")
        self.lab_input = QLineEdit(self.form_frame)
        self.lab_input.setPlaceholderText("Enter Lab ID")
        self.lab_input.setStyleSheet("font-size: 16px; background: white; padding: 5px; border-radius: 5px; margin-bottom: 5px;")
        #num input
        self.lab_input.mousePressEvent = self.show_numeric_keypad



        # Admin ID Input
        self.id_label = QLabel("Enter Admin ID:", self.form_frame)
        self.id_label.setStyleSheet("font-size: 16px; color: white; margin-bottom: 2px; padding: 5px;")
        self.id_input = QLineEdit(self.form_frame)
        self.id_input.setPlaceholderText("Enter Admin ID")
        self.id_input.setStyleSheet("font-size: 16px; background: white; padding: 5px; border-radius: 5px; margin-bottom: 15px;")
        #num input diag
        self.id_input.mousePressEvent = self.show_numeric_keypad

        # Login Button
        self.login_button = CustomButton2("Set", self.form_frame)
        self.login_button.clicked.connect(self.handle_login)
        
        # Numeric Keypad (Hidden by Default)
        self.keypad_frame = QWidget(self.main_widget)
        self.keypad_frame.setStyleSheet("""
            background-color: #f0f0f0;
            border: 1px solid #ccc;
            border-radius: 10px;
            padding: 10px;
        """)
        self.keypad_layout = QGridLayout()
        self.keypad_buttons = []

        # Create buttons for numbers 1-9 in a grid format
        positions = [
            (0, 0), (0, 1), (0, 2),  # Row 0: 1, 2, 3
            (1, 0), (1, 1), (1, 2),  # Row 1: 4, 5, 6
            (2, 0), (2, 1), (2, 2)   # Row 2: 7, 8, 9
        ]

        for idx, (row, col) in enumerate(positions, start=1):
            button = QPushButton(str(idx))
            button.setFixedSize(60, 60)
            button.clicked.connect(self.keypad_input)
            self.keypad_layout.addWidget(button, row, col, alignment=Qt.AlignCenter)  # Align buttons in the grid
            self.keypad_buttons.append(button)

        # Add 0 button
        button_zero = QPushButton("0")
        button_zero.setFixedSize(60, 60)
        button_zero.clicked.connect(self.keypad_input)
        self.keypad_layout.addWidget(button_zero, 3, 1, alignment=Qt.AlignCenter)  # Place 0 in the middle of the 4th row

        # Add Backspace Button
        backspace_button = QPushButton("←")
        backspace_button.setFixedSize(60, 60)
        backspace_button.clicked.connect(self.keypad_backspace)
        self.keypad_layout.addWidget(backspace_button, 3, 0, alignment=Qt.AlignCenter)  # Place Backspace on the left of 4th row

        # Add Close Keypad Button
        close_button = QPushButton("Close")
        close_button.setFixedSize(60, 60)
        close_button.clicked.connect(self.hide_numeric_keypad)
        self.keypad_layout.addWidget(close_button, 3, 2, alignment=Qt.AlignCenter)  # Place Close on the right of 4th row

        self.keypad_frame.setLayout(self.keypad_layout)
        self.keypad_frame.hide()

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

        # Layouts
        form_layout = QVBoxLayout(self.form_frame)
        form_layout.setAlignment(Qt.AlignCenter)
        form_layout.addWidget(self.lab_label)
        form_layout.addWidget(self.lab_input)
        form_layout.addWidget(self.id_label)
        form_layout.addWidget(self.id_input)
        form_layout.addWidget(self.login_button)

        main_layout = QVBoxLayout(self.main_widget)
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.title_label)
        main_layout.addWidget(self.form_frame, alignment=Qt.AlignCenter)
        main_layout.addWidget(self.keypad_frame, alignment=Qt.AlignBottom)
        main_layout.addWidget(self.back_button, alignment=Qt.AlignCenter)


    def hide_numeric_keypad(self):
        self.keypad_frame.hide()

    def show_numeric_keypad(self, event):
        sender = self.sender()
        self.active_input = sender 
        self.keypad_frame.show()

    def keypad_input(self):
        button = self.sender()
        if hasattr(self, "active_input"):
            self.active_input.setText(self.active_input.text() + button.text())

    def keypad_backspace(self):
        if hasattr(self, "active_input"):
            current_text = self.active_input.text()
            self.active_input.setText(current_text[:-1])

    def handle_login(self):
        lab_id = self.lab_input.text().strip() 
        admin_id = self.id_input.text().strip() 

        if not admin_id or not lab_id:
            QMessageBox.warning(self, "Input Error", "Both fields are required.")
            return
        
        if len(admin_id) != 10:
            QMessageBox.warning(self, "Format Error", "Admin ID must be exactly 10 characters long.")
            return

    
        if len(lab_id) != 5:
            QMessageBox.warning(self, "Format Error", "Lab ID must be exactly 5 characters long.")
            return

        try:
            # Connect to AWS RDS
            db_conn = connect_to_rds()
            cursor = db_conn.cursor()

            # Check if admin exists and password matches
            cursor.execute(
                "SELECT * FROM admin WHERE admin_id = %s",
                (admin_id)
            )
            result = cursor.fetchone()

            if not result:
                QMessageBox.critical(self, "Setting Failed", "Invalid Admin ID.")

            else:
                cursor.execute(
                "SELECT lab_name FROM labs WHERE lab_id = %s",
                (lab_id,)
                )
                lab_result = cursor.fetchone()

                if lab_result:
                    lab_name = lab_result[0]
                    from main import MainWindow
                    self.main_window = MainWindow(lab_id, lab_name)
                    self.main_window.show()
                    self.close()
                else:
                    QMessageBox.critical(self, "Setting Failed", "Invalid Lab ID.")

        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"An error occurred: {str(e)}")
        finally:
            if 'db_conn' in locals() and db_conn:
                db_conn.close()

    def go_back(self):
        from main import MainWindow
        self.main_window = MainWindow(self.lab_id, self.lab_name)
        self.main_window.show()
        self.close()

