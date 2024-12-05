from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt5.QtWidgets import (
    QMainWindow, QLabel, QPushButton, QMessageBox, QHBoxLayout, QVBoxLayout, QFrame, QWidget
)
from PyQt5.QtGui import QPixmap, QImage
import cv2
import numpy as np
from custom_button import CustomButton2, CustomButton2_false
from unlock_page import UnlockWindow
import requests

class Worker(QThread):
    result_signal = pyqtSignal(np.ndarray)
    find_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, capture, lab_id, lab_name):
        super().__init__()
        self.capture = capture
        self.is_running = True
        self.lab_id = lab_id
        self.lab_name = lab_name
        self.is_face_processed = False
        self.frame_counter = 1

        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    def run(self):
        while self.is_running:
            ret, frame = self.capture.read()
            if ret: 
                self.frame_counter += 1    
                self.detect_and_process_face(frame)

    def detect_and_process_face(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        if len(faces) > 0:  
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

            self.compare_faces(frame)

        self.result_signal.emit(frame)

    def compare_faces(self, frame):
        """Compare detected face with the database faces."""
        if self.is_face_processed or self.frame_counter % 50 != 0:
            return
        self.is_face_processed = True
        self.frame_counter = 1
        self.sync_compare_faces(frame)

    def sync_compare_faces(self, frame):
        try:
            _, img_encoded = cv2.imencode('.jpg', frame)
            img_bytes = img_encoded.tobytes()
            files = {
                'image': ('image.jpg', img_bytes, 'image/jpeg'),
                'lab_id': (None, self.lab_id)
            }
            response = requests.post('http://localhost:5001/upload_image', files=files)
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get('verified') and response_data.get('student_id'):
                    student_id = response_data['student_id']
                    self.find_signal.emit(student_id)
                else:
                    self.error_signal.emit("No matching student found")
            else:
                self.error_signal.emit("Failed to detect face")
        except Exception as e:
            self.error_signal.emit(f"Error occurred: {str(e)}")
        finally:
            self.is_face_processed = False

    def stop(self):
        self.is_running = False
        self.quit()
class CameraWindow(QMainWindow):
    def __init__(self, lab_id, lab_name):
        super().__init__()
        self.setWindowTitle("Face_Camera")
        self.setGeometry(100, 100, 720, 1080)
        self.lab_id = lab_id
        self.lab_name = lab_name
        self.is_popup_open = False
        self.current_message_box = None

        # Set up the main UI
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
        self.bt_frame.setGeometry(50, 50, 400,100)
        button_layout = QHBoxLayout(self.bt_frame)
        button_layout.setSpacing(20)

        self.face_button = CustomButton2_false("Facial Detection", self)
        self.face_button.setEnabled(False)
        button_layout.addWidget(self.face_button)

        self.qr_button = CustomButton2("QR Code Recognition", self)
        self.qr_button.clicked.connect(self.start_qr_recognition)
        button_layout.addWidget(self.qr_button)

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

        # Layout setup
        main_layout = QVBoxLayout(self.main_widget)
        main_layout.setSpacing(10)
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.camera_frame)
        main_layout.addWidget(self.back_button)
        main_layout.addWidget(self.bt_frame)

        self.capture = cv2.VideoCapture(0)


        self.worker = Worker(self.capture,self.lab_id,self.lab_name)
        self.worker.result_signal.connect(self.update_frame)
        self.worker.error_signal.connect(self.show_error_message) 
        self.worker.find_signal.connect(self.find_message) 
        self.worker.start()


        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_camera_frame)
        self.timer.start(100) 

    def show_error_message(self, message):
        if not self.is_popup_open:
            self.is_popup_open = True
            # 创建 QMessageBox 实例
            self.current_message_box = QMessageBox(self)
            self.current_message_box.setIcon(QMessageBox.Critical)
            self.current_message_box.setWindowTitle("Error")
            self.current_message_box.setText(message)
            self.current_message_box.setStandardButtons(QMessageBox.Ok)
            self.current_message_box.finished.connect(self.reset_popup_status)  # 监听弹窗关闭事件
            self.current_message_box.show()

    def reset_popup_status(self):
        self.is_popup_open = False
        self.current_message_box = None

    def find_message(self, stu_id):
        if self.current_message_box:
            self.current_message_box.close()

        self.unlock_window = UnlockWindow(self.lab_id, self.lab_name, stu_id)
        self.unlock_window.show()
        self.close()

    def update_frame(self, frame):
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channel = frame.shape
        step = channel * width
        q_image = QImage(frame.data, width, height, step, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_image)
        self.camera_label.setPixmap(pixmap)

    def update_camera_frame(self):
        pass 
    

    def start_qr_recognition(self):
        """Switch to QR recognition screen."""
        from qr_verify_page import QR_CameraWindow
        self.capture.release()
        self.timer.stop()
        self.qr_window = QR_CameraWindow(self.lab_id, self.lab_name)
        self.qr_window.show()
        self.close()

    def go_back(self):
        """Go back to the homepage."""
        from main import MainWindow
        self.capture.release()
        self.timer.stop()
        self.main_window = MainWindow(self.lab_id, self.lab_name)
        self.main_window.show()
        self.close()

    def closeEvent(self, event):
        """Release the capture and stop the timer when the window is closed."""
        self.worker.stop()
        self.worker.wait() 
        self.capture.release()
        self.timer.stop()
        event.accept()


