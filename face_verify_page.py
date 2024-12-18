from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer
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
from queue import Queue
import pymysql

class Worker(QThread):
    find_signal = pyqtSignal(str)  # Signal for successful verification with student ID
    error_signal = pyqtSignal(str)  # Signal for errors or verification failures

    def __init__(self, db_connection):
        super().__init__()
        self.loop = asyncio.get_event_loop()  # Use the current event loop if available
        self.db_connection = db_connection  # Reuse the provided database connection


    async def send_request(self, lab_id, image):
        """Asynchronous function to send the request."""
        try:
            _, img_encoded = cv2.imencode('.jpg', image)
            img_bytes = img_encoded.tobytes()
            data = aiohttp.FormData()
            data.add_field('image', img_bytes, filename='image.jpg', content_type='image/jpeg')
            data.add_field('lab_id', lab_id)

            print(f"Sending request with lab_id: {lab_id}, Image size: {len(img_bytes)}")

            async with aiohttp.ClientSession() as session:
                async with session.post('http://localhost:5000/upload_image', data=data) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        print(f"Response received: {response_data}")

                        if response_data.get('verified') and response_data.get('student_id'):
                            self.find_signal.emit(response_data['student_id'])
                        else:
                            self.error_signal.emit(response_data.get('message', 'Verification failed'))
                    else:
                        self.error_signal.emit(f"Request failed with status code {response.status}")
        except Exception as e:
            self.error_signal.emit(f"Error occurred: {str(e)}")

    def run_task(self, lab_id, image):
        """Start the asynchronous request."""
        asyncio.run(self.send_request(lab_id, image))  # Runs the coroutine in the current thread

    def run(self):
        """Start the event loop in this thread."""
        try:
            self.loop.run_forever()  # Keep the loop running
        except RuntimeError as e:
            print(f"RuntimeError in Worker run: {e}")

    def stop(self):
        """Stop the event loop."""
        if self.loop.is_running():
            self.loop.stop()

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
        self.frame_counter = 0  # Add frame counter
        self.frame_skip = 25  # Send request every 25 frames

        self.db_connection = self.open_database_connection()


        # Initialize Picamera2
        self.picam2 = Picamera2()
        self.picam2.configure(self.picam2.create_preview_configuration(main={"format": "RGB888","size": (640, 480)}))
        self.picam2.set_controls({"AfMode": controls.AfModeEnum.Continuous})
        self.picam2.start()

        # Load Haar Cascade for face detection
        self.face_cascade = cv2.CascadeClassifier('/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml')


        # Set up the main UI
        self.main_widget = QWidget(self)
        self.setCentralWidget(self.main_widget)

        # Status label
        self.status_label = QLabel("Please show your face", self.main_widget)
        self.status_label.setStyleSheet("font-size: 18px; font-weight: bold; color: blue;")
        self.status_label.setAlignment(Qt.AlignCenter)

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
        main_layout.addWidget(self.status_label)
        main_layout.addWidget(self.camera_label)
        main_layout.addWidget(self.back_button)
        main_layout.addWidget(self.bt_frame)

        # Timer to capture frames and process in main thread
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.timerEvent)
        self.timer.start(30)  # Update every 30ms

        # Initialize worker thread
        self.worker = Worker(self.db_connection)
        self.worker.find_signal.connect(self.find_message)
        self.worker.error_signal.connect(self.show_error_message)
        self.worker.start()

    def open_database_connection(self):
        try:
            connection = pymysql.connect(
                host="YOUR_DB_HOST",
                user="YOUR_DB_USER",
                password="YOUR_DB_PASSWORD",
                database="YOUR_DB_NAME"
            )
            print("Database connection established")
            return connection
        except Exception as e:
            print(f"Error opening database connection: {e}")
            return None

    def close_database_connection(self):
        if self.db_connection:
            self.db_connection.close()
            print("Database connection closed")
            
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

    def detect_and_process_face(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        if len(faces) > 0:
            self.status_label.setText("Face detected. Identifying...") 

            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        
            #self.frame_counter += 1
            #self.worker.run_task(self.lab_id, frame)

            # Send a request every n frames
            #if self.frame_counter >= self.frame_skip and not self.worker.is_running:
            self.worker.run_task(self.lab_id, frame)
                #self.frame_counter = 0 

        return frame

    def show_error_message(self, message):
        self.status_label.setText("Please show your face") 

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
        self.status_label.setText("Student identified. Verifying...")

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

        if self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()

        if self.picam2:
            self.picam2.stop()
            self.picam2.close()
            self.picam2 = None

        self.close_database_connection()


    def closeEvent(self, event):
        self.cleanup_resources()
        event.accept()
