import queue
import sounddevice as sd
import whisper  # Changed from vosk import
import numpy as np
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                            QLineEdit, QMessageBox, QStackedWidget, QTextEdit, QScrollArea,
                            QFrame)
from PyQt6.QtGui import QFont, QPalette, QColor
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
import json, random, requests, time
import win32com.client
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import threading

FIREBASE_URL = "https://include-6e31e-default-rtdb.firebaseio.com/"

# Disable SSL warnings and configure for better connectivity
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Whisper Model - Initialize empty, will load later
whisper_model = None
audio_queue = queue.Queue()

# ==========================================================
# High-Performance Text-to-Speech Engine using win32com
# ==========================================================
class TextToSpeechEngine:
    def __init__(self):
        self.speaker = win32com.client.Dispatch("SAPI.SpVoice")
        self.word_queue = queue.Queue()
        self.is_speaking = False
        self.running = True
        self.processing_thread = None
        self.start_processing()
        
    def start_processing(self):
        """Start the background processing thread"""
        self.processing_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.processing_thread.start()
        
    def _process_queue(self):
        """Process the word queue in background thread"""
        while self.running:
            try:
                if not self.word_queue.empty() and not self.is_speaking:
                    word = self.word_queue.get_nowait()
                    self.is_speaking = True
                    try:
                        # Speak the word using win32com - this is non-blocking!
                        self.speaker.Speak(word, 1)  # 1 = async speak
                        # Wait a bit for the speech to complete
                        time.sleep(0.5 + len(word) * 0.1)  # Dynamic delay based on word length
                    except Exception as e:
                        print(f"TTS Error: {e}")
                    finally:
                        self.is_speaking = False
                time.sleep(0.05)  # Small delay to prevent CPU overload
            except:
                time.sleep(0.1)
        
    def speak(self, word):
        """Add word to queue for speaking - NON-BLOCKING"""
        if word.strip() and len(word.strip()) > 1:
            self.word_queue.put(word.strip())
            
    def stop(self):
        """Stop the TTS engine"""
        self.running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=1.0)

# ==========================================================
# Enhanced Firebase Student Transcript Listener with Chat
# ==========================================================
class StudentTranscriptListener(QThread):
    new_transcript = pyqtSignal(str)
    new_chat_message = pyqtSignal(dict)  # Emit chat message as dict
    connection_status = pyqtSignal(bool)
    student_info_updated = pyqtSignal(str)  # Emit student name
    
    def __init__(self, session_id):
        super().__init__()
        self.session_id = session_id
        self.running = True
        self.last_transcript = ""
        self.last_chat_count = 0
        self.last_chat_message = ""  # Track last chat message to avoid duplicates
        self.student_name = "Student"  # Default name
        
    def run(self):
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        while self.running:
            try:
                response = session.get(
                    f"{FIREBASE_URL}/sessions/{self.session_id}.json",
                    timeout=10,
                    verify=False
                )
                if response.status_code == 200:
                    self.connection_status.emit(True)
                    session_data = response.json() or {}
                    
                    # Check for student name updates
                    current_student_name = session_data.get("student_name", "Student")
                    if current_student_name != self.student_name:
                        self.student_name = current_student_name
                        self.student_info_updated.emit(self.student_name)
                    
                    # Check for student transcript updates
                    student_transcript = session_data.get("student_transcript", "")
                    if student_transcript and student_transcript != self.last_transcript:
                        self.last_transcript = student_transcript
                        self.new_transcript.emit(student_transcript)
                    
                    # Check for chat updates
                    chat_messages = session_data.get("chat_messages", [])
                    current_chat_count = len(chat_messages)
                    
                    if current_chat_count > self.last_chat_count:
                        # New messages detected
                        new_messages = chat_messages[self.last_chat_count:]
                        for message in new_messages:
                            # Only emit student messages to avoid echoing teacher's own messages
                            if message.get("sender") == "student":
                                current_message = message.get("message", "")
                                # Avoid emitting duplicate messages
                                if current_message != self.last_chat_message:
                                    self.last_chat_message = current_message
                                    self.new_chat_message.emit(message)
                        self.last_chat_count = current_chat_count
                        
                else:
                    self.connection_status.emit(False)
                    
            except Exception as e:
                print(f"Firebase listener: {e}")
                self.connection_status.emit(False)
            
            QThread.msleep(300)
    
    def stop(self):
        self.running = False

# ==========================================================
# Flutter-Style Session Creation Page
# ==========================================================
class SessionCreationPage(QWidget):
    session_created = pyqtSignal(str, str)  # session_id, session_code
    
    def __init__(self):
        super().__init__()
        self.session = self._create_session()
        self.init_ui()

    def _create_session(self):
        """Create a requests session with proper retry strategy"""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def init_ui(self):
        # Main layout with Flutter-style background
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #E3F2FD, stop:1 #BBDEFB);
            }
        """)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # App Bar
        app_bar = QWidget()
        app_bar.setFixedHeight(80)
        app_bar.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2196F3, stop:1 #1976D2);
                border: none;
            }
        """)
        app_bar_layout = QHBoxLayout(app_bar)
        app_bar_layout.setContentsMargins(30, 15, 30, 15)
        
        # App title
        title_layout = QHBoxLayout()
        title_icon = QLabel("🎓")
        title_icon.setFont(QFont("Segoe UI", 24))
        title_text = QLabel("Include")
        title_text.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        title_text.setStyleSheet("color: white; margin-left: 10px;")
        title_layout.addWidget(title_icon)
        title_layout.addWidget(title_text)
        app_bar_layout.addLayout(title_layout)
        app_bar_layout.addStretch()
        
        main_layout.addWidget(app_bar)

        # Content area
        content_widget = QWidget()
        content_widget.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(30, 40, 30, 40)
        content_layout.setSpacing(0)

        # Centered card
        card = QWidget()
        card.setMaximumWidth(500)
        card.setStyleSheet("""
            QWidget {
                background: white;
                border-radius: 20px;
                border: none;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 40, 40, 40)
        card_layout.setSpacing(0)

        # Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(20)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_label = QLabel("🚀")
        icon_label.setFont(QFont("Segoe UI", 48))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(icon_label)

        title_label = QLabel("Create New Session")
        title_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #1976D2; margin-bottom: 8px;")
        header_layout.addWidget(title_label)

        subtitle_label = QLabel("Start an inclusive learning session with your student")
        subtitle_label.setFont(QFont("Segoe UI", 14))
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("color: #757575; margin-bottom: 40px; line-height: 1.4;")
        subtitle_label.setWordWrap(True)
        header_layout.addWidget(subtitle_label)

        card_layout.addLayout(header_layout)

        # Form section
        form_layout = QVBoxLayout()
        form_layout.setSpacing(25)

        # Input field
        input_container = QVBoxLayout()
        input_container.setSpacing(8)

        name_label = QLabel("Session Name")
        name_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Medium))
        name_label.setStyleSheet("color: #424242;")
        input_container.addWidget(name_label)

        self.session_input = QLineEdit()
        self.session_input.setPlaceholderText("Enter a name for your session...")
        self.session_input.setFont(QFont("Segoe UI", 13))
        self.session_input.setMinimumHeight(52)
        self.session_input.setStyleSheet("""
            QLineEdit {
                background-color: #FAFAFA;
                color: #212121;
                padding: 16px 20px;
                border-radius: 12px;
                border: 2px solid #E0E0E0;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #2196F3;
                background-color: #FFFFFF;
            }
            QLineEdit::placeholder {
                color: #9E9E9E;
            }
        """)
        input_container.addWidget(self.session_input)
        form_layout.addLayout(input_container)

        # Create button
        self.create_button = QPushButton("Create Session")
        self.create_button.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.create_button.setMinimumHeight(54)
        self.create_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.create_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2196F3, stop:1 #1976D2);
                color: white;
                border: none;
                border-radius: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1976D2, stop:1 #1565C0);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1565C0, stop:1 #0D47A1);
            }
            QPushButton:disabled {
                background: #BDBDBD;
                color: #9E9E9E;
            }
        """)
        self.create_button.clicked.connect(self.create_session)
        form_layout.addWidget(self.create_button)

        card_layout.addLayout(form_layout)
        card_layout.addSpacing(30)

        # Status area
        self.status_label = QLabel("Ready to create your session")
        self.status_label.setFont(QFont("Segoe UI", 12))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("""
            color: #757575;
            padding: 16px;
            background-color: #F5F5F5;
            border-radius: 12px;
            border: 1px solid #EEEEEE;
            line-height: 1.4;
        """)
        self.status_label.setWordWrap(True)
        card_layout.addWidget(self.status_label)

        # Success section (initially hidden)
        self.success_widget = QWidget()
        self.success_widget.setStyleSheet("background: transparent;")
        success_layout = QVBoxLayout(self.success_widget)
        success_layout.setSpacing(25)
        success_layout.setContentsMargins(0, 0, 0, 0)

        success_icon = QLabel("✅")
        success_icon.setFont(QFont("Segoe UI", 48))
        success_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        success_layout.addWidget(success_icon)

        success_title = QLabel("Session Created!")
        success_title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        success_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        success_title.setStyleSheet("color: #1976D2; margin-bottom: 8px;")
        success_layout.addWidget(success_title)

        success_subtitle = QLabel("Share this code with your student to begin")
        success_subtitle.setFont(QFont("Segoe UI", 14))
        success_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        success_subtitle.setStyleSheet("color: #757575; margin-bottom: 30px;")
        success_layout.addWidget(success_subtitle)

        # Code display
        code_card = QWidget()
        code_card.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #E8F5E8, stop:1 #C8E6C9);
                border-radius: 16px;
                border: 2px solid #4CAF50;
            }
        """)
        code_layout = QVBoxLayout(code_card)
        code_layout.setContentsMargins(30, 25, 30, 25)

        code_title = QLabel("Session Code")
        code_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Medium))
        code_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        code_title.setStyleSheet("color: #2E7D32; margin-bottom: 8px;")
        code_layout.addWidget(code_title)

        self.session_code_label = QLabel("")
        self.session_code_label.setFont(QFont("Segoe UI", 32, QFont.Weight.Bold))
        self.session_code_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.session_code_label.setStyleSheet("""
            color: #1B5E20;
            letter-spacing: 8px;
            margin: 12px 0;
        """)
        code_layout.addWidget(self.session_code_label)

        code_hint = QLabel("Your student will use this 6-digit code to join")
        code_hint.setFont(QFont("Segoe UI", 11))
        code_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        code_hint.setStyleSheet("color: #4CAF50; margin-top: 8px;")
        code_layout.addWidget(code_hint)

        success_layout.addWidget(code_card)

        # Continue button
        self.continue_button = QPushButton("Enter Classroom")
        self.continue_button.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.continue_button.setMinimumHeight(54)
        self.continue_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.continue_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4CAF50, stop:1 #43A047);
                color: white;
                border: none;
                border-radius: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #43A047, stop:1 #388E3C);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #388E3C, stop:1 #2E7D32);
            }
        """)
        self.continue_button.clicked.connect(self.continue_to_session)
        success_layout.addWidget(self.continue_button)

        card_layout.addWidget(self.success_widget)
        self.success_widget.hide()

        content_layout.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(content_widget)

        self.setLayout(main_layout)

    def create_session(self):
        session_name = self.session_input.text().strip()
        if not session_name:
            self.show_error("Please enter a session name")
            return

        # Disable form and show loading state
        self.create_button.setEnabled(False)
        self.create_button.setText("Creating...")
        self.session_input.setEnabled(False)
        
        self.status_label.setText("Setting up your virtual classroom...")
        self.status_label.setStyleSheet("""
            color: #F57C00;
            padding: 16px;
            background-color: #FFF3E0;
            border-radius: 12px;
            border: 1px solid #FFB74D;
        """)

        # Generate session code and create in Firebase
        session_code = str(random.randint(100000, 999999))
        session_id = self.push_to_firebase(session_name, session_code)
        
        if session_id:
            self.session_id = session_id
            self.session_code = session_code
            
            # Hide form elements and show success state
            self.session_input.hide()
            self.create_button.hide()
            self.status_label.hide()
            
            # Show session code
            self.session_code_label.setText(session_code)
            self.success_widget.show()
            
        else:
            self.show_error("Unable to create session. Please check your connection and try again.")
            self.create_button.setEnabled(True)
            self.create_button.setText("Create Session")
            self.session_input.setEnabled(True)

    def show_error(self, message):
        """Show error message with proper styling"""
        self.status_label.setText(f"⚠️ {message}")
        self.status_label.setStyleSheet("""
            color: #D32F2F;
            padding: 16px;
            background-color: #FFEBEE;
            border-radius: 12px;
            border: 1px solid #FFCDD2;
        """)

    def push_to_firebase(self, session_name, session_code):
        """Push session data to Firebase with improved error handling"""
        data = {
            "session_code": session_code,
            "session_name": session_name,
            "status": "active",
            "current_transcript": "",
            "student_transcript": "Student has not started signing yet...",
            "student_name": "Waiting for student...",
            "chat_messages": [],
            "created_at": time.time(),
            "last_updated": time.time()
        }
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.session.post(
                    f"{FIREBASE_URL}/sessions.json", 
                    json=data,
                    timeout=10,
                    verify=False
                )
                print(f"Firebase response status: {response.status_code}")
                print(f"Firebase response text: {response.text}")
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"Session created successfully: {result['name']}")
                    return result['name']
                else:
                    print(f"Firebase error: {response.status_code} - {response.text}")
                    
            except requests.exceptions.Timeout:
                print(f"Attempt {attempt + 1}: Firebase timeout")
            except requests.exceptions.ConnectionError as e:
                print(f"Attempt {attempt + 1}: Connection error - {e}")
            except Exception as e:
                print(f"Attempt {attempt + 1}: Unexpected error - {e}")
            
            # Wait before retrying
            if attempt < max_retries - 1:
                time.sleep(1)
        
        print("All Firebase connection attempts failed")
        return None

    def continue_to_session(self):
        self.session_created.emit(self.session_id, self.session_code)

# ==========================================================
# Whisper STT Processor for Real-time Audio
# ==========================================================
class WhisperSTTProcessor:
    def __init__(self, model_size="medium"):
        """
        Initialize Whisper STT Processor
        
        model_size: "tiny" (75MB), "base" (142MB), "small" (466MB), 
                   "medium" (1.5GB), "large" (2.9GB)
        """
        self.model_size = model_size
        self.model = None
        self.audio_buffer = []
        self.sample_rate = 16000
        self.buffer_duration = 3  # Process every 3 seconds
        self.last_processing_time = 0
        self.processing_interval = 2  # Minimum seconds between processing
        self.load_model()
        
    def load_model(self):
        """Load Whisper model"""
        try:
            print(f"Loading Whisper {self.model_size} model...")
            self.model = whisper.load_model(self.model_size)
            print(f"✅ Whisper {self.model_size} model loaded successfully!")
        except Exception as e:
            print(f"❌ Failed to load Whisper model: {e}")
            # Fallback to tiny model
            try:
                print("Trying to load tiny model as fallback...")
                self.model = whisper.load_model("tiny")
                print("✅ Tiny model loaded as fallback")
            except Exception as e2:
                print(f"❌ Failed to load any Whisper model: {e2}")
                self.model = None
    
    def add_audio_chunk(self, audio_bytes):
        """Add audio chunk for processing"""
        if self.model is None:
            return
            
        # Convert bytes to numpy array
        audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        self.audio_buffer.append(audio_np)
        
        # Check if we have enough audio and enough time has passed
        current_time = time.time()
        total_samples = sum(len(chunk) for chunk in self.audio_buffer)
        
        if (total_samples > self.sample_rate * self.buffer_duration and 
            current_time - self.last_processing_time > self.processing_interval):
            return self.process_buffer()
        
        return ""
    
    def process_buffer(self):
        """Process accumulated audio buffer and return transcription"""
        if self.model is None or not self.audio_buffer:
            return ""
        
        try:
            # Combine audio chunks
            audio = np.concatenate(self.audio_buffer)
            
            # Ensure minimum length
            if len(audio) < self.sample_rate * 0.5:  # Less than 0.5 seconds
                return ""
            
            # Transcribe with Whisper
            result = self.model.transcribe(
                audio,
                language="en",  # English language
                task="transcribe",
                fp16=False,     # Use CPU (set to True for GPU)
                temperature=0.0,
                best_of=5,
                beam_size=5,
                condition_on_previous_text=False  # Better for real-time
            )
            
            text = result.get("text", "").strip()
            
            if text:
                print(f"🎤 Whisper transcribed: {text}")
                
                # Clear buffer (keep last 0.5 seconds for continuity)
                keep_samples = int(self.sample_rate * 0.5)
                if len(audio) > keep_samples:
                    self.audio_buffer = [audio[-keep_samples:]]
                else:
                    self.audio_buffer = [audio]
                
                self.last_processing_time = time.time()
                return text
                
        except Exception as e:
            print(f"❌ Whisper transcription error: {e}")
        
        # Clear buffer on error
        self.audio_buffer = []
        return ""

# ==========================================================
# Flutter-Style Teacher Session Page (UPDATED WITH WHISPER)
# ==========================================================
class TeacherSessionPage(QWidget):
    def __init__(self, session_id, session_code):
        super().__init__()
        self.session_id = session_id
        self.session_code = session_code
        self.listening = False
        self.stream = None
        self.current_transcript = ""
        self.student_listener = None
        self.tts_engine = TextToSpeechEngine()
        self.tts_enabled = True
        self.last_full_transcript = ""
        self.currently_speaking_word = ""
        
        # Initialize Whisper STT Processor
        print("Initializing Whisper STT...")
        self.whisper_processor = WhisperSTTProcessor(model_size="base")  # Change to "small" or "medium" for better accuracy
        
        # TTS tracking to prevent duplicates
        self.last_spoken_content = ""
        self.last_spoken_time = 0
        self.min_speech_interval = 2.0
        self.student_name = "Student"
        
        # Create session with retry capability
        self.session = self._create_session()

        self.init_ui()
        self.start_student_listener()

    def _create_session(self):
        """Create a requests session with proper retry strategy"""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def init_ui(self):
        # Main styling with Flutter Material Design colors
        self.setStyleSheet("""
            QWidget {
                background-color: #FAFAFA;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # App Bar - Flutter Style
        app_bar = QWidget()
        app_bar.setFixedHeight(70)
        app_bar.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2196F3, stop:1 #1976D2);
                border: none;
            }
        """)
        app_bar_layout = QHBoxLayout(app_bar)
        app_bar_layout.setContentsMargins(25, 15, 25, 15)
        
        # App Title
        title_layout = QHBoxLayout()
        title_icon = QLabel("🎓")
        title_icon.setFont(QFont("Segoe UI", 24))
        title_text = QLabel("Include")
        title_text.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title_text.setStyleSheet("color: white; margin-left: 10px;")
        title_layout.addWidget(title_icon)
        title_layout.addWidget(title_text)
        app_bar_layout.addLayout(title_layout)
        app_bar_layout.addStretch()
        
        # Session Info
        session_info = QLabel(f"Session: {self.session_code}")
        session_info.setFont(QFont("Segoe UI", 12))
        session_info.setStyleSheet("""
            color: rgba(255,255,255,0.9); 
            background: rgba(255,255,255,0.15); 
            padding: 8px 16px; 
            border-radius: 16px;
        """)
        app_bar_layout.addWidget(session_info)
        
        # STT Status
        self.stt_status = QLabel("🤖 Whisper Ready")
        self.stt_status.setFont(QFont("Segoe UI", 11))
        self.stt_status.setStyleSheet("""
            color: white; 
            background: rgba(255,255,255,0.15); 
            padding: 8px 16px; 
            border-radius: 16px;
        """)
        app_bar_layout.addWidget(self.stt_status)
        
        # Connection Status
        self.connection_status = QLabel("🟢 Connected")
        self.connection_status.setFont(QFont("Segoe UI", 11))
        self.connection_status.setStyleSheet("""
            color: white; 
            background: rgba(255,255,255,0.15); 
            padding: 8px 16px; 
            border-radius: 16px;
        """)
        app_bar_layout.addWidget(self.connection_status)
        
        layout.addWidget(app_bar)

        # Main Content Area
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: #FAFAFA;")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(20)
        content_layout.setContentsMargins(25, 25, 25, 25)

        # Controls Section - Flutter Card Style
        controls_card = QWidget()
        controls_card.setFixedHeight(140)
        controls_card.setStyleSheet("""
            QWidget {
                background: white;
                border-radius: 16px;
                border: none;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
        """)
        controls_layout = QHBoxLayout(controls_card)
        controls_layout.setContentsMargins(30, 25, 30, 25)
        
        # TTS Control
        tts_container = QVBoxLayout()
        tts_label = QLabel("Voice Output")
        tts_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        tts_label.setStyleSheet("color: #424242; margin-bottom: 12px;")
        tts_container.addWidget(tts_label)
        
        self.tts_button = QPushButton("🔊 Voice: ON")
        self.tts_button.setFont(QFont("Segoe UI", 12))
        self.tts_button.setFixedSize(140, 48)
        self.tts_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tts_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 12px;
                border: none;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #43A047;
            }
        """)
        self.tts_button.clicked.connect(self.toggle_tts)
        tts_container.addWidget(self.tts_button)
        controls_layout.addLayout(tts_container)
        
        controls_layout.addStretch()
        
        # Microphone Control
        mic_container = QVBoxLayout()
        mic_label = QLabel("Your Microphone")
        mic_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        mic_label.setStyleSheet("color: #424242; margin-bottom: 12px;")
        mic_container.addWidget(mic_label)
        
        self.session_button = QPushButton("🎤 Start Listening")
        self.session_button.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.session_button.setFixedSize(180, 52)
        self.session_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.session_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border-radius: 12px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.session_button.clicked.connect(self.toggle_session)
        mic_container.addWidget(self.session_button)
        controls_layout.addLayout(mic_container)
        
        content_layout.addWidget(controls_card)

        # Main Content Area - Responsive Layout
        main_content = QHBoxLayout()
        main_content.setSpacing(25)

        # Left Panel - Communication
        left_panel = QVBoxLayout()
        left_panel.setSpacing(25)

        # Student Communication Card
        student_card = QWidget()
        student_card.setStyleSheet("""
            QWidget {
                background: white;
                border-radius: 16px;
                border: none;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
        """)
        student_layout = QVBoxLayout(student_card)
        student_layout.setContentsMargins(25, 25, 25, 25)
        student_layout.setSpacing(20)
        
        # Student Header
        student_header = QHBoxLayout()
        student_title = QLabel("Student Communication")
        student_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        student_title.setStyleSheet("color: #1976D2;")
        student_header.addWidget(student_title)
        student_header.addStretch()
        
        # Student Name Badge
        self.student_name_badge = QLabel(f"👤 {self.student_name}")
        self.student_name_badge.setFont(QFont("Segoe UI", 12, QFont.Weight.Medium))
        self.student_name_badge.setStyleSheet("""
            color: #424242; 
            background: #F5F5F5; 
            padding: 8px 16px; 
            border-radius: 12px;
            border: 1px solid #E0E0E0;
        """)
        student_header.addWidget(self.student_name_badge)
        student_layout.addLayout(student_header)

        # Live Signs Section
        signs_section = QVBoxLayout()
        signs_section.setSpacing(12)
        
        signs_label = QLabel("Live Sign Language Translation")
        signs_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        signs_label.setStyleSheet("color: #616161;")
        signs_section.addWidget(signs_label)
        
        self.student_transcript_label = QLabel("Waiting for student to start signing...")
        self.student_transcript_label.setFont(QFont("Segoe UI", 13))
        self.student_transcript_label.setStyleSheet("""
            QLabel {
                background: #E8F5E9;
                color: #2E7D32;
                padding: 20px;
                border-radius: 12px;
                border: 2px solid #C8E6C9;
                min-height: 120px;
                line-height: 1.5;
            }
        """)
        self.student_transcript_label.setWordWrap(True)
        self.student_transcript_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        signs_section.addWidget(self.student_transcript_label)
        student_layout.addLayout(signs_section)

        # TTS Status
        tts_status_layout = QHBoxLayout()
        tts_status_layout.addStretch()
        
        self.tts_status_label = QLabel("🔊 Voice output ready")
        self.tts_status_label.setFont(QFont("Segoe UI", 11))
        self.tts_status_label.setStyleSheet("""
            color: #424242; 
            background: #F5F5F5; 
            padding: 8px 16px; 
            border-radius: 12px;
            border: 1px solid #E0E0E0;
        """)
        tts_status_layout.addWidget(self.tts_status_label)
        student_layout.addLayout(tts_status_layout)

        left_panel.addWidget(student_card)

        # Teacher Speech Card
        teacher_card = QWidget()
        teacher_card.setStyleSheet("""
            QWidget {
                background: white;
                border-radius: 16px;
                border: none;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
        """)
        teacher_layout = QVBoxLayout(teacher_card)
        teacher_layout.setContentsMargins(25, 25, 25, 25)
        teacher_layout.setSpacing(20)
        
        teacher_title = QLabel("Your Speech (Whisper STT)")
        teacher_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        teacher_title.setStyleSheet("color: #1976D2;")
        teacher_layout.addWidget(teacher_title)
        
        self.teacher_transcript_label = QLabel("Start speaking to see your transcript here...")
        self.teacher_transcript_label.setFont(QFont("Segoe UI", 13))
        self.teacher_transcript_label.setStyleSheet("""
            QLabel {
                background: #F5F5F5;
                color: #616161;
                padding: 20px;
                border-radius: 12px;
                border: 2px solid #E0E0E0;
                min-height: 100px;
                line-height: 1.5;
            }
        """)
        self.teacher_transcript_label.setWordWrap(True)
        self.teacher_transcript_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        teacher_layout.addWidget(self.teacher_transcript_label)
        
        left_panel.addWidget(teacher_card)

        main_content.addLayout(left_panel, 1)

        # Right Panel - Chat
        right_panel = QVBoxLayout()
        right_panel.setSpacing(25)

        # Chat Card
        chat_card = QWidget()
        chat_card.setStyleSheet("""
            QWidget {
                background: white;
                border-radius: 16px;
                border: none;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
        """)
        chat_layout = QVBoxLayout(chat_card)
        chat_layout.setContentsMargins(25, 25, 25, 25)
        chat_layout.setSpacing(20)
        
        # Chat Header
        chat_header = QHBoxLayout()
        chat_title = QLabel("Live Chat")
        chat_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        chat_title.setStyleSheet("color: #1976D2;")
        chat_header.addWidget(chat_title)
        chat_header.addStretch()
        
        self.chat_status_label = QLabel("💬 Online")
        self.chat_status_label.setFont(QFont("Segoe UI", 11))
        self.chat_status_label.setStyleSheet("""
            color: #4CAF50; 
            background: #E8F5E9; 
            padding: 8px 16px; 
            border-radius: 12px;
            border: 1px solid #C8E6C9;
        """)
        chat_header.addWidget(self.chat_status_label)
        chat_layout.addLayout(chat_header)

        # Chat Display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Segoe UI", 12))
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background: #FAFAFA;
                color: #424242;
                border: 2px solid #E0E0E0;
                border-radius: 12px;
                padding: 16px;
                min-height: 250px;
                line-height: 1.4;
            }
        """)
        chat_layout.addWidget(self.chat_display)

        # Chat Input
        chat_input_layout = QHBoxLayout()
        chat_input_layout.setSpacing(12)
        
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Type a message...")
        self.chat_input.setFont(QFont("Segoe UI", 12))
        self.chat_input.setStyleSheet("""
            QLineEdit {
                background: white;
                color: #424242;
                border: 2px solid #E0E0E0;
                border-radius: 12px;
                padding: 12px 16px;
            }
            QLineEdit:focus {
                border-color: #2196F3;
                background: #FAFAFA;
            }
            QLineEdit::placeholder {
                color: #9E9E9E;
            }
        """)
        self.chat_input.returnPressed.connect(self.send_chat_message)
        chat_input_layout.addWidget(self.chat_input)
        
        self.send_chat_button = QPushButton("Send")
        self.send_chat_button.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.send_chat_button.setFixedSize(80, 48)
        self.send_chat_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_chat_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border-radius: 12px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.send_chat_button.clicked.connect(self.send_chat_message)
        chat_input_layout.addWidget(self.send_chat_button)
        
        chat_layout.addLayout(chat_input_layout)
        right_panel.addWidget(chat_card)

        main_content.addLayout(right_panel, 1)
        content_layout.addLayout(main_content)
        layout.addWidget(content_widget)

        self.setLayout(layout)
        self.timer = QTimer()
        self.timer.timeout.connect(self.process_audio)
        self.timer.start(100)  # Check audio every 100ms

    def update_student_name_display(self, student_name):
        """Update student name display"""
        self.student_name = student_name
        self.student_name_badge.setText(f"👤 {self.student_name}")

    def toggle_tts(self):
        """Toggle text-to-speech on/off"""
        self.tts_enabled = not self.tts_enabled
        if self.tts_enabled:
            self.tts_button.setText("🔊 Voice: ON")
            self.tts_button.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border-radius: 12px;
                    border: none;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #43A047;
                }
            """)
            self.tts_status_label.setText("🔊 Voice output ready")
        else:
            self.tts_button.setText("🔇 Voice: OFF")
            self.tts_button.setStyleSheet("""
                QPushButton {
                    background-color: #F44336;
                    color: white;
                    border-radius: 12px;
                    border: none;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #E53935;
                }
            """)
            self.tts_status_label.setText("🔇 Voice output disabled")

    def get_new_words(self, current_transcript):
        """Get only the new words that haven't been spoken yet"""
        if not self.last_full_transcript:
            return current_transcript.split()
        
        current_words = current_transcript.split()
        previous_words = self.last_full_transcript.split()
        
        new_words = []
        if len(current_words) > len(previous_words):
            new_words = current_words[len(previous_words):]
        
        return new_words

    def speak_new_words(self, transcript):
        """Speak only the new words from the student's transcript"""
        if not self.tts_enabled or not transcript.strip():
            return
            
        # Filter out initialization messages
        if any(phrase in transcript.lower() for phrase in [
            "student has not started", 
            "waiting for student", 
            "session created",
            "share the code",
            "waiting for student..."
        ]):
            return
        
        new_words = self.get_new_words(transcript)
        self.last_full_transcript = transcript
        
        for word in new_words:
            if len(word) > 1:
                self.speak_word(word)

    def speak_word(self, word):
        """Speak a single word with visual feedback"""
        current_time = time.time()
        if (word == self.last_spoken_content and 
            current_time - self.last_spoken_time < self.min_speech_interval):
            return
            
        self.last_spoken_content = word
        self.last_spoken_time = current_time
        
        self.tts_engine.speak(word)

    def speak_chat_message(self, message):
        """Speak student's chat message with student name prefix"""
        if not self.tts_enabled or not message.strip():
            return
            
        current_time = time.time()
        chat_content = f"{self.student_name} says: {message}"
        
        if (chat_content == self.last_spoken_content and 
            current_time - self.last_spoken_time < self.min_speech_interval):
            return
            
        self.last_spoken_content = chat_content
        self.last_spoken_time = current_time
        
        self.tts_engine.speak(chat_content)

    def send_chat_message(self):
        """Send chat message to student via Firebase"""
        message = self.chat_input.text().strip()
        if not message:
            return
        
        if self.upload_chat_to_firebase(message):
            timestamp = time.strftime("%H:%M:%S")
            self.chat_display.append(f'<div style="color: #424242; margin: 10px 0;"><b>[{timestamp}] You:</b> {message}</div>')
            self.chat_display.verticalScrollBar().setValue(
                self.chat_display.verticalScrollBar().maximum()
            )
            self.chat_input.clear()
            self.chat_status_label.setText("✅ Sent")
            self.chat_status_label.setStyleSheet("""
                color: #4CAF50; 
                background: #E8F5E9; 
                padding: 8px 16px; 
                border-radius: 12px;
                border: 1px solid #C8E6C9;
            """)
        else:
            self.chat_status_label.setText("❌ Failed")
            self.chat_status_label.setStyleSheet("""
                color: #F44336; 
                background: #FFEBEE; 
                padding: 8px 16px; 
                border-radius: 12px;
                border: 1px solid #FFCDD2;
            """)

    def upload_chat_to_firebase(self, message):
        """Upload teacher's chat message to Firebase"""
        try:
            response = self.session.get(f"{FIREBASE_URL}/sessions/{self.session_id}.json")
            if response.status_code == 200:
                session_data = response.json() or {}
                existing_chat = session_data.get("chat_messages", [])
                
                chat_data = {
                    "sender": "teacher",
                    "message": message,
                    "timestamp": int(time.time())
                }
                existing_chat.append(chat_data)
                
                update_data = {
                    "chat_messages": existing_chat,
                    "last_updated": int(time.time())
                }
                
                response = self.session.patch(
                    f"{FIREBASE_URL}/sessions/{self.session_id}.json",
                    json=update_data,
                    timeout=5,
                    verify=False
                )
                return response.status_code == 200
        except Exception as e:
            print(f"Chat upload error: {e}")
        return False

    def update_chat_display(self, message_data):
        """Update chat display with new message from student and speak it"""
        sender = message_data.get("sender", "unknown")
        message = message_data.get("message", "")
        timestamp = time.strftime("%H:%M:%S", time.localtime(message_data.get("timestamp", time.time())))
        
        if sender == "student":
            self.chat_display.append(f'<div style="color: #1976D2; margin: 10px 0;"><b>[{timestamp}] {self.student_name}:</b> {message}</div>')
            self.chat_display.verticalScrollBar().setValue(
                self.chat_display.verticalScrollBar().maximum()
            )
            self.chat_status_label.setText("🟢 New message")
            self.chat_status_label.setStyleSheet("""
                color: #2196F3; 
                background: #E3F2FD; 
                padding: 8px 16px; 
                border-radius: 12px;
                border: 1px solid #BBDEFB;
            """)
            
            self.speak_chat_message(message)

    def start_student_listener(self):
        """Start listening for student transcript updates"""
        if self.session_id:
            self.student_listener = StudentTranscriptListener(self.session_id)
            self.student_listener.new_transcript.connect(self.update_student_transcript)
            self.student_listener.new_chat_message.connect(self.update_chat_display)
            self.student_listener.connection_status.connect(self.update_connection_status)
            self.student_listener.student_info_updated.connect(self.update_student_name_display)
            self.student_listener.start()

    def update_student_transcript(self, transcript):
        """Update the display with student's transcript and speak new words"""
        self.student_transcript_label.setText(transcript)
        self.student_transcript_label.setStyleSheet("""
            QLabel {
                background: #E8F5E9;
                color: #2E7D32;
                padding: 20px;
                border-radius: 12px;
                border: 2px solid #C8E6C9;
                min-height: 120px;
                line-height: 1.5;
            }
        """)
        
        self.speak_new_words(transcript)

    def update_connection_status(self, connected):
        """Update connection status display"""
        if connected:
            self.connection_status.setText("🟢 Connected")
            self.connection_status.setStyleSheet("color: white; background: rgba(255,255,255,0.15); padding: 8px 16px; border-radius: 16px;")
            self.stt_status.setText("🤖 Whisper Ready")
            self.stt_status.setStyleSheet("""
                color: white; 
                background: rgba(255,255,255,0.15); 
                padding: 8px 16px; 
                border-radius: 16px;
            """)
        else:
            self.connection_status.setText("🔴 Connecting...")
            self.connection_status.setStyleSheet("color: white; background: rgba(255,255,255,0.15); padding: 8px 16px; border-radius: 16px;")
            self.stt_status.setText("🤖 Whisper Ready")
            self.stt_status.setStyleSheet("""
                color: white; 
                background: rgba(255,255,255,0.15); 
                padding: 8px 16px; 
                border-radius: 16px;
            """)

    def update_transcript_in_firebase(self, transcript):
        """Update teacher's transcript in Firebase"""
        if not self.session_id:
            return False
        try:
            self.session.patch(
                f"{FIREBASE_URL}/sessions/{self.session_id}.json",
                json={"current_transcript": transcript, "last_updated": time.time()},
                timeout=5,
                verify=False
            )
            return True
        except:
            return False

    def cleanup_firebase_session(self):
        """Clean up Firebase session and resources"""
        if self.session_id:
            try:
                self.session.delete(
                    f"{FIREBASE_URL}/sessions/{self.session_id}.json",
                    timeout=5,
                    verify=False
                )
            except:
                pass
        if self.student_listener:
            self.student_listener.stop()
            self.student_listener.wait(500)
        if self.tts_engine:
            self.tts_engine.stop()
        if self.stream:
            self.stream.stop()
            self.stream.close()

    def toggle_session(self):
        """Toggle microphone listening"""
        if not self.listening:
            self.start_listening()
        else:
            self.stop_listening()

    def start_listening(self):
        """Start audio capture and processing"""
        try:
            self.stream = sd.RawInputStream(
                samplerate=16000, 
                blocksize=4000,
                dtype="int16", 
                channels=1, 
                callback=self.audio_callback
            )
            self.stream.start()
            self.listening = True
            self.session_button.setText("🎤 Stop Listening")
            self.session_button.setStyleSheet("""
                QPushButton {
                    background-color: #F44336;
                    color: white;
                    border-radius: 12px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #E53935;
                }
            """)
            self.stt_status.setText("🎤 Listening...")
        except Exception as e:
            QMessageBox.critical(self, "Audio Error", f"Failed to start audio:\n{str(e)}")

    def stop_listening(self):
        """Stop audio capture"""
        if self.stream:
            self.stream.stop()
            self.stream.close()
        self.listening = False
        self.session_button.setText("🎤 Start Listening")
        self.session_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border-radius: 12px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.stt_status.setText("🤖 Whisper Ready")

    def audio_callback(self, indata, frames, time, status):
        """Audio callback for capturing microphone input"""
        audio_queue.put(bytes(indata))

    def process_audio(self):
        """Process audio queue with Whisper"""
        if not self.listening or self.whisper_processor.model is None:
            return
            
        # Process all audio chunks in queue
        while not audio_queue.empty():
            data = audio_queue.get()
            # Send to Whisper processor
            text = self.whisper_processor.add_audio_chunk(data)
            
            if text and text.strip():
                self.current_transcript = text
                self.teacher_transcript_label.setText(text)
                self.update_transcript_in_firebase(text)

    def closeEvent(self, event):
        """Handle window close event"""
        self.cleanup_firebase_session()
        event.accept()

# ==========================================================
# Main Teacher Widget with Page Management
# ==========================================================
class TeacherPage(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.stacked_widget = QStackedWidget()
        
        # Create pages
        self.session_creation_page = SessionCreationPage()
        self.teacher_session_page = None
        
        # Connect signals
        self.session_creation_page.session_created.connect(self.on_session_created)
        
        # Add pages to stacked widget
        self.stacked_widget.addWidget(self.session_creation_page)
        
        layout.addWidget(self.stacked_widget)
        self.setLayout(layout)

    def on_session_created(self, session_id, session_code):
        """Handle session creation and switch to teacher session page"""
        self.teacher_session_page = TeacherSessionPage(session_id, session_code)
        self.stacked_widget.addWidget(self.teacher_session_page)
        self.stacked_widget.setCurrentWidget(self.teacher_session_page)

    def closeEvent(self, event):
        """Clean up when closing the application"""
        if self.teacher_session_page:
            self.teacher_session_page.cleanup_firebase_session()
        event.accept()