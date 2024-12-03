from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt5.QtWidgets import (
    QMainWindow, QLabel, QPushButton, QMessageBox, QHBoxLayout, QVBoxLayout, QFrame, QWidget
)
from PyQt5.QtGui import QPixmap, QImage
import cv2
import numpy as np
from custom_button import CustomButton2, CustomButton2_false
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
from unlock_page import UnlockWindow
import aiohttp
import asyncio

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
        if self.is_face_processed or self.frame_counter % 20 != 0:
            return
        self.is_face_processed = True
        self.frame_counter = 1
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self.async_compare_faces(frame))

    async def async_compare_faces(self, frame):
        async with aiohttp.ClientSession() as session:
            _, img_encoded = cv2.imencode('.jpg', frame)
            img_bytes = img_encoded.tobytes()
            files = {
                'image': img_bytes,  # The image file
                'lab_id': self.lab_id  # The lab ID
            }
            # files = {'image': img_encoded.tobytes()}
            async with session.post('http://localhost:5001/upload_image', data=files) as response:
                if response.status == 200:
                    response_data = await response.json()
                    if response_data.get('verified') and response_data.get('student_id'):
                        student_id = response_data['student_id']
                        self.find_signal.emit(student_id)
                    else:
                        self.error_signal.emit("No matching student found")
                else:
                    self.error_signal.emit("Failed to detect face")
                self.is_face_processed = False
    
    """
    def check_res(self,student_id):
        try:
            # Connect to database
            db_conn = connect_to_rds()
            cursor = db_conn.cursor()
            
            print(f"matching face found.{student_id}")
            today_date = datetime.date.today()
            # Query the reservations table for the reservation_id
            # cursor.execute(
                SELECT * FROM reservations 
                WHERE user_id = %s AND lab_id = %s AND date = %s AND verified = 1
                , (student_id, self.lab_id, today_date))
            reservations = cursor.fetchall()

            if not reservations:
                self.error_signal.emit("No reservation found for this ID.")
                return

            current_time = datetime.datetime.now()
            # Extract reservation details
            for reservation in reservations:
                reservation_id, date, time = reservation[0], reservation[3], reservation[4]
                reservation_time = datetime.datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
                time_diff = abs((current_time - reservation_time).total_seconds()) / 60

                if time_diff <= 5:
                    self.find_signal.emit(student_id)
                    cursor.execute(
                                "UPDATE reservations SET checked = 1 WHERE reservation_id = %s",
                                (reservation_id,)
                            )
                    db_conn.commit()
                    return
            #self.error_signal.emit("You are not within the valid reservation time.") 
                #return "You are not within the valid reservation time."
            self.error_signal.emit("You are not within the valid reservation time.")

        except Exception as e:
            print(f"Error in comparing faces: {str(e)}")

        finally:
            # self.is_face_processed = False
            if 'db_conn' in locals() and db_conn:
                db_conn.close()
"""
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
        QMessageBox.critical(self, "Error", message)
    
    def find_message(self, stu_id):
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


