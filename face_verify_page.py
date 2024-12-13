from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QMainWindow, QLabel, QPushButton, QMessageBox, QHBoxLayout, QVBoxLayout, QFrame, QWidget
)
from custom_button import CustomButton2, CustomButton2_false
from PyQt5.QtGui import QPixmap, QImage
from picamera2 import Picamera2
from libcamera import controls
import cv2
import numpy as np
import aiohttp
import asyncio

class CameraWindow(QMainWindow):
    def __init__(self, lab_id, lab_name):
        super().__init__()
        self.setWindowTitle("Face_Camera")
        self.showFullScreen()
        self.setGeometry(100, 100, 720, 1080)
        self.lab_id = lab_id
        self.lab_name = lab_name
        self.is_popup_open = False
        self.current_message_box = None
        self.is_request = False  # Tracks if a request is in progress

        # Initialize Picamera2
        self.picam2 = Picamera2()
        self.picam2.configure(self.picam2.create_preview_configuration(main={"format": "RGB888", "size": (640, 480)}))
        self.picam2.set_controls({"AfMode": controls.AfModeEnum.Continuous})
        self.picam2.start()

        # Load Haar Cascade for face detection
        self.face_cascade = cv2.CascadeClassifier('/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml')

        # Set up the main UI
        self.main_widget = QWidget(self)
        self.setCentralWidget(self.main_widget)

        self.camera_label = QLabel(self)
        self.camera_label.setStyleSheet("border: 1px solid black;")

        # Buttons
        self.bt_frame = QFrame(self.main_widget)
        self.bt_frame.setGeometry(50, 50, 400, 100)
        button_layout = QHBoxLayout(self.bt_frame)
        button_layout.setSpacing(20)

        self.face_button = CustomButton2_false("Facial Detection", self)
        self.face_button.setEnabled(False)
        button_layout.addWidget(self.face_button)

        self.qr_button = CustomButton2("QR Code Recognition", self)
        self.qr_button.clicked.connect(self.start_qr_recognition)
        button_layout.addWidget(self.qr_button)

        self.back_button = QPushButton("Go back to homepage", self)
        self.back_button.setStyleSheet(
            """
            font-size: 16px;
            text-decoration: underline;
            color: #006d2e;
            border: none; 
            background: transparent; 
            padding: 0; 
            """
        )
        self.back_button.clicked.connect(self.go_back)

        # Layout setup
        self.show()
        main_layout = QVBoxLayout(self.main_widget)
        main_layout.setSpacing(10)
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.camera_label)
        main_layout.addWidget(self.back_button)
        main_layout.addWidget(self.bt_frame)

        # Timer to capture frames and process in main thread
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.detect_and_process_face)
        self.timer.start(30)  # Update every 30ms

    def timerEvent(self):
        frame = self.picam2.capture_array()
        if frame is not None:
            frame = cv2.flip(frame, 1)  # Mirror the frame
            frame = self.detect_and_process_face(frame)
            self.display_frame(frame)

    def display_frame(self, frame):
        height, width, channel = frame.shape
        step = channel * width
        q_image = QImage(frame.data, width, height, step, QImage.Format_BGR888)
        pixmap = QPixmap.fromImage(q_image)
        self.camera_label.setPixmap(pixmap)

    def detect_and_process_face(self):
        frame = self.picam2.capture_array()
        if frame is not None:
            frame = cv2.flip(frame, 1)  # Mirror the frame
            frame = self.detect_and_process_face(frame)


        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        if len(faces) > 0:
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

                if(self.is_request == False):
                    self.is_request = True
                    asyncio.create_task(self.send_request(self.lab_id, frame))

        self.display_frame(frame)

    async def send_request(self, lab_id, image):
        try:
            _, img_encoded = cv2.imencode('.jpg', image)
            img_bytes = img_encoded.tobytes()
            data = aiohttp.FormData()
            data.add_field('image', img_bytes, filename='image.jpg', content_type='image/jpeg')
            data.add_field('lab_id', lab_id)

            async with aiohttp.ClientSession() as session:
                async with session.post('http://localhost:5001/upload_image', data=data) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        if response_data.get('verified') and response_data.get('student_id'):
                            self.find_message(response_data['student_id'])
                        else:
                            self.show_error_message(response_data.get('message', 'Verification failed'))
                    else:
                        self.show_error_message(f"Request failed with status code {response.status}")
        except Exception as e:
            self.show_error_message(f"Error occurred: {str(e)}")
        finally:
            self.is_request = False  # Reset flag after request completion

    def show_error_message(self, message):
        if not self.is_popup_open:
            self.is_popup_open = True
            self.current_message_box = QMessageBox(self)
            self.current_message_box.setIcon(QMessageBox.Critical)
            self.current_message_box.setWindowTitle("Error")
            self.current_message_box.setText(message)
            self.current_message_box.setStandardButtons(QMessageBox.Ok)
            self.current_message_box.finished.connect(self.reset_popup_status)
            self.current_message_box.show()

    def reset_popup_status(self):
        self.is_popup_open = False
        self.current_message_box = None

    def find_message(self, student_id):
        if self.current_message_box:
            self.current_message_box.close()

        from unlock_page import UnlockWindow
        self.cleanup_resources()
        self.unlock_window = UnlockWindow(self.lab_id, self.lab_name, student_id)
        self.unlock_window.show()
        self.close()

    def go_back(self):
        from main import MainWindow
        self.cleanup_resources()
        self.main_window = MainWindow(self.lab_id, self.lab_name)
        self.main_window.show()
        self.close()

    def start_qr_recognition(self):
        from qr_verify_page import QR_CameraWindow
        self.cleanup_resources()
        self.qr_window = QR_CameraWindow(self.lab_id, self.lab_name)
        self.qr_window.show()
        self.close()

    def cleanup_resources(self):
        self.timer.stop()

        if self.picam2:
            self.picam2.stop()
            self.picam2.close()
            self.picam2 = None

    def closeEvent(self, event):
        self.cleanup_resources()
        event.accept()