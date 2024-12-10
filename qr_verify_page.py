from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import (
    QMainWindow, QLabel, QPushButton, QMessageBox, QHBoxLayout, QVBoxLayout, QFrame, QWidget
)
from PyQt5.QtGui import QPixmap, QImage
from picamera2 import Picamera2, Preview
from pyzbar.pyzbar import decode
from custom_button import CustomButton2, CustomButton2_false
import datetime
from aws_connect import connect_to_rds
from unlock_page import UnlockWindow
import numpy as np


class QR_CameraWindow(QMainWindow):
    def __init__(self, lab_id, lab_name):
        super().__init__()
        self.setWindowTitle("QR_Camera")
        self.setGeometry(100, 100, 720, 1080)
        self.lab_id = lab_id
        self.lab_name = lab_name
        self.is_qr_processed = False

        self.main_widget = QWidget(self)
        self.setCentralWidget(self.main_widget)

        # Camera Label
        self.camera_frame = QFrame(self.main_widget)
        self.camera_frame.setFixedSize(600, 560)
        self.camera_label = QLabel(self)
        self.camera_label.setGeometry(50, 50, 600, 560)
        self.camera_label.setStyleSheet("border: 1px solid black;")

        # Buttons
        self.bt_frame = QFrame(self.main_widget)
        self.bt_frame.setGeometry(50, 50, 400, 100)

        button_layout = QHBoxLayout(self.bt_frame)
        button_layout.setSpacing(10)

        # Face Detection Button
        self.face_button = CustomButton2("Facial Detection", self)
        self.face_button.clicked.connect(self.start_face_detection)
        button_layout.addWidget(self.face_button)

        # QR Code Recognition Button (Initially disabled)
        self.qr_button = CustomButton2_false("QR Code Recognition", self)
        self.qr_button.setEnabled(False)  # Disable the button to prevent interaction
        button_layout.addWidget(self.qr_button)

        # Back to Homepage Button
        self.back_button = QPushButton("Go back to homepage", self)
        self.back_button.setStyleSheet("""
            text-decoration: underline;
            color: #006d2e;
            border: none;
            background: transparent;
            padding: 0;
        """)
        self.back_button.clicked.connect(self.go_back)
        self.back_button.setGeometry(50, 50, 200, 40)

        # PiCamera2 Setup
        self.picam2 = Picamera2()
        self.picam2.configure(self.picam2.create_preview_configuration(main={"size": (640, 480)}))
        self.picam2.start()

        # Timer for frame updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # Update every 30ms

        # Layout Setup
        self.show()
        main_layout = QVBoxLayout(self.main_widget)
        main_layout.setSpacing(10)
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.camera_frame)
        main_layout.addWidget(self.back_button)
        main_layout.addWidget(self.bt_frame)

    def start_face_detection(self):
        from face_verify_page import CameraWindow
        self.picam2.stop()
        self.timer.stop()
        self.face_window = CameraWindow(self.lab_id, self.lab_name)
        self.face_window.show()
        self.close()

    def update_frame(self):
        frame = self.picam2.capture_array()
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channel = frame.shape
        step = channel * width
        q_image = QPixmap.fromImage(
            QImage(frame.data, width, height, step, QImage.Format_RGB888)
        )
        self.camera_label.setPixmap(q_image)
        self.scan_qr_code(frame)

    def scan_qr_code(self, frame):
        if self.is_qr_processed:
            return

        decoded_objects = decode(frame)
        for obj in decoded_objects:
            points = obj.polygon
            if len(points) == 4:
                pts = [tuple(point) for point in points]
                cv2.polylines(frame, [np.array(pts, dtype=np.int32)], True, (0, 255, 0), 3)
            qr_data = obj.data.decode('utf-8')
            if len(qr_data) == 15 and qr_data.isdigit():
                reservation_id = qr_data
                self.is_qr_processed = True
                QTimer.singleShot(100, lambda: self.verify_reservation(reservation_id))
                break

    def verify_reservation(self, reservation_id):
        # Same verification logic as your original implementation
        pass

    def go_back(self):
        from main import MainWindow
        self.picam2.stop()
        self.timer.stop()
        self.main_window = MainWindow(self.lab_id, self.lab_name)
        self.main_window.show()
        self.close()

    def closeEvent(self, event):
        self.picam2.stop()
        self.timer.stop()
        event.accept()
