from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import (
    QMainWindow, QLabel, QPushButton, QMessageBox, QHBoxLayout, QVBoxLayout, QFrame, QWidget
)
from PyQt5.QtGui import QPixmap, QImage
from picamera2 import Picamera2, Preview
from libcamera import controls
from pyzbar.pyzbar import decode
from custom_button import CustomButton2, CustomButton2_false
import datetime
from aws_connect import connect_to_rds
from unlock_page import UnlockWindow
import numpy as np
import cv2


class QR_CameraWindow(QMainWindow):
    def __init__(self, lab_id, lab_name):
        super().__init__()
        self.setWindowTitle("QR_Camera")
        self.showFullScreen()
        self.setGeometry(100, 100, 720, 1080)
        self.lab_id = lab_id
        self.lab_name = lab_name
        self.is_qr_processed = False
        self.is_popup_open = False
        self.current_message_box = None
        self.is_face_processed = False
        self.frame_counter = 1

        self.main_widget = QWidget(self)
        self.setCentralWidget(self.main_widget)

        # Camera Label
        #self.camera_frame = QFrame(self.main_widget)
        #self.camera_frame.setFixedSize(600, 560)
        #self.welcome_label = QLabel("Please show your QR-code", self)
        #self.welcome_label.setStyleSheet("font-size: 45px; font-weight: bold;")
        self.status_label = QLabel("Initializing camera...", self.main_widget)
        self.status_label.setStyleSheet("font-size: 18px; font-weight: bold; color: blue;")
        self.status_label.setAlignment(Qt.AlignCenter)
        
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
            font-size: 16px;
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
        self.picam2.configure(self.picam2.create_preview_configuration(main={"format": "RGB888","size": (640, 480)}))
        self.picam2.set_controls({"AfMode": controls.AfModeEnum.Continuous})
        self.picam2.start()
        self.status_label.setText("Please show your QR code") 

        # Timer for frame updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.scan_qr_code)
        self.timer.start(30)  # Update every 30ms
        
        # Layout Setup
        self.show()
        main_layout = QVBoxLayout(self.main_widget)
        main_layout.setSpacing(10)
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)
        #main_layout.addWidget(self.camera_frame)
        #main_layout.addWidget(self.welcome_label)
        main_layout.addWidget(self.camera_label)
        main_layout.addWidget(self.back_button)
        main_layout.addWidget(self.bt_frame)

    #def start_face_detection(self):
    #    from face_verify_page import CameraWindow
    #    if self.picam2:
    #        self.picam2.stop()
    #        self.picam2.close()
    #        self.picam2 = None
    #    self.timer.stop()
    #    self.face_window = CameraWindow(self.lab_id, self.lab_name)
    #    self.face_window.show()
    #    self.close()

    def update_frame(self,frame):
            #frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            height, width, channel = frame.shape
            step = channel * width
            q_image = QPixmap.fromImage(
                QImage(frame.data, width, height, step, QImage.Format_BGR888)
            )
            self.camera_label.setPixmap(q_image)
            # self.scan_qr_code(frame)

        
    def scan_qr_code(self):
        #ret, frame = self.capture.read()
        frame = self.picam2.capture_array()
        if frame is None: 
            return
        frame = cv2.flip(frame, 1)

        decoded_objects = decode(frame)
        for obj in decoded_objects:
            points = obj.polygon
            if len(points) == 4:
                pts = [tuple(point) for point in points]
                cv2.polylines(frame, [np.array(pts, dtype=np.int32)], True, (0, 255, 0), 3)
                self.status_label.setText("QR code detected. Identifying...") 
            #(x, y, w, h) = obj.rect
            #cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)
            qr_data = obj.data.decode('utf-8')
            # Step 1: Verify that the QR code data is a 15-digit number
            if len(qr_data) == 15 and qr_data.isdigit():
                reservation_id = qr_data
                #self.verify_reservation(reservation_id)
                if self.is_qr_processed == False:
                    self.is_qr_processed = True
                    QTimer.singleShot(100, lambda: self.verify_reservation(reservation_id))
                # Stop the scan after processing one QR code
                break
            else:
                QMessageBox.warning(self, "Error", "Not a valid QR-code.")
                self.status_label.setText("Please show your QR code") 
        self.update_frame(frame)

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
                self.status_label.setText("Please show your QR code") 
                return

            # Extract reservation details
            lab_id_db, user_id, reservation_date, time, verified = reservation[1], reservation[2], reservation[3], reservation[4], reservation[5]

            # Check if the reservation is verified
            if verified != 1:
                QMessageBox.warning(self, "Unverified Reservation", "This reservation is not verified.")
                self.status_label.setText("Please show your QR code") 
                return

            # Check if the lab_id matches
            if lab_id_db != self.lab_id:
                QMessageBox.warning(self, "Wrong Lab", "The reservation is for a different lab.")
                self.status_label.setText("Please show your QR code") 
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
                self.status_label.setText("Please show your QR code") 
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
                if self.picam2:
                    self.picam2.stop()
                    self.picam2.close()
                    self.picam2 = None
                self.timer.stop()
                self.unlock_window = UnlockWindow(self.lab_id, self.lab_name, user_id)
                self.unlock_window.show()
                self.close()
                
                cursor.execute(
                    "UPDATE reservations SET checked = 1 WHERE reservation_id = %s",
                    (reservation_id,)
                )
                db_conn.commit()
            else:
                QMessageBox.warning(self, "Not Now","Outside the reservation time window")
                self.status_label.setText("Please show your QR code") 
            
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"An error occurred: {str(e)}")
        finally:
            self.is_qr_processed = False
            if 'db_conn' in locals() and db_conn:
                db_conn.close()

    def start_face_detection(self):
        from face_verify_page import CameraWindow
        if self.picam2:
            self.picam2.stop()
            self.picam2.close()
            self.picam2 = None
        self.timer.stop()
        self.face_window = CameraWindow(self.lab_id,self.lab_name)
        self.face_window.show()
        QTimer.singleShot(80, self.close)

    def go_back(self):
        from main import MainWindow
        if self.picam2:
            self.picam2.stop()
            self.picam2.close()
            self.picam2 = None
        self.timer.stop()
        self.main_window = MainWindow(self.lab_id, self.lab_name)
        self.main_window.show()
        self.close()

    def closeEvent(self, event):
        if self.picam2:
            self.picam2.stop()
            self.picam2.close()
            self.picam2 = None
        self.timer.stop()
        event.accept()
