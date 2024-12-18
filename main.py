import sys
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QVBoxLayout, QHBoxLayout, QWidget
)
from custom_button import CustomButton1, CustomButton1_false, CustomButton1_trans
from qr_verify_page import QR_CameraWindow
from face_verify_page import CameraWindow
#from stream_page import StreamWindow
from setting_page import LAbSetWindow

class MainWindow(QMainWindow):
    def __init__(self, lab_id=None, lab_name=None):
        super().__init__()
        self.setWindowTitle("Lab Reservation System")
        self.showFullScreen()
        self.setGeometry(100, 100, 720, 1080)
        self.setStyleSheet("background-color:white;")

        self.lab_id = lab_id if lab_id else None
        self.lab_name = lab_name if lab_name else None
        
        # Create a central widget and layout
        central_widget = QWidget(self)
        layout = QVBoxLayout(central_widget)

        trans_button_layout = QHBoxLayout()
        trans_button_layout.setSpacing(20)
        # Create a "Exit" button
        self.exit_button = CustomButton1_trans("Exit", self)
        self.exit_button.setFixedSize(200, 60)
        self.exit_button.clicked.connect(self.close_application)  # Connect to settings page
        # Create a "Setting" button
        self.setting_button = CustomButton1_trans("Setting", self)
        self.setting_button.setFixedSize(200, 60)
        self.setting_button.clicked.connect(self.open_settings_page)  # Connect to settings page
        layout.addWidget(self.setting_button)
        trans_button_layout.addWidget(self.exit_button)
        trans_button_layout.addWidget(self.setting_button)
        trans_button_layout.setAlignment(Qt.AlignCenter)  # Center the button horizontally
        # Add the button layout to the main vertical layout
        layout.addLayout(trans_button_layout)

                # Welcome label (Centered with text)

        if self.lab_id is None or self.lab_name is None:
            self.welcome_label = QLabel("Please set the lab!", self)
            self.welcome_label.setStyleSheet("font-size: 45px; font-weight: bold;")
            self.qr_unlock_button = CustomButton1_false("Unlock", self)
            #self.face_unlock_button = CustomButton1_false("Face Unlock", self)
            self.qr_unlock_button.setEnabled(False)  
        else:
            self.welcome_label = QLabel(f"Welcome to <br>{self.lab_name}!", self)
            
            self.welcome_label.setStyleSheet("font-size: 45px; font-weight: bold;")
            self.qr_unlock_button = CustomButton1("Unlock", self)
            #self.face_unlock_button = CustomButton1("Face Unlock", self)
            self.qr_unlock_button.setEnabled(True)  
        #self.welcome_label = QLabel("Please set the lab!", self)
        #self.welcome_label.setStyleSheet("font-size: 50px; font-weight: bold;")
        self.welcome_label.setAlignment(Qt.AlignCenter)  # Center align the text
        layout.addWidget(self.welcome_label)

        # Add a spacer between label and button
        layout.addSpacing(20) 

        # Create a horizontal layout to center the button
        unlock_button_layout = QVBoxLayout()
        # Unlock button with rounded corners and adjusted size
        #self.face_unlock_button.setFixedSize(200, 60)
        self.qr_unlock_button.setFixedSize(200, 60)
        # Add the button to the horizontal layout to center it
        unlock_button_layout.addWidget(self.qr_unlock_button)
        #unlock_button_layout.addWidget(self.face_unlock_button)
        unlock_button_layout.setAlignment(Qt.AlignCenter)  # Center the button horizontally
        # Add the button layout to the main vertical layout
        layout.addLayout(unlock_button_layout)

        # Center the entire layout in the window
        layout.setAlignment(Qt.AlignCenter)

        # Set layout for the central widget
        self.setCentralWidget(central_widget)

        # Button click connection
        self.qr_unlock_button.clicked.connect(self.open_qr_camera_page)
        #self.face_unlock_button.clicked.connect(self.open_face_camera_page)
        self.show()

    def open_qr_camera_page(self):
        self.qrcamera_window = QR_CameraWindow(self.lab_id,self.lab_name)
        self.qrcamera_window.show()
        #self.close()
        QTimer.singleShot(80, self.clone)

    #def open_face_camera_page(self):
    #    self.facecamera_window = CameraWindow(self.lab_id,self.lab_name)
    #    self.facecamera_window.show()
    #    self.close()


    def open_settings_page(self):
        self.setting_window = LAbSetWindow(self.lab_id, self.lab_name)
        self.setting_window.show()
        #self.close()
        QTimer.singleShot(80, self.close)

    def close_application(self):
        QApplication.quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
