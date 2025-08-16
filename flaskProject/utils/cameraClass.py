import cv2
import threading

class VideoCamera:
    def __init__(self, camera_id=0):
        self.cap = None
        self.lock = threading.Lock()  # 每个实例独立锁
        self.open_camera(camera_id)   # 初始化时自动打开摄像头

    def open_camera(self, camera_id):
        with self.lock:
            if self.cap is None or not self.cap.isOpened():
                self.cap = cv2.VideoCapture(camera_id)
                if not self.cap.isOpened():
                    raise RuntimeError(f"摄像头初始化失败，设备索引: {camera_id}")

    def get_frame(self):
        with self.lock:
            if self.cap is None:
                return None
            try:
                success, frame = self.cap.read()
                if not success:
                    return None
                # 帧处理（示例：添加文本）
                cv2.putText(frame, "Live Stream", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                ret, jpeg = cv2.imencode('.jpg', frame)
                return jpeg.tobytes()
            except cv2.error as e:
                print(f"OpenCV错误: {e}")
                return None

    def release(self):
        with self.lock:
            if self.cap is not None and self.cap.isOpened():
                self.cap.release()
                self.cap = None

    def __del__(self):
        self.release()  # 确保对象销毁时释放资源