from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QMainWindow, QLabel, QLineEdit, QPushButton, QVBoxLayout, QMessageBox, QWidget, QFrame
)
from PyQt5.QtGui import QFont, QGuiApplication
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
        #fullscreen + virtkeyboard
        self.lab_input.setFocusPolicy(Qt.StrongFocus)
        self.lab_input.focusInEvent = lambda event: QGuiApplication.inputMethod().show()


        # Admin ID Input
        self.id_label = QLabel("Enter Admin ID:", self.form_frame)
        self.id_label.setStyleSheet("font-size: 16px; color: white; margin-bottom: 2px; padding: 5px;")
        self.id_input = QLineEdit(self.form_frame)
        self.id_input.setPlaceholderText("Enter Admin ID")
        self.id_input.setStyleSheet("font-size: 16px; background: white; padding: 5px; border-radius: 5px; margin-bottom: 15px;")
        #fullscreen + virtkeboard
        self.id_input.setFocusPolicy(Qt.StrongFocus)
        self.id_input.focusInEvent = lambda event: QGuiApplication.inputMethod().show()

        # Password Input
        #self.pass_label = QLabel("Password:", self.form_frame)
        #self.pass_label.setStyleSheet("font-size: 16px; color: white; margin-bottom: 5px;padding: 5px;")
        #self.pass_input = QLineEdit(self.form_frame)
        #self.pass_input.setPlaceholderText("Enter Password")
        #self.pass_input.setEchoMode(QLineEdit.Password)
        #self.pass_input.setStyleSheet("font-size: 16px; background: white; padding: 5px; border-radius: 5px; margin-bottom: 20px;")

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

