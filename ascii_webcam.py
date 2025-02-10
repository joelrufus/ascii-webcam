import sys
import cv2
import numpy as np
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, 
    QSizePolicy, QSpacerItem, QDialog, QSlider, QFormLayout
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QImage, QPixmap, QFont, QColor, QPainter, QLinearGradient


class GradientHeader(QLabel):
    def paintEvent(self, event):
        painter = QPainter(self)
        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0, QColor(106, 17, 203))
        gradient.setColorAt(1, QColor(37, 117, 252))
        painter.fillRect(event.rect(), gradient)
        painter.setPen(Qt.GlobalColor.white)
        painter.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        painter.drawText(20, 40, "EMOJI VISION PRO 9000")


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advanced Settings")
        self.setFixedSize(300, 200)

        layout = QFormLayout()

        self.emoji_density = QSlider(Qt.Orientation.Horizontal)
        self.emoji_density.setRange(5, 100)
        self.emoji_density.setValue(40)

        self.brightness = QSlider(Qt.Orientation.Horizontal)
        self.brightness.setRange(-100, 100)
        self.brightness.setValue(0)

        self.sensitivity = QSlider(Qt.Orientation.Horizontal)
        self.sensitivity.setRange(1, 100)
        self.sensitivity.setValue(30)

        layout.addRow("Emoji Density:", self.emoji_density)
        layout.addRow("Brightness:", self.brightness)
        layout.addRow("Sensitivity:", self.sensitivity)

        self.setLayout(layout)


class EmojiWebcam(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Emoji Vision Pro - Joel Rufus")
        self.setGeometry(100, 100, 1200, 800)
        self.EMOJI_MAP = [
            "🌑", "🌒", "🌓", "🌔", "🌕", "⭐", "🌟", "💫", "✨",
            "🔥", "💥", "☀️", "🌞", "◼️", "◻️", "⬛", "⬜",
            "🎮", "👾", "🕹️", "😀", "😲", "👀", "👄", "👅"
        ]
        self.setup_ui()
        self.setup_webcam()
        self.setup_styles()

        # Emoji display settings
        self.emoji_density = 40  # Initial density value (number of emoji columns)
        self.font_size = 14
        self.sensitivity_threshold = 30  # Sensitivity slider value (1-100)
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.prev_frame = None  # For motion detection

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.header = GradientHeader()
        self.header.setFixedHeight(60)
        main_layout.addWidget(self.header)

        content_layout = QHBoxLayout()
        control_panel = QVBoxLayout()
        control_panel.setContentsMargins(20, 20, 20, 20)

        self.mode_btn = self.create_button("🎥 Toggle View Mode", self.toggle_style)
        self.record_btn = self.create_button("⏺️ Start Recording", self.toggle_recording)
        self.settings_btn = self.create_button("⚙️ Advanced Settings", self.show_settings)

        control_panel.addWidget(self.mode_btn)
        control_panel.addWidget(self.record_btn)
        control_panel.addWidget(self.settings_btn)
        control_panel.addSpacerItem(
            QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )

        display_panel = QVBoxLayout()
        self.display_label = QLabel()
        self.display_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.display_label.setWordWrap(True)
        self.display_label.setStyleSheet("""
            background-color: #1a1a1a;
            border-radius: 15px;
            padding: 20px;
        """)

        self.stats_label = QLabel("FPS: -\nResolution: -")
        self.stats_label.setStyleSheet("""
            color: white;
            background-color: rgba(0, 0, 0, 150);
            padding: 10px;
            border-radius: 5px;
        """)
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

        display_panel.addWidget(self.display_label)
        display_panel.addWidget(self.stats_label)

        content_layout.addLayout(control_panel, 1)
        content_layout.addLayout(display_panel, 3)
        main_layout.addLayout(content_layout)
        self.setLayout(main_layout)

        self.recording_anim = QPropertyAnimation(self.record_btn, b"styleSheet")
        self.recording_anim.setDuration(1000)
        self.recording_anim.setLoopCount(-1)

    def create_button(self, text, callback):
        btn = QPushButton(text)
        btn.setFixedHeight(45)
        btn.clicked.connect(callback)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return btn

    def setup_styles(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #121212;
                color: #ffffff;
                font-family: 'Segoe UI';
            }
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                border: 2px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                text-align: left;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
                border-color: rgba(255, 255, 255, 0.3);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.05);
            }
        """)

    def setup_webcam(self):
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.show_error("Webcam not found!")

        self.modes = ["emoji", "normal", "edges"]
        self.current_mode = 0
        self.recording = False
        self.frame_count = 0
        self.fps = 0

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)
        self.fps_timer = QTimer()
        self.fps_timer.timeout.connect(self.update_fps)
        self.fps_timer.start(1000)

    def update_fps(self):
        self.fps = self.frame_count
        self.frame_count = 0
        self.update_stats()

    def update_stats(self):
        res = f"{int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}"
        self.stats_label.setText(f"FPS: {self.fps}\nResolution: {res}")

    def toggle_style(self):
        self.current_mode = (self.current_mode + 1) % len(self.modes)
        self.animate_mode_change()

    def animate_mode_change(self):
        anim = QPropertyAnimation(self.display_label, b"geometry")
        anim.setDuration(300)
        anim.setEasingCurve(QEasingCurve.Type.OutBack)
        current_geo = self.display_label.geometry()
        anim.setStartValue(current_geo.adjusted(20, 20, -20, -20))
        anim.setEndValue(current_geo)
        anim.start()

    def toggle_recording(self):
        self.recording = not self.recording
        if self.recording:
            self.start_recording_animation()
            self.record_btn.setText("⏹️ Stop Recording")
        else:
            self.recording_anim.stop()
            self.record_btn.setStyleSheet("")
            self.record_btn.setText("⏺️ Start Recording")

    def start_recording_animation(self):
        self.recording_anim.setStartValue("background-color: rgba(255, 0, 0, 0.3);")
        self.recording_anim.setEndValue("background-color: rgba(255, 0, 0, 0.8);")
        self.recording_anim.start()

    def show_settings(self):
        settings_dialog = SettingsDialog(self)
        if settings_dialog.exec():
            self.emoji_density = settings_dialog.emoji_density.value()
            self.sensitivity_threshold = settings_dialog.sensitivity.value()
            self.font_size = int(np.interp(self.emoji_density, [5, 100], [24, 8]))

    def show_error(self, message):
        error_label = QLabel(f"❌ {message}")
        error_label.setStyleSheet("color: #ff4444; font-size: 18px;")
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(error_label)

    def convert_to_emojis(self, frame):
        try:
            # Convert to grayscale and enhance contrast
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.equalizeHist(gray)
            # Detect faces in the frame
            faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)

            motion_mask = None
            if self.prev_frame is not None:
                frame_diff = cv2.absdiff(self.prev_frame, gray)
                _, motion_mask = cv2.threshold(frame_diff, 30, 255, cv2.THRESH_BINARY)
            self.prev_frame = gray.copy()

            cols = self.emoji_density
            rows = int(cols * (frame.shape[0] / frame.shape[1]))
            small_frame = cv2.resize(gray, (cols, rows))

            emoji_frame = []
            # Determine block size in the original frame for each emoji cell
            block_height = frame.shape[0] // rows
            block_width = frame.shape[1] // cols

            # Normalize sensitivity threshold to the 0-255 range.
            # (Assumes sensitivity slider (1-100) mapped to 0-255)
            motion_thresh = (self.sensitivity_threshold / 100.0) * 255

            for y in range(rows):
                emoji_row = []
                for x in range(cols):
                    # Calculate the top-left coordinate in the original frame for this block
                    block_x = x * block_width
                    block_y = y * block_height

                    # Determine if the block lies inside any detected face
                    in_face = any(
                        (fx < block_x < fx + fw) and (fy < block_y < fy + fh)
                        for (fx, fy, fw, fh) in faces
                    )
                    base_value = small_frame[y, x]

                    # Compute average motion intensity for the block, if available
                    if motion_mask is not None:
                        block_motion = motion_mask[
                            block_y:block_y + block_height,
                            block_x:block_x + block_width
                        ]
                        motion_intensity = np.mean(block_motion)
                    else:
                        motion_intensity = 0

                    # Decide which emoji to use based on face and motion information
                    if in_face:
                        if motion_intensity > motion_thresh:
                            # Head is moving—show a special emoji (here: "😲")
                            emoji = "😲"
                        else:
                            # Face present but little motion—add a small offset
                            emoji_index = min(
                                int((base_value / 255) * (len(self.EMOJI_MAP) - 1)) + 2,
                                len(self.EMOJI_MAP) - 1
                            )
                            emoji = self.EMOJI_MAP[emoji_index]
                    else:
                        if motion_intensity > motion_thresh:
                            emoji_index = min(
                                int((base_value / 255) * (len(self.EMOJI_MAP) - 1)) + 3,
                                len(self.EMOJI_MAP) - 1
                            )
                            emoji = self.EMOJI_MAP[emoji_index]
                        else:
                            emoji_index = min(
                                int((base_value / 255) * (len(self.EMOJI_MAP) - 1)),
                                len(self.EMOJI_MAP) - 1
                            )
                            emoji = self.EMOJI_MAP[emoji_index]

                    emoji_row.append(emoji)
                emoji_frame.append("".join(emoji_row))
            return "\n".join(emoji_frame)
        except Exception as e:
            print(f"Enhanced conversion error: {str(e)}")
            return "⚠️ Camera Error ⚠️"

    def update_frame(self):
        try:
            ret, frame = self.cap.read()
            self.frame_count += 1

            if not ret:
                self.show_error("Frame capture failed!")
                return

            if self.modes[self.current_mode] == "emoji":
                text = self.convert_to_emojis(frame)
                self.display_label.clear()
                self.display_label.setFont(QFont("Segoe UI Emoji", self.font_size))
                self.display_label.setText(text)
            else:
                if self.modes[self.current_mode] == "edges":
                    frame = cv2.Canny(frame, 100, 200)
                    frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)

                h, w, ch = frame.shape
                bytes_per_line = ch * w
                q_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                self.display_label.setPixmap(
                    QPixmap.fromImage(
                        q_img.scaled(
                            self.display_label.width() - 40,
                            self.display_label.height() - 40,
                            Qt.AspectRatioMode.KeepAspectRatio,
                        )
                    )
                )
        except Exception as e:
            print(f"Frame update error: {str(e)}")
            self.show_error("Camera processing error!")

    def closeEvent(self, event):
        self.cap.release()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EmojiWebcam()
    window.show()
    sys.exit(app.exec())
