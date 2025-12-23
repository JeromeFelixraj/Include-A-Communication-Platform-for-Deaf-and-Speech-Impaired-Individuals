import sys
import requests
import cv2
import subprocess
import os
import time
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QMessageBox, QTextEdit, QScrollArea, QFrame
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ----------------------------
# Firebase Base URL
# ----------------------------
FIREBASE_URL = "https://include-6e31e-default-rtdb.firebaseio.com/"

# ==========================================================
# Optimized Standalone MediaPipe Script
# ==========================================================
MEDIAPIPE_SCRIPT = """import cv2
import mediapipe as mp
import numpy as np
from collections import deque
import time
import requests
import sys

FIREBASE_URL = "https://include-6e31e-default-rtdb.firebaseio.com/"

FINGER_SIGNS = {
    1: "HELLO", 2: "PLEASE", 3: "RPEPEAT THAT", 4: "I DID NOT UNDERSTAND", 5: "STOP",
    6: "THANKS", 7: "GREAT", 8: "GOT IT ", 9: "YES", 10: "GOOD"
}

def upload_to_firebase(session_code, student_name, sentence):
    try:
        response = requests.get(f"{FIREBASE_URL}/sessions.json", timeout=5)
        if response.status_code == 200:
            sessions = response.json() or {}
            for session_id, session_data in sessions.items():
                if session_data.get("session_code") == session_code:
                    update_data = {
                        "student_transcript": sentence,
                        "student_name": student_name,
                        "last_updated": int(time.time())
                    }
                    response = requests.patch(
                        f"{FIREBASE_URL}/sessions/{session_id}.json",
                        json=update_data,
                        timeout=3
                    )
                    if response.status_code == 200:
                        print(f"✅ Uploaded: {sentence}")
                    break
    except Exception as e:
        print(f"Firebase error: {e}")

if len(sys.argv) >= 3:
    session_code = sys.argv[1]
    student_name = sys.argv[2]
else:
    print("❌ No session code or student name provided")
    sys.exit(1)

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=2, min_detection_confidence=0.7)

def count_fingers_simple(hand_landmarks):
    tips_raised = []
    landmarks = hand_landmarks.landmark
    
    thumb_tip = landmarks[4]
    thumb_ip = landmarks[3]
    thumb_raised = thumb_tip.x < thumb_ip.x - 0.05 if thumb_tip.x < landmarks[0].x else thumb_tip.x > thumb_ip.x + 0.05
    tips_raised.append(1 if thumb_raised else 0)
    
    for tip_idx in [8, 12, 16, 20]:
        tip = landmarks[tip_idx]
        mcp = landmarks[tip_idx - 3]
        tips_raised.append(1 if tip.y < mcp.y else 0)
    
    return sum(tips_raised), tips_raised

sentence = ""
finger_count_queue = deque(maxlen=5)
last_finger_count = -1
repeat_count = 0
REPEAT_THRESHOLD = 10
last_upload_time = 0
upload_cooldown = 2

print("=== ASL Recognition Started ===")
print(f"Session: {session_code}, Student: {student_name}")

cap = None
try:
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Error: Could not open webcam")
        sys.exit(1)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        image = cv2.flip(frame, 1)
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        hand_results = hands.process(image_rgb)
        
        current_finger_count = 0
        
        if hand_results.multi_hand_landmarks:
            for hand_landmarks in hand_results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            
            total_fingers = 0
            for hand_landmarks in hand_results.multi_hand_landmarks:
                finger_count, _ = count_fingers_simple(hand_landmarks)
                total_fingers += finger_count
            
            current_finger_count = min(total_fingers, 10)
            finger_count_queue.append(current_finger_count)
            
            smoothed_count = max(set(finger_count_queue), key=finger_count_queue.count) if len(finger_count_queue) == 5 else current_finger_count
            sign_text = FINGER_SIGNS.get(smoothed_count, "UNKNOWN")
            
            cv2.putText(image, f"Fingers: {smoothed_count}", (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(image, f"Sign: {sign_text}", (30, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            cv2.putText(image, f"Student: {student_name}", (30, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            if smoothed_count == last_finger_count:
                repeat_count += 1
            else:
                repeat_count = 0
                last_finger_count = smoothed_count
            
            if repeat_count == REPEAT_THRESHOLD and smoothed_count > 0:
                sentence += sign_text + " "
                print(f"Recognized: {sign_text}")
                repeat_count = 0
                
                current_time = time.time()
                if current_time - last_upload_time >= upload_cooldown:
                    upload_to_firebase(session_code, student_name, sentence)
                    last_upload_time = current_time
                
        else:
            cv2.putText(image, "Show your hands", (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        cv2.putText(image, f"Sentence: {sentence}", (30, image.shape[0] - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(image, "Press 'q': quit", (image.shape[1] - 200, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(image, "'c': clear sentence", (image.shape[1] - 200, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        cv2.imshow("ASL Finger Recognition", image)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('c'):
            sentence = ""
            print("Sentence cleared")
            upload_to_firebase(session_code, student_name, sentence)

except Exception as e:
    print(f"Error during ASL recognition: {e}")

finally:
    if cap is not None:
        cap.release()
    if 'hands' in locals():
        hands.close()
    cv2.destroyAllWindows()
    print("✅ ASL Recognition closed properly")
    sys.exit(0)
"""

# ==========================================================
# Enhanced Firebase Listener Thread with Better Error Handling
# ==========================================================
class FirebaseListener(QThread):
    new_chat_message = pyqtSignal(dict)
    new_student_transcript = pyqtSignal(str)
    connection_status = pyqtSignal(bool)
    session_verified = pyqtSignal(bool)
    
    def __init__(self, session_code):
        super().__init__()
        self.session_code = session_code
        self.running = True
        self.session_id = None
        self.last_chat_count = 0
        self.last_transcript = ""
        
        # Enhanced session configuration
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
    def run(self):
        while self.running:
            try:
                # Test connection first
                response = self.session.get(f"{FIREBASE_URL}/.json", timeout=10)
                if response.status_code == 200:
                    self.connection_status.emit(True)
                    
                    # Now search for the session
                    sessions_response = self.session.get(f"{FIREBASE_URL}/sessions.json", timeout=10)
                    if sessions_response.status_code == 200:
                        sessions = sessions_response.json() or {}
                        session_found = False
                        
                        for session_id, session_data in sessions.items():
                            if session_data and session_data.get("session_code") == self.session_code:
                                self.session_id = session_id
                                session_found = True
                                self.session_verified.emit(True)
                                
                                # Check for chat updates
                                chat_messages = session_data.get("chat_messages", [])
                                current_chat_count = len(chat_messages)
                                
                                if current_chat_count > self.last_chat_count:
                                    new_messages = chat_messages[self.last_chat_count:]
                                    for message in new_messages:
                                        if message and message.get("sender") == "teacher":
                                            self.new_chat_message.emit(message)
                                    self.last_chat_count = current_chat_count
                                
                                # Check for student transcript updates
                                current_transcript = session_data.get("student_transcript", "")
                                if current_transcript != self.last_transcript:
                                    self.last_transcript = current_transcript
                                    if current_transcript:
                                        self.new_student_transcript.emit(current_transcript)
                                break
                        
                        if not session_found:
                            self.session_verified.emit(False)
                    else:
                        print(f"❌ Failed to fetch sessions: {sessions_response.status_code}")
                        self.connection_status.emit(False)
                else:
                    print(f"❌ Firebase connection failed: {response.status_code}")
                    self.connection_status.emit(False)
                    
            except requests.exceptions.Timeout:
                print("❌ Firebase connection timeout")
                self.connection_status.emit(False)
            except requests.exceptions.ConnectionError:
                print("❌ Firebase connection error - check internet")
                self.connection_status.emit(False)
            except Exception as e:
                print(f"Firebase listener error: {e}")
                self.connection_status.emit(False)
            
            QThread.msleep(1000)  # Reduced frequency to avoid rate limiting
    
    def stop(self):
        self.running = False

# ==========================================================
# PREMIUM UI/UX FOR STUDENT PAGE - APP STORE QUALITY
# ==========================================================
class MuteStudentPage(QWidget):
    def __init__(self):
        super().__init__()
        self.session_code = None
        self.student_name = None
        self.firebase_listener = None
        self.is_leaving = False
        self.mediapipe_process = None
        self.mediapipe_running = False
        self.mediapipe_monitor_timer = None
        
        self.init_ui()

    def init_ui(self):
        # Premium gradient background
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #667eea, stop:1 #764ba2);
            }
        """)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Scroll area for responsiveness
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: rgba(255,255,255,0.1);
                width: 6px;
                margin: 0px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,0.3);
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255,255,255,0.5);
            }
        """)

        # Central widget
        central_widget = QWidget()
        central_widget.setStyleSheet("background: transparent;")
        scroll_area.setWidget(central_widget)

        # Main layout for central widget
        central_layout = QVBoxLayout(central_widget)
        central_layout.setContentsMargins(20, 20, 20, 20)
        central_layout.setSpacing(0)

        # JOIN SCREEN - Premium Centered Card
        self.join_screen = QWidget()
        self.join_screen.setMinimumSize(450, 550)
        self.join_screen.setMaximumSize(500, 650)
        self.join_screen.setStyleSheet("""
            QWidget {
                background: white;
                border-radius: 24px;
                border: none;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1);
            }
        """)
        
        join_layout = QVBoxLayout(self.join_screen)
        join_layout.setContentsMargins(40, 50, 40, 50)
        join_layout.setSpacing(0)
        join_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # App icon with premium design
        icon_label = QLabel("👋")
        icon_label.setFont(QFont("Segoe UI", 72))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("margin-bottom: 20px;")
        join_layout.addWidget(icon_label)

        # Title
        title_label = QLabel("Join Classroom")
        title_label.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            color: #1a202c;
            margin-bottom: 8px;
        """)
        join_layout.addWidget(title_label)

        # Subtitle
        subtitle_label = QLabel("Connect with your teacher seamlessly")
        subtitle_label.setFont(QFont("Segoe UI", 14))
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("""
            color: #718096;
            margin-bottom: 40px;
            line-height: 1.4;
        """)
        join_layout.addWidget(subtitle_label)

        # Form container
        form_layout = QVBoxLayout()
        form_layout.setSpacing(20)

        # Name input
        name_container = QVBoxLayout()
        name_container.setSpacing(6)

        name_label = QLabel("Your Name")
        name_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Medium))
        name_label.setStyleSheet("color: #4a5568;")
        name_container.addWidget(name_label)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter your full name...")
        self.name_input.setFont(QFont("Segoe UI", 14))
        self.name_input.setMinimumHeight(50)
        self.name_input.setStyleSheet("""
            QLineEdit {
                background-color: #f8fafc;
                color: #2d3748;
                padding: 14px 18px;
                border-radius: 12px;
                border: 2px solid #e2e8f0;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #4299e1;
                background-color: #ffffff;
            }
            QLineEdit::placeholder {
                color: #a0aec0;
            }
        """)
        name_container.addWidget(self.name_input)
        form_layout.addLayout(name_container)

        # Session code input
        code_container = QVBoxLayout()
        code_container.setSpacing(6)

        code_label = QLabel("Session Code")
        code_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Medium))
        code_label.setStyleSheet("color: #4a5568;")
        code_container.addWidget(code_label)

        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("Enter 6-digit code...")
        self.code_input.setFont(QFont("Segoe UI", 14))
        self.code_input.setMinimumHeight(50)
        self.code_input.setStyleSheet("""
            QLineEdit {
                background-color: #f8fafc;
                color: #2d3748;
                padding: 14px 18px;
                border-radius: 12px;
                border: 2px solid #e2e8f0;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #4299e1;
                background-color: #ffffff;
            }
            QLineEdit::placeholder {
                color: #a0aec0;
            }
        """)
        code_container.addWidget(self.code_input)
        form_layout.addLayout(code_container)

        # Join button
        self.join_button = QPushButton("Join Session")
        self.join_button.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        self.join_button.setMinimumHeight(55)
        self.join_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.join_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4299e1, stop:1 #3182ce);
                color: white;
                border: none;
                border-radius: 12px;
                padding: 16px 24px;
                font-weight: bold;
                margin-top: 10px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3182ce, stop:1 #2b6cb0);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2b6cb0, stop:1 #2c5282);
            }
            QPushButton:disabled {
                background: #cbd5e0;
                color: #a0aec0;
            }
        """)
        self.join_button.clicked.connect(self.check_session)
        form_layout.addWidget(self.join_button)

        join_layout.addLayout(form_layout)
        join_layout.addStretch()

        # Status label
        self.status_label = QLabel("Enter your details to join the classroom")
        self.status_label.setFont(QFont("Segoe UI", 12))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("""
            color: #718096;
            padding: 16px;
            background-color: #f7fafc;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
            line-height: 1.4;
            margin-top: 20px;
        """)
        self.status_label.setWordWrap(True)
        join_layout.addWidget(self.status_label)

        # SESSION SCREEN - Premium Layout
        self.session_screen = QWidget()
        self.session_screen.setStyleSheet("background: transparent;")
        session_layout = QVBoxLayout(self.session_screen)
        session_layout.setContentsMargins(0, 0, 0, 0)
        session_layout.setSpacing(20)

        # Header with premium design
        header = QWidget()
        header.setFixedHeight(70)
        header.setStyleSheet("""
            QWidget {
                background: rgba(255, 255, 255, 0.98);
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(25, 12, 25, 12)

        # Session info
        session_info = QVBoxLayout()
        session_title = QLabel("Classroom Session")
        session_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        session_title.setStyleSheet("color: #2d3748;")
        session_info.addWidget(session_title)
        
        self.session_details = QLabel("")
        self.session_details.setFont(QFont("Segoe UI", 12))
        self.session_details.setStyleSheet("color: #718096;")
        session_info.addWidget(self.session_details)
        
        header_layout.addLayout(session_info)
        header_layout.addStretch()

        # Connection status
        self.connection_label = QLabel("🟢 Connected")
        self.connection_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        self.connection_label.setStyleSheet("""
            color: #22543d;
            background: rgba(72, 187, 120, 0.1);
            padding: 6px 12px;
            border-radius: 10px;
            border: 1px solid rgba(72, 187, 120, 0.2);
        """)
        header_layout.addWidget(self.connection_label)

        # Leave button
        leave_btn = QPushButton("Leave")
        leave_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        leave_btn.setFixedSize(80, 36)
        leave_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        leave_btn.setStyleSheet("""
            QPushButton {
                background-color: #e53e3e;
                color: white;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background-color: #c53030;
            }
        """)
        leave_btn.clicked.connect(self.leave_session)
        header_layout.addWidget(leave_btn)

        session_layout.addWidget(header)

        # Main content area - Fixed layout to prevent display issues
        content_widget = QWidget()
        content_widget.setStyleSheet("background: transparent;")
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(20)

        # Left column - Communication
        left_column = QVBoxLayout()
        left_column.setSpacing(20)

        # ASL Recognition Card
        asl_card = QFrame()
        asl_card.setFrameStyle(QFrame.Shape.NoFrame)
        asl_card.setStyleSheet("""
            QFrame {
                background: white;
                border-radius: 16px;
                border: none;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
            }
        """)
        asl_layout = QVBoxLayout(asl_card)
        asl_layout.setContentsMargins(25, 25, 25, 25)
        asl_layout.setSpacing(20)

        asl_title = QLabel("Sign Language Communication")
        asl_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        asl_title.setStyleSheet("color: #2d3748; margin-bottom: 5px;")
        asl_layout.addWidget(asl_title)

        # ASL Button
        self.show_signs_button = QPushButton("🎥 Start Camera for Sign Recognition")
        self.show_signs_button.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.show_signs_button.setMinimumHeight(55)
        self.show_signs_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.show_signs_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #ed8936, stop:1 #dd6b20);
                color: white;
                border: none;
                border-radius: 12px;
                padding: 16px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #dd6b20, stop:1 #c05621);
            }
            QPushButton:disabled {
                background: #cbd5e0;
                color: #a0aec0;
            }
        """)
        self.show_signs_button.clicked.connect(self.launch_mediapipe_asl)
        asl_layout.addWidget(self.show_signs_button)

        # ASL Status
        self.asl_status_label = QLabel("Ready to start sign language recognition")
        self.asl_status_label.setFont(QFont("Segoe UI", 12))
        self.asl_status_label.setStyleSheet("""
            color: #4a5568;
            padding: 16px;
            background: #f0fff4;
            border-radius: 12px;
            border: 2px solid #c6f6d5;
            line-height: 1.4;
        """)
        self.asl_status_label.setWordWrap(True)
        asl_layout.addWidget(self.asl_status_label)

        # Instructions
        instructions_card = QFrame()
        instructions_card.setFrameStyle(QFrame.Shape.NoFrame)
        instructions_card.setStyleSheet("""
            QFrame {
                background: #f8fafc;
                border-radius: 12px;
                border: 1px solid #e2e8f0;
            }
        """)
        instructions_layout = QVBoxLayout(instructions_card)
        instructions_layout.setContentsMargins(20, 20, 20, 20)
        instructions_layout.setSpacing(12)
        
        instructions_title = QLabel("How to Use Sign Recognition")
        instructions_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        instructions_title.setStyleSheet("color: #2d3748; margin-bottom: 8px;")
        instructions_layout.addWidget(instructions_title)
        
        instructions_text = QLabel(
            "• Click 'Start Camera for Sign Recognition'\n"
            "• Allow camera access when prompted\n"
            "• Show your hands clearly to the camera\n"
            "• Use finger signs (1-5 fingers) to communicate\n"
            "• Your signs will be translated automatically\n"
            "• Close the camera window when done"
        )
        instructions_text.setFont(QFont("Segoe UI", 11))
        instructions_text.setStyleSheet("color: #4a5568; line-height: 1.5;")
        instructions_layout.addWidget(instructions_text)
        
        asl_layout.addWidget(instructions_card)

        left_column.addWidget(asl_card)

        # Transcript Card
        transcript_card = QFrame()
        transcript_card.setFrameStyle(QFrame.Shape.NoFrame)
        transcript_card.setStyleSheet("""
            QFrame {
                background: white;
                border-radius: 16px;
                border: none;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
            }
        """)
        transcript_layout = QVBoxLayout(transcript_card)
        transcript_layout.setContentsMargins(25, 25, 25, 25)
        transcript_layout.setSpacing(15)
        
        transcript_title = QLabel("Your Translated Message")
        transcript_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        transcript_title.setStyleSheet("color: #2d3748;")
        transcript_layout.addWidget(transcript_title)
        
        self.transcript_display = QTextEdit()
        self.transcript_display.setReadOnly(True)
        self.transcript_display.setFont(QFont("Segoe UI", 12))
        self.transcript_display.setStyleSheet("""
            QTextEdit {
                background: #f0fff4;
                color: #22543d;
                border: 2px solid #9ae6b4;
                border-radius: 12px;
                padding: 16px;
                min-height: 120px;
                line-height: 1.4;
            }
        """)
        transcript_layout.addWidget(self.transcript_display)
        
        left_column.addWidget(transcript_card)

        content_layout.addLayout(left_column)

        # Right column - Chat
        right_column = QVBoxLayout()
        right_column.setSpacing(20)

        # Chat Card
        chat_card = QFrame()
        chat_card.setFrameStyle(QFrame.Shape.NoFrame)
        chat_card.setStyleSheet("""
            QFrame {
                background: white;
                border-radius: 16px;
                border: none;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
            }
        """)
        chat_layout = QVBoxLayout(chat_card)
        chat_layout.setContentsMargins(25, 25, 25, 25)
        chat_layout.setSpacing(20)
        
        chat_title = QLabel("Speak to Teacher")
        chat_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        chat_title.setStyleSheet("color: #2d3748;")
        chat_layout.addWidget(chat_title)

        # Chat Display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Segoe UI", 11))
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background: #f8fafc;
                color: #2d3748;
                border: 2px solid #e2e8f0;
                border-radius: 12px;
                padding: 16px;
                min-height: 250px;
                line-height: 1.4;
            }
        """)
        chat_layout.addWidget(self.chat_display)

        # Chat Input Area
        chat_input_layout = QHBoxLayout()
        chat_input_layout.setSpacing(12)
        
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Type your message...")
        self.chat_input.setFont(QFont("Segoe UI", 12))
        self.chat_input.setMinimumHeight(45)
        self.chat_input.setStyleSheet("""
            QLineEdit {
                background: white;
                color: #2d3748;
                border: 2px solid #e2e8f0;
                border-radius: 10px;
                padding: 12px 16px;
            }
            QLineEdit:focus {
                border-color: #4299e1;
                background: #f7fafc;
            }
            QLineEdit::placeholder {
                color: #a0aec0;
            }
        """)
        self.chat_input.returnPressed.connect(self.send_chat_message)
        chat_input_layout.addWidget(self.chat_input)
        
        self.send_chat_button = QPushButton("Send")
        self.send_chat_button.setFont(QFont("Segoe UI", 12, QFont.Weight.Medium))
        self.send_chat_button.setFixedSize(80, 45)
        self.send_chat_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_chat_button.setStyleSheet("""
            QPushButton {
                background-color: #4299e1;
                color: white;
                border-radius: 10px;
                border: none;
            }
            QPushButton:hover {
                background-color: #3182ce;
            }
        """)
        self.send_chat_button.clicked.connect(self.send_chat_message)
        chat_input_layout.addWidget(self.send_chat_button)
        
        chat_layout.addLayout(chat_input_layout)
        right_column.addWidget(chat_card)

        content_layout.addLayout(right_column)
        session_layout.addWidget(content_widget)

        # Add both screens to central layout
        central_layout.addWidget(self.join_screen, alignment=Qt.AlignmentFlag.AlignCenter)
        central_layout.addWidget(self.session_screen)
        self.session_screen.hide()

        # Add scroll area to main layout
        main_layout.addWidget(scroll_area)

    # ALL BACKEND METHODS REMAIN EXACTLY THE SAME - ONLY UI FIXED
    def check_session(self):
        name = self.name_input.text().strip()
        code = self.code_input.text().strip()
        
        if not name:
            self.show_error("Please enter your name")
            return
            
        if not code:
            self.show_error("Please enter a session code")
            return

        if len(code) != 6 or not code.isdigit():
            self.show_error("Please enter a valid 6-digit code")
            return

        self.student_name = name
        self.session_code = code
        self.join_button.setEnabled(False)
        self.join_button.setText("Joining...")
        self.status_label.setText("Connecting to classroom session...")
        self.status_label.setStyleSheet("""
            color: #d69e2e;
            padding: 16px;
            background-color: #fefcbf;
            border-radius: 12px;
            border: 2px solid #f6e05e;
        """)

        QTimer.singleShot(100, self._check_session_async)

    def _check_session_async(self):
        try:
            # Test Firebase connection first
            session = requests.Session()
            test_response = session.get(f"{FIREBASE_URL}/.json", timeout=10)
            
            if test_response.status_code != 200:
                self.show_error(f"Connection failed (Status: {test_response.status_code}). Please check your internet connection.")
                return

            # Now search for the session
            response = session.get(f"{FIREBASE_URL}/sessions.json", timeout=10)
            if response.status_code == 200:
                data = response.json() or {}
                session_found = False
                
                for session_id, session_data in data.items():
                    if session_data and session_data.get("session_code") == self.session_code:
                        session_found = True
                        # Update the session with student name immediately
                        update_data = {
                            "student_name": self.student_name,
                            "last_updated": int(time.time())
                        }
                        patch_response = session.patch(
                            f"{FIREBASE_URL}/sessions/{session_id}.json",
                            json=update_data,
                            timeout=5
                        )
                        if patch_response.status_code == 200:
                            print(f"✅ Student name '{self.student_name}' saved to session")
                            self.setup_live_session()
                        else:
                            self.show_error(f"Failed to join session (Error: {patch_response.status_code})")
                        break

                if not session_found:
                    self.show_error("Session not found. Please check the code and make sure your teacher has created the session.")
            else:
                self.show_error(f"Failed to fetch sessions (Error: {response.status_code})")

        except requests.exceptions.Timeout:
            self.show_error("Connection timeout. Please check your internet connection and try again.")
        except requests.exceptions.ConnectionError:
            self.show_error("Connection error. Please check your internet connection.")
        except Exception as e:
            self.show_error(f"Connection error: {str(e)}")

    def setup_live_session(self):
        # Switch to session screen
        self.join_screen.hide()
        self.session_screen.show()
        
        # Update session details
        self.session_details.setText(f"Session: {self.session_code} | Student: {self.student_name}")
        
        # Update status
        self.asl_status_label.setText("Ready to start sign language recognition")
        
        # Start Firebase listener
        QTimer.singleShot(200, self.start_firebase_listener)

    def show_error(self, message):
        """Show error message with modern styling"""
        self.status_label.setText(message)
        self.status_label.setStyleSheet("""
            color: #e53e3e;
            padding: 16px;
            background-color: #fed7d7;
            border-radius: 12px;
            border: 2px solid #feb2b2;
        """)
        self.join_button.setEnabled(True)
        self.join_button.setText("Join Session")

    def launch_mediapipe_asl(self):
        """Launch MediaPipe ASL recognition as separate process"""
        if self.mediapipe_running:
            QMessageBox.information(self, "Already Running", "ASL Recognition is already running. Please close the existing window first.")
            return
            
        try:
            # Save the MediaPipe script to a temporary file
            script_path = "mediapipe_asl_temp.py"
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(MEDIAPIPE_SCRIPT)
            
            print("Launching MediaPipe ASL Recognition...")
            self.mediapipe_running = True
            self.show_signs_button.setEnabled(False)
            self.show_signs_button.setText("🎥 Recognition Active...")
            
            # Launch the script with session code and student name as arguments
            self.mediapipe_process = subprocess.Popen([
                sys.executable, script_path, self.session_code, self.student_name
            ])
            
            self.asl_status_label.setText("🎥 Camera active - Show your hands to the camera to start signing!\n\nYour signs will be automatically translated and sent to your teacher.")
            self.asl_status_label.setStyleSheet("""
                color: #22543d;
                padding: 16px;
                background: #f0fff4;
                border-radius: 12px;
                border: 2px solid #9ae6b4;
            """)
            
            # Start monitoring the process
            self.start_mediapipe_monitoring()
            
        except Exception as e:
            print(f"Error launching MediaPipe: {e}")
            self.asl_status_label.setText("❌ Failed to start sign recognition. Please check if your camera is available.")
            self.asl_status_label.setStyleSheet("""
                color: #e53e3e;
                padding: 16px;
                background: #fed7d7;
                border-radius: 12px;
                border: 2px solid #feb2b2;
            """)
            self.mediapipe_running = False
            self.show_signs_button.setEnabled(True)
            self.show_signs_button.setText("🎥 Start Camera for Sign Recognition")

    def start_mediapipe_monitoring(self):
        """Start monitoring the MediaPipe process"""
        if self.mediapipe_monitor_timer:
            self.mediapipe_monitor_timer.stop()
        
        self.mediapipe_monitor_timer = QTimer()
        self.mediapipe_monitor_timer.timeout.connect(self.check_mediapipe_status)
        self.mediapipe_monitor_timer.start(1000)

    def check_mediapipe_status(self):
        """Check if MediaPipe process is still running"""
        if not self.mediapipe_running or not self.mediapipe_process:
            if self.mediapipe_monitor_timer:
                self.mediapipe_monitor_timer.stop()
            return
        
        return_code = self.mediapipe_process.poll()
        if return_code is not None:
            self.mediapipe_cleanup()
            
            if return_code == 0:
                self.asl_status_label.setText("✅ Sign recognition completed successfully")
            else:
                self.asl_status_label.setText("⚠️ Sign recognition session ended")
            
            print(f"✅ MediaPipe process ended with code: {return_code}")

    def mediapipe_cleanup(self):
        """Clean up MediaPipe resources"""
        self.mediapipe_running = False
        self.show_signs_button.setEnabled(True)
        self.show_signs_button.setText("🎥 Start Camera for Sign Recognition")
        
        if self.mediapipe_monitor_timer:
            self.mediapipe_monitor_timer.stop()
            self.mediapipe_monitor_timer = None
        
        try:
            if os.path.exists("mediapipe_asl_temp.py"):
                os.remove("mediapipe_asl_temp.py")
        except Exception as e:
            print(f"Error cleaning up temporary file: {e}")

    def send_chat_message(self):
        """Send chat message to teacher"""
        message = self.chat_input.text().strip()
        if not message:
            return
        
        self.chat_input.clear()
        timestamp = time.strftime("%H:%M:%S")
        self.chat_display.append(f'<div style="color: #2d3748; margin: 8px 0; padding: 12px; background: #f7fafc; border-radius: 10px;"><b>[{timestamp}] You:</b> {message}</div>')
        self.scroll_chat_to_bottom()
        
        QTimer.singleShot(10, lambda: self._send_chat_async(message))

    def _send_chat_async(self, message):
        """Fixed chat sending with proper error handling"""
        try:
            session = requests.Session()
            session.mount('http://', HTTPAdapter(max_retries=2))
            session.mount('https://', HTTPAdapter(max_retries=2))
            
            response = session.get(f"{FIREBASE_URL}/sessions.json", timeout=5)
            if response.status_code == 200:
                sessions = response.json() or {}
                
                for session_id, session_data in sessions.items():
                    if session_data and session_data.get("session_code") == self.session_code:
                        existing_chat = session_data.get("chat_messages", [])
                        
                        chat_data = {
                            "sender": "student",
                            "message": message,
                            "timestamp": int(time.time())
                        }
                        existing_chat.append(chat_data)
                        
                        update_data = {
                            "chat_messages": existing_chat,
                            "last_updated": int(time.time())
                        }
                        
                        patch_response = session.patch(
                            f"{FIREBASE_URL}/sessions/{session_id}.json", 
                            json=update_data, 
                            timeout=3
                        )
                        
                        if patch_response.status_code == 200:
                            print(f"✅ Chat message sent: {message}")
                        break
                    
        except Exception as e:
            print(f"Chat send error: {e}")

    def update_chat_display(self, message_data):
        """Update chat display with teacher's messages"""
        try:
            sender = message_data.get("sender", "")
            message = message_data.get("message", "")
            timestamp_int = message_data.get("timestamp", time.time())
            timestamp = time.strftime("%H:%M:%S", time.localtime(timestamp_int))
            
            if sender == "teacher":
                self.chat_display.append(f'<div style="color: #2b6cb0; margin: 8px 0; padding: 12px; background: #ebf8ff; border-radius: 10px;"><b>[{timestamp}] Teacher:</b> {message}</div>')
                self.scroll_chat_to_bottom()
        except Exception as e:
            print(f"Chat display update error: {e}")

    def update_transcript_display(self, transcript):
        """Update the transcript display with new content"""
        self.transcript_display.setText(transcript)

    def scroll_chat_to_bottom(self):
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def start_firebase_listener(self):
        if self.is_leaving:
            return
            
        try:
            self.firebase_listener = FirebaseListener(self.session_code)
            self.firebase_listener.connection_status.connect(self.update_connection_status)
            self.firebase_listener.new_chat_message.connect(self.update_chat_display)
            self.firebase_listener.new_student_transcript.connect(self.update_transcript_display)
            self.firebase_listener.session_verified.connect(self.on_session_verified)
            self.firebase_listener.start()
        except Exception as e:
            print(f"Error starting listener: {e}")

    def on_session_verified(self, verified):
        """Handle session verification status"""
        if not verified:
            self.connection_label.setText("🔴 Session Not Found")
            self.connection_label.setStyleSheet("""
                color: #2d3748;
                background: rgba(254, 215, 215, 0.1);
                padding: 6px 12px;
                border-radius: 10px;
                border: 1px solid rgba(254, 178, 178, 0.3);
            """)

    def update_connection_status(self, connected):
        if connected:
            self.connection_label.setText("🟢 Connected")
            self.connection_label.setStyleSheet("""
                color: #22543d;
                background: rgba(72, 187, 120, 0.1);
                padding: 6px 12px;
                border-radius: 10px;
                border: 1px solid rgba(72, 187, 120, 0.2);
            """)
        else:
            self.connection_label.setText("🔴 Connecting...")
            self.connection_label.setStyleSheet("""
                color: #2d3748;
                background: rgba(247, 203, 123, 0.1);
                padding: 6px 12px;
                border-radius: 10px;
                border: 1px solid rgba(247, 203, 123, 0.3);
            """)

    def leave_session(self):
        if self.is_leaving:
            return
            
        self.is_leaving = True
        
        # Stop MediaPipe process if running
        if self.mediapipe_process and self.mediapipe_running:
            try:
                self.mediapipe_process.terminate()
                self.mediapipe_process.wait(timeout=3)
                print("✅ MediaPipe process terminated")
            except subprocess.TimeoutExpired:
                try:
                    self.mediapipe_process.kill()
                    print("✅ MediaPipe process killed")
                except Exception as e:
                    print(f"❌ Failed to kill MediaPipe process: {e}")
            except Exception as e:
                print(f"Error stopping MediaPipe: {e}")
            finally:
                self.mediapipe_cleanup()
        
        # Stop Firebase listener
        if self.firebase_listener:
            try:
                self.firebase_listener.stop()
                self.firebase_listener.wait(1000)
                print("✅ Firebase listener stopped")
            except Exception as e:
                print(f"❌ Failed to stop Firebase listener: {e}")
        
        # Clean up temporary file
        try:
            if os.path.exists("mediapipe_asl_temp.py"):
                os.remove("mediapipe_asl_temp.py")
        except Exception as e:
            print(f"Error cleaning up temporary file: {e}")
        
        self.is_leaving = False
        # Reset to join screen
        self._reset_to_join_screen()

    def _reset_to_join_screen(self):
        """Reset the UI back to the join screen"""
        # Clear session data
        self.session_code = None
        self.student_name = None
        
        # Hide session screen, show join screen
        self.session_screen.hide()
        self.join_screen.show()
        
        # Reset inputs and status
        self.name_input.clear()
        self.code_input.clear()
        self.status_label.setText("Enter your details to join the classroom")
        self.status_label.setStyleSheet("""
            color: #718096;
            padding: 16px;
            background-color: #f7fafc;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
            line-height: 1.4;
            margin-top: 20px;
        """)
        
        # Reset join button
        self.join_button.setEnabled(True)
        self.join_button.setText("Join Session")
        
        # Reset other displays
        self.chat_display.clear()
        self.transcript_display.clear()
        self.asl_status_label.setText("Ready to start sign language recognition")

    def closeEvent(self, event):
        self.leave_session()
        event.accept()