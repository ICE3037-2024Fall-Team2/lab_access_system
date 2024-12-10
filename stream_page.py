from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import (
    QMainWindow, QLabel, QPushButton, QMessageBox, QHBoxLayout, QVBoxLayout, QFrame, QWidget
)
from PyQt5.QtGui import QPixmap, QImage
from pyzbar.pyzbar import decode
from custom_button import CustomButton2, CustomButton2_false
from camera import CameraManager
import datetime
from aws_connect import connect_to_rds
from unlock_page import UnlockWindow
import numpy as np
import cv2
import requests
import time

class StreamWindow(QMainWindow):
    def __init__(self, lab_id, lab_name):
        super().__init__()
        self.setWindowTitle("Unified Camera")
        self.setGeometry(100, 100, 720, 1080)

        self.camera_manager = CameraManager()
        self.mode = "qr"  

        self.face_cascade = cv2.CascadeClassifier('~/opencv_haarcascades/haarcascade_frontalface_default.xml')

        self.showFullScreen()
        self.lab_id = lab_id
        self.lab_name = lab_name
        self.is_qr_processed = False
        self.is_face_processed = False
        self.frame_counter = 1

        self.main_widget = QWidget(self)
        self.setCentralWidget(self.main_widget)

        # Camera Label
        #self.camera_frame = QFrame(self.main_widget)
        #self.camera_frame.setFixedSize(600, 560)
        self.camera_label = QLabel(self)
        self.camera_label.setGeometry(50, 50, 600, 560)
        self.camera_label.setStyleSheet("border: 1px solid black;")

        # Buttons
        self.bt_frame = QFrame(self.main_widget)
        self.bt_frame.setGeometry(50, 50, 400, 100)

        self.button_layout = QHBoxLayout(self.bt_frame)
        self.button_layout.setSpacing(10)

        # Face Detection Button
        self.face_button = CustomButton2("Facial Detection", self)
        self.face_button.clicked.connect(self.start_face_detection)
        self.button_layout.addWidget(self.face_button)

        # QR Code Recognition Button (Initially disabled)
        self.qr_button = CustomButton2_false("QR Code Recognition", self)
        self.qr_button.setEnabled(False)  # Disable the button to prevent interaction
        self.button_layout.addWidget(self.qr_button)

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


        # Layout Setup
        self.show()
        main_layout = QVBoxLayout(self.main_widget)
        main_layout.setSpacing(10)
        main_layout.setAlignment(Qt.AlignCenter)
        #main_layout.addWidget(self.camera_frame)
        main_layout.addWidget(self.camera_label)
        main_layout.addWidget(self.back_button)
        main_layout.addWidget(self.bt_frame)


        self.timer = QTimer(self)
        self.timer.timeout.connect(self.process_frame)
        self.timer.start(30) 

    def process_frame(self):
        frame = self.camera_manager.get_frame()
        frame = cv2.flip(frame, 1)

        height, width, channel = frame.shape
        step = channel * width
        q_image = QImage(frame.data, width, height, step, QImage.Format_BGR888)
        pixmap = QPixmap.fromImage(q_image)
        self.camera_label.setPixmap(pixmap)
                
        if self.mode == "qr":
            self.scan_qr_code(frame)
        elif self.mode == "face":
            self.frame_counter += 1
            self.detect_and_process_face(frame)

    def reset_popup_status(self):
        self.is_popup_open = False
        self.current_message_box = None
    
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
        
    """ For qr code detection """
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
            else:
                self.last_qr_warning_time = 0
                WARNING_INTERVAL = 2  
                if time() - self.last_qr_warning_time < WARNING_INTERVAL:
                    return
                self.last_qr_warning_time = time()
                QMessageBox.warning(self, "Error", "Not a valid QR-code.")

    def verify_reservation(self, reservation_id):
        try:
            # Connect to database
            db_conn = connect_to_rds()
            cursor = db_conn.cursor()

            # Query the reservations table for the reservation_id
            cursor.execute("SELECT * FROM reservations WHERE reservation_id = %s", (reservation_id,))
            reservation = cursor.fetchone()

            if not reservation:
                QMessageBox.warning(self, "Error", "No reservation found for this ID.")
                return

            # Extract reservation details
            lab_id_db, user_id, reservation_date, time, verified = reservation[1], reservation[2], reservation[3], reservation[4], reservation[5]

            # Check if the reservation is verified
            if verified != 1:
                QMessageBox.warning(self, "Unverified Reservation", "This reservation is not verified.")
                return

            # Check if the lab_id matches
            if lab_id_db != self.lab_id:
                QMessageBox.warning(self, "Wrong Lab", "The reservation is for a different lab.")
                return
            # Check if the reservation date is valid
            current_date = datetime.date.today()
            #reservation_date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
            print(reservation_date)
            if reservation_date != current_date:
                if reservation_date < current_date:
                    QMessageBox.warning(self, "Past Reservation", "This reservation date has passed.")
                else:
                    QMessageBox.warning(self, "Future Reservation", "This reservation is for a future date.")
                return

            # Check if the current time is within 5 minutes of the reservation time
            current_time = datetime.datetime.now().strftime("%H:%M")
            reservation_time = time

            current_time_obj = datetime.datetime.strptime(current_time, "%H:%M")
            reservation_time_obj = datetime.datetime.strptime(reservation_time, "%H:%M")
            # Allow a 5-minute window before and after the reservation time
            time_diff = abs((current_time_obj - reservation_time_obj).total_seconds()) / 60

            if time_diff <= 5:
                # Step 9: Unlock window and update 'checked' to 1
                self.unlock_window = UnlockWindow(self.lab_id, self.lab_id, user_id)
                self.unlock_window.show()
                self.close()
                
                cursor.execute(
                    "UPDATE reservations SET checked = 1 WHERE reservation_id = %s",
                    (reservation_id,)
                )
                db_conn.commit()
            else:
                QMessageBox.warning(self, "Not the Reservation Time", "You are not within the valid reservation time window.")
            
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"An error occurred: {str(e)}")
        finally:
            self.is_qr_processed = False
            if 'db_conn' in locals() and db_conn:
                db_conn.close()

    """ For face detection """
    def detect_and_process_face(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        if len(faces) > 0:
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

            self.compare_faces(frame)


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
                    self.find_message(student_id)
                else:
                    self.show_error_message("No matching student found")
            else:
                self.show_error_message("Failed to detect face")
        except Exception as e:
            self.show_error_message(f"Error occurred: {str(e)}")
        finally:
            self.is_face_processed = False

    def find_message(self, stu_id):
        if self.current_message_box:
            self.current_message_box.close()

        self.unlock_window = UnlockWindow(self.lab_id, self.lab_name, stu_id)
        self.unlock_window.show()
        self.close()
        

    """ For mode switch """
    def switch_to_qr(self):
        while self.button_layout.count():
            self.button_layout.layout().takeAt(0).widget().deleteLater()

        self.mode = "qr"
        self.is_qr_processed = False

        self.face_button = CustomButton2("Facial Detection", self)
        self.face_button.clicked.connect(self.start_face_detection)
        self.button_layout.addWidget(self.face_button)

        # QR Code Recognition Button (Initially disabled)
        self.qr_button = CustomButton2_false("QR Code Recognition", self)
        self.qr_button.setEnabled(False)  # Disable the button to prevent interaction
        self.button_layout.addWidget(self.qr_button)

        print("Switched to QR Code Recognition")

    def switch_to_face(self):
        while self.button_layout.count():
            self.button_layout.layout().takeAt(0).widget().deleteLater()

        self.mode = "face"
        self.is_face_processed = False
        print("Switched to Face Detection")

        self.face_button = CustomButton2_false("Facial Detection", self)
        self.qr_button.setEnabled(False)  # Disable the button to prevent interaction
        self.button_layout.addWidget(self.face_button)

        # QR Code Recognition Button (Initially disabled)
        self.qr_button = CustomButton2("QR Code Recognition", self)
        self.qr_button.clicked.connect(self.start_qr_recognition)
        self.button_layout.addWidget(self.qr_button)

    def go_back(self):
        from main import MainWindow
        self.timer.stop()
        self.camera_manager.close()
        self.main_window = MainWindow(self.lab_id, self.lab_name)
        self.main_window.show()
        self.close()

    def closeEvent(self, event):
        self.timer.stop()
        self.camera_manager.close()
        event.accept()
