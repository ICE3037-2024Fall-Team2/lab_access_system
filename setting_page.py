from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QMainWindow, QLabel, QLineEdit, QPushButton, QVBoxLayout, QMessageBox, QWidget, QFrame, QDialog, QGridLayout
)

from PyQt5.QtGui import QFont
from aws_connect import connect_to_rds 
from custom_button import CustomButton2

class NumericInputPopup(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Numeric Input")
        self.setWindowFlags(self.windowFlags() | Qt.Tool) 
        self.setFixedSize(400, 300)
        self.input_value = ""

        grid_layout = QGridLayout()

        # Horizontal layout for buttons
        button_layout = QHBoxLayout()

        # Add buttons 0-9
        for i in range(10):
            button = QPushButton(str(i))
            button.setFixedSize(60, 60)
            button.clicked.connect(self.number)
            button_layout.addWidget(button)

        # Add Backspace and Close buttons
        extra_button_layout = QHBoxLayout()
        backspace_button = QPushButton("←")
        backspace_button.setFixedSize(100, 60)
        backspace_button.clicked.connect(self.backspace)
        extra_button_layout.addWidget(backspace_button)

        close_button = QPushButton("Close")
        close_button.setFixedSize(100, 60)
        close_button.clicked.connect(self.close)
        extra_button_layout.addWidget(close_button)

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.addLayout(button_layout)
        main_layout.addLayout(extra_button_layout)
        self.setLayout(main_layout)

    def number(self):
        # Append the clicked number to the input value
        button = self.sender()
        self.input_value += button.text()

    def backspace(self):
        # Remove the last character from the input value
        self.input_value = self.input_value[:-1]

    def get_value(self):
        return self.input_value


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
        #num input diag
        #self.lab_input.setReadOnly(True)
        self.lab_input.mousePressEvent = self.open_numeric_popup


        # Admin ID Input
        self.id_label = QLabel("Enter Admin ID:", self.form_frame)
        self.id_label.setStyleSheet("font-size: 16px; color: white; margin-bottom: 2px; padding: 5px;")
        self.id_input = QLineEdit(self.form_frame)
        self.id_input.setPlaceholderText("Enter Admin ID")
        self.id_input.setStyleSheet("font-size: 16px; background: white; padding: 5px; border-radius: 5px; margin-bottom: 15px;")
        #num input diag
        #self.id_input.setReadOnly(True)
        self.id_input.mousePressEvent = self.open_numeric_popup


        # Login Button
        self.login_button = CustomButton2("Set", self.form_frame)
        self.login_button.clicked.connect(self.handle_login)

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
        #form_layout.addWidget(self.pass_label)
        #form_layout.addWidget(self.pass_input)
        form_layout.addWidget(self.login_button)

        main_layout = QVBoxLayout(self.main_widget)
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.title_label)
        main_layout.addWidget(self.form_frame, alignment=Qt.AlignCenter)
        main_layout.addWidget(self.back_button, alignment=Qt.AlignCenter)

        
    def open_numeric_popup(self, event):
        sender = self.sender()  # Determine which input field triggered the popup
        popup = NumericInputPopup(self)

        # Position the popup near the bottom center of the screen
        screen_geometry = self.screen().geometry()
        popup_width = popup.width()
        popup_height = popup.height()
        popup_x = (screen_geometry.width() - popup_width) // 2
        popup_y = screen_geometry.height() - popup_height - 50  # Adjust margin from bottom
        popup.move(popup_x, popup_y)

        # Show the popup
        if popup.exec_() == QDialog.Accepted:
            sender.setText(popup.get_value())


    def handle_login(self):
        lab_id = self.lab_input.text().strip() 
        admin_id = self.id_input.text().strip() 
        #password = self.pass_input.text()

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

