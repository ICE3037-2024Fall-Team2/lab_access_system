import sys
from picamera2 import Picamera2
from libcamera import controls
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QVBoxLayout, QHBoxLayout, QWidget
)
from custom_button import CustomButton1, CustomButton1_false
from qr_verify_page import QR_CameraWindow
#from stream_page import StreamWindow
from setting_page import LAbSetWindow

class MainWindow(QMainWindow):
    def __init__(self, lab_id=None, lab_name=None):
        super().__init__()
        self.setWindowTitle("Lab Reservation System")
        self.showFullScreen()
        self.setGeometry(100, 100, 720, 1080)

        self.lab_id = lab_id if lab_id else None
        self.lab_name = lab_name if lab_name else None
        
        # Create a central widget and layout
        central_widget = QWidget(self)
        layout = QVBoxLayout(central_widget)
        
        # Welcome label (Centered with text)

        if self.lab_id is None or self.lab_name is None:
            self.welcome_label = QLabel("Please set the lab!", self)
            self.welcome_label.setStyleSheet("font-size: 45px; font-weight: bold;")
            self.unlock_button = CustomButton1_false("Unlock", self)
            self.unlock_button.setEnabled(False)  # 禁用按钮
        else:
            self.welcome_label = QLabel(f"Welcome to <br>{self.lab_name}!", self)
            
            self.welcome_label.setStyleSheet("font-size: 45px; font-weight: bold;")
            self.unlock_button = CustomButton1("Unlock", self)
            self.unlock_button.setEnabled(True)  # 启用按钮
        #self.welcome_label = QLabel("Please set the lab!", self)
        #self.welcome_label.setStyleSheet("font-size: 50px; font-weight: bold;")
        self.welcome_label.setAlignment(Qt.AlignCenter)  # Center align the text
        layout.addWidget(self.welcome_label)

        # Add a spacer between label and button
        layout.addSpacing(20)  # Adds 20px of vertical space between label and button

        # Create a horizontal layout to center the button
        unlock_button_layout = QHBoxLayout()
        # Unlock button with rounded corners and adjusted size
        
        self.unlock_button.setFixedSize(200, 60)
        # Add the button to the horizontal layout to center it
        unlock_button_layout.addWidget(self.unlock_button)
        unlock_button_layout.setAlignment(Qt.AlignCenter)  # Center the button horizontally
        # Add the button layout to the main vertical layout
        layout.addLayout(unlock_button_layout)

        trans_button_layout = QHBoxLayout()
        trans_button_layout.setSpacing(20)
        # Create a "Exit" button
        self.exit_button = CustomButton1("Exit", self)
        self.exit_button.setFixedSize(200, 60)
        self.exit_button.clicked.connect(self.close_application)  # Connect to settings page
        # Create a "Setting" button
        self.setting_button = CustomButton1("Setting", self)
        self.setting_button.setFixedSize(200, 60)
        self.setting_button.clicked.connect(self.open_settings_page)  # Connect to settings page
        layout.addWidget(self.setting_button)
        trans_button_layout.addWidget(self.exit_button)
        trans_button_layout.addWidget(self.setting_button)
        trans_button_layout.setAlignment(Qt.AlignCenter)  # Center the button horizontally
        # Add the button layout to the main vertical layout
        layout.addLayout(trans_button_layout)

        # Center the entire layout in the window
        layout.setAlignment(Qt.AlignCenter)

        # Set layout for the central widget
        self.setCentralWidget(central_widget)

        # Button click connection
        self.unlock_button.clicked.connect(self.open_camera_page)

        self.show()

    def open_camera_page(self):
        # PiCamera2 Setup
        self.picam2 = None
        self.picam2 = Picamera2()
        self.picam2.configure(self.picam2.create_preview_configuration(main={"format": "RGB888","size": (640, 480)}))
        self.picam2.set_controls({"AfMode": controls.AfModeEnum.Continuous})
        self.picam2.start()
        self.camera_window = QR_CameraWindow(self.picam2,self.lab_id,self.lab_name)
        self.camera_window.show()
        self.close()

    def open_settings_page(self):
        self.setting_window = LAbSetWindow(self.lab_id, self.lab_name)
        self.setting_window.show()
        self.close()

    def close_application(self):
        QApplication.quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
