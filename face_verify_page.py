
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import (
    QMainWindow, QLabel, QPushButton, QMessageBox, QHBoxLayout, QVBoxLayout, QFrame, QWidget
)
from PyQt5.QtGui import QPixmap, QImage
import cv2
import dlib
import numpy as np
from custom_button import CustomButton2,CustomButton2_false
import datetime
from deepface import DeepFace
import requests
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
from unlock_page import UnlockWindow
from aws_connect import connect_to_rds

class CameraWindow(QMainWindow):
    def __init__(self,lab_id,lab_name):
        super().__init__()
        self.setWindowTitle("Face_Camera")
        self.setGeometry(100, 100, 800, 600)
        self.lab_id = lab_id
        self.lab_name = lab_name
        self.is_face_processed = False

        self.s3_client = boto3.client(
            
        )

        self.bucket_name = "lrsys-bucket"

        self.main_widget = QWidget(self)
        self.setCentralWidget(self.main_widget)
        # Camera Label
        self.camera_frame = QFrame(self.main_widget)
        self.camera_frame.setFixedSize(700, 400)
        self.camera_label = QLabel(self)
        self.camera_label.setGeometry(50, 50, 700, 400)
        self.camera_label.setStyleSheet("border: 1px solid black;")

        
        # Buttons
        self.bt_frame = QFrame(self.main_widget)
        self.bt_frame.setFixedSize(700, 100)

        button_layout = QHBoxLayout(self.bt_frame)
        button_layout.setSpacing(20)
        self.face_button = CustomButton2_false("Facial Detection", self)
        self.face_button.setEnabled(False)
        # self.face_button.setGeometry(150, 500, 150, 80)
        button_layout.addWidget(self.face_button) 

        self.qr_button = CustomButton2("QR Code Recognition", self)
        # self.qr_button.setGeometry(500, 500, 200, 80)
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
        self.back_button.setGeometry(300, 550, 200, 40)
        # OpenCV Setup
        self.capture = cv2.VideoCapture(0)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.start_face_detection)
        self.timer.start(30)  # Update every 30ms
        self.show()

        main_layout = QVBoxLayout(self.main_widget)
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.camera_frame)
        main_layout.addWidget(self.bt_frame)

    def generate_presigned_url(self, photo_path):
        try:
            response = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': photo_path},
                ExpiresIn=3600 
            )
            return response
        except Exception as e:
            print(f"Error generating presigned URL for {photo_path}: {e}")
            return None

    def start_qr_recognition(self):
        from qr_verify_page import QR_CameraWindow
        self.capture.release()
        self.timer.stop()
        self.qr_window = QR_CameraWindow(self.lab_id,self.lab_name)
        self.qr_window.show()
        self.close()

    def update_frame(self, frame):
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channel = frame.shape
        step = channel * width
        q_image = QPixmap.fromImage(
            QImage(frame.data, width, height, step, QImage.Format_RGB888)
        )
        self.camera_label.setPixmap(q_image)

    def start_face_detection(self):
        if self.is_face_processed:
            return 
        ret, frame = self.capture.read()
        if ret:
            face_objects = DeepFace.extract_faces(frame, enforce_detection=False)
            if face_objects:
                for face in face_objects:
                    facial_area = face['facial_area']
                    x, y, w, h = facial_area['x'], facial_area['y'], facial_area['w'], facial_area['h']

                    # Draw rectangle around the detected face
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    self.update_frame(frame)
                    self.is_face_processed = True
                    QTimer.singleShot(1000, lambda: self.compare_faces(frame))
            else:
                print("No faces detected.")
                self.update_frame(frame)

    def compare_faces(self, frame):
        try:
            db_conn = connect_to_rds()
            cursor = db_conn.cursor()

            cursor.execute("SELECT id, photo_path FROM user_img")
            students = cursor.fetchall()  
            min_distance = float("inf")
            matched_student_id = None

            for student_id, photo_path in students:
                presigned_url = self.generate_presigned_url(photo_path)
                if not presigned_url:
                    continue

                response = requests.get(presigned_url)
                db_img_array = np.asarray(bytearray(response.content), dtype=np.uint8)
                db_img = cv2.imdecode(db_img_array, cv2.IMREAD_COLOR)

                if db_img is None:
                    print(f"Failed to decode image for student ID {student_id}. Skipping...")
                    continue

               
                result_original = DeepFace.verify(frame, db_img, model_name='ArcFace', enforce_detection=False)
                result_mirrored = DeepFace.verify(cv2.flip(frame, 1), db_img, model_name='ArcFace', enforce_detection=False)

                best_distance = min(result_original["distance"], result_mirrored["distance"])

                if best_distance < min_distance:
                    min_distance = best_distance
                    matched_student_id = student_id

            if matched_student_id:
                self.verify_reservation(matched_student_id)
            else:
                print("No matching face found.")
                return None, None

        except Exception as e:
            print(f"Error in comparing faces: {str(e)}")
            return None, None

        finally:
            if 'db_conn' in locals() and db_conn:
                db_conn.close()

    def verify_reservation(self, matched_student_id):
        try:
            # Connect to database
            db_conn = connect_to_rds()
            cursor = db_conn.cursor()
            today_date = datetime.date.today()
            # Query the reservations table for the reservation_id
            cursor.execute("""
            SELECT * FROM reservations 
            WHERE user_id = %s AND lab_id = %s AND date = %s AND verified = 1
            """, (matched_student_id, self.lab_id, today_date))
            
            reservations = cursor.fetchall()

            if not reservations:
                QMessageBox.warning(self, "Error", "No valid reservation found.")
                return
            
            current_time = datetime.datetime.now()
            for reservation in reservations:
                reservation_id, user_id, date, time = reservation[0], reservation[2], reservation[3], reservation[4]
                
                reservation_time = datetime.datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")

                time_diff = abs((current_time - reservation_time).total_seconds()) / 60

                if time_diff <= 5:
                    self.unlock_window = UnlockWindow(self.lab_id, self.lab_name, user_id)
                    self.unlock_window.show()
                    self.close()
                    
                    cursor.execute(
                        "UPDATE reservations SET checked = 1 WHERE reservation_id = %s",
                        (reservation_id,)
                    )
                    db_conn.commit()
                
            QMessageBox.warning(self, "Not the Reservation Time", "You are not within the valid reservation time.")
                
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"An error occurred: {str(e)}")
        finally:
            self.is_face_processed = False
            if 'db_conn' in locals() and db_conn:
                db_conn.close()
                

    def go_back(self):
        from main import MainWindow
        self.capture.release()
        self.timer.stop()
        self.main_window = MainWindow(self.lab_id,self.lab_name)
        self.main_window.show()
        self.close()

    def closeEvent(self, event):
        self.capture.release()
        self.timer.stop()
        event.accept()
