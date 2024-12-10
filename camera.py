from picamera2 import Picamera2
from libcamera import controls

class CameraManager:
    def __init__(self):
        self.picam2 = Picamera2()
        self.picam2.configure(self.picam2.create_preview_configuration(main={"format": "RGB888", "size": (640, 480)}))
        self.picam2.set_controls({"AfMode": controls.AfModeEnum.Continuous})
        self.picam2.start()

    def get_frame(self):
        return self.picam2.capture_array()

    def close(self):
        if self.picam2:
            self.picam2.stop()
            self.picam2.close()
