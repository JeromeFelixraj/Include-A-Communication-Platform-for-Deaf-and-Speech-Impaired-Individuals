import queue
import sounddevice as sd
import whisper
import numpy as np
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                            QLineEdit, QMessageBox, QStackedWidget, QTextEdit, QScrollArea,
                            QFrame, QSplitter)
from PyQt6.QtGui import QFont, QPalette, QColor, QPixmap, QPainter, QPen, QBrush, QLinearGradient
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QRectF, QPointF
import json, random, requests, time, re, math
import win32com.client
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import threading
import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

FIREBASE_URL = "https://include-6e31e-default-rtdb.firebaseio.com/"

# Disable SSL warnings and configure for better connectivity
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Whisper Model - Initialize empty, will load later
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
# Professional Visual Generator - Clear and Cool
# ==========================================================
class ProfessionalVisualGenerator:
    def __init__(self):
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("⚠️ GEMINI_API_KEY not found. Visualization will be limited.")
            self.model = None
        else:
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('models/gemini-2.0-flash')
                print("✅ Professional Visual Generator initialized!")
            except:
                self.model = None
                print("⚠️ Gemini failed to initialize")
        
    def generate_professional_concept(self, text_snippet):
        """Generate a clear professional visual concept from text snippet"""
        if not self.model or len(text_snippet.split()) < 5:
            return None
            
        try:
            prompt = f"""
            Create a CLEAR and PROFESSIONAL visual concept from this teaching text:
            "{text_snippet}"
            
            Return ONLY in format:
            CONCEPT: [3-4 word topic]
            KEY_POINTS:
            - [max 3 words - clear and simple]
            - [max 3 words - clear and simple]
            - [max 3 words - clear and simple]
            VISUAL_TYPE: [bubbles/mindmap/flowchart]
            
            Keep points VERY CLEAR and READABLE.
            """
            
            response = self.model.generate_content(prompt, generation_config=genai.GenerationConfig(
                max_output_tokens=150,
                temperature=0.3
            ))
            return response.text.strip()
            
        except Exception as e:
            print(f"❌ Visual concept error: {e}")
            return None

# ==========================================================
# Professional Visual Renderer - Clear, Cool and Readable
# ==========================================================
class ProfessionalVisualRenderer:
    COLOR_PALETTES = {
        'bubbles': ['#667eea', '#764ba2', '#f093fb', '#f5576c'],
        'mindmap': ['#4facfe', '#00f2fe', '#43e97b', '#38f9d7'],
        'flowchart': ['#fa709a', '#fee140', '#30cfd0', '#330867'],
        'default': ['#667eea', '#764ba2', '#f093fb', '#f5576c']
    }
    
    GRADIENTS = {
        'bubbles': [('#667eea', '#764ba2'), ('#f093fb', '#f5576c')],
        'mindmap': [('#4facfe', '#00f2fe'), ('#43e97b', '#38f9d7')],
        'flowchart': [('#fa709a', '#fee140'), ('#30cfd0', '#330867')],
        'default': [('#667eea', '#764ba2'), ('#f093fb', '#f5576c')]
    }
    
    @staticmethod
    def create_professional_visual(visual_concept, width=700, height=450):
        """Create professional visualization with clear text and cool design"""
        try:
            pixmap = QPixmap(width, height)
            
            # Create gradient background
            gradient = QLinearGradient(0, 0, width, height)
            gradient.setColorAt(0, QColor(248, 249, 250))
            gradient.setColorAt(1, QColor(241, 243, 245))
            pixmap.fill(QColor(248, 249, 250))
            
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Draw subtle background pattern
            ProfessionalVisualRenderer._draw_background_pattern(painter, width, height)
            
            # Parse concept
            concept_data = ProfessionalVisualRenderer._parse_concept_clearly(visual_concept)
            visual_type = concept_data.get('type', 'bubbles').lower()
            
            # Get colors for this visual type
            colors = ProfessionalVisualRenderer.COLOR_PALETTES.get(visual_type, ProfessionalVisualRenderer.COLOR_PALETTES['default'])
            gradients = ProfessionalVisualRenderer.GRADIENTS.get(visual_type, ProfessionalVisualRenderer.GRADIENTS['default'])
            
            # Draw based on type
            if 'mindmap' in visual_type:
                ProfessionalVisualRenderer._draw_mindmap(painter, concept_data, colors, gradients, width, height)
            elif 'flowchart' in visual_type:
                ProfessionalVisualRenderer._draw_flowchart(painter, concept_data, colors, gradients, width, height)
            else:
                ProfessionalVisualRenderer._draw_bubbles(painter, concept_data, colors, gradients, width, height)
            
            # Add subtle border
            painter.setPen(QPen(QColor(229, 231, 235), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(5, 5, width - 10, height - 10, 15, 15)
            
            painter.end()
            return pixmap
            
        except Exception as e:
            print(f"❌ Professional visual error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def _draw_background_pattern(painter, width, height):
        """Draw subtle background pattern"""
        painter.setPen(QPen(QColor(241, 245, 249, 30), 1))
        grid_size = 40
        for x in range(0, width + grid_size, grid_size):
            painter.drawLine(x, 0, x, height)
        for y in range(0, height + grid_size, grid_size):
            painter.drawLine(0, y, width, y)
    
    @staticmethod
    def _parse_concept_clearly(visual_concept):
        """Parse visual concept with clear formatting"""
        data = {
            'concept': 'Teaching Concept',
            'type': 'bubbles',
            'points': []
        }
        
        if not visual_concept:
            return data
        
        lines = visual_concept.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('CONCEPT:'):
                concept = line.replace('CONCEPT:', '').strip()
                # Keep concept readable - max 4 words
                words = concept.split()[:4]
                data['concept'] = ' '.join(words)
            elif line.startswith('VISUAL_TYPE:'):
                vis_type = line.replace('VISUAL_TYPE:', '').strip().lower()
                data['type'] = vis_type
            elif line.startswith('-'):
                point = line.replace('-', '').strip()
                # Keep points clear - max 3 words
                words = point.split()[:3]
                if words:
                    data['points'].append(' '.join(words))
        
        # Ensure we have at least 3 points
        if len(data['points']) < 3:
            default_points = ['Learning Process', 'Key Concepts', 'Understanding']
            data['points'] = default_points[:3]
        
        # Limit to 4 points for clarity
        data['points'] = data['points'][:4]
        
        return data
    
    @staticmethod
    def _draw_bubbles(painter, data, colors, gradients, width, height):
        """Draw beautiful bubble chart with clear text"""
        points = data['points']
        if not points:
            return
        
        # Title with shadow effect
        painter.setPen(QPen(QColor(30, 41, 59)))
        painter.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        concept = data['concept']
        title_rect = QRectF(20, 20, width - 40, 40)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, concept)
        
        # Add subtitle
        painter.setPen(QPen(QColor(100, 116, 139)))
        painter.setFont(QFont("Segoe UI", 12))
        subtitle_rect = QRectF(20, 60, width - 40, 30)
        painter.drawText(subtitle_rect, Qt.AlignmentFlag.AlignCenter, "AI Visualization • 20-word Summary")
        
        # Calculate bubble positions
        num_points = len(points)
        center_x, center_y = width // 2, height // 2 + 20
        radius = min(width, height) // 3
        
        for i, point in enumerate(points):
            angle = 2 * math.pi * i / num_points
            x = int(center_x + radius * math.cos(angle) * 0.9)
            y = int(center_y + radius * math.sin(angle) * 0.9)
            
            # Bubble size based on text length - larger for readability
            text_length = len(point)
            size = 120 + (text_length * 2)
            color_index = i % len(colors)
            
            # Get gradient colors for this bubble
            if i < len(gradients):
                start_color_hex, end_color_hex = gradients[i % len(gradients)]
            else:
                start_color_hex, end_color_hex = gradients[0]
            
            # Create gradient for bubble
            gradient = QLinearGradient(x - size//2, y - size//2, x + size//2, y + size//2)
            gradient.setColorAt(0, QColor(start_color_hex))
            gradient.setColorAt(1, QColor(end_color_hex))
            
            # Draw bubble with shadow effect
            painter.setBrush(QBrush(gradient))
            painter.setPen(QPen(QColor(30, 41, 59, 100), 2))
            painter.drawEllipse(x - size//2, y - size//2, size, size)
            
            # Draw inner highlight
            painter.setBrush(QBrush(QColor(255, 255, 255, 50)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(x - size//2 + 5, y - size//2 + 5, size - 10, size - 10)
            
            # Text - clear and centered
            painter.setPen(QPen(Qt.GlobalColor.white))
            font_size = max(12, min(16, 200 // max(1, len(point))))
            painter.setFont(QFont("Segoe UI", font_size, QFont.Weight.Bold))
            
            # Text with proper word wrapping
            words = point.split()
            if len(words) <= 2:
                # Single line for short text
                text_rect = QRectF(x - size//2 + 10, y - size//2 + size//3, size - 20, size//2)
                painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, point)
            else:
                # Two lines for longer text
                half = len(words) // 2
                line1 = ' '.join(words[:half])
                line2 = ' '.join(words[half:])
                
                text_rect1 = QRectF(x - size//2 + 10, y - size//2 + size//4, size - 20, size//4)
                text_rect2 = QRectF(x - size//2 + 10, y - size//2 + size//2, size - 20, size//4)
                
                painter.drawText(text_rect1, Qt.AlignmentFlag.AlignCenter, line1)
                painter.drawText(text_rect2, Qt.AlignmentFlag.AlignCenter, line2)
            
            # Draw connection line to center
            painter.setPen(QPen(QColor(start_color_hex), 3))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawLine(center_x, center_y, x, y)
    
    @staticmethod
    def _draw_mindmap(painter, data, colors, gradients, width, height):
        """Draw clear and cool mindmap"""
        points = data['points'][:5]  # Max 5 points
        
        center_x, center_y = width // 2, height // 2
        
        # Title
        painter.setPen(QPen(QColor(30, 41, 59)))
        painter.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        concept = data['concept']
        title_rect = QRectF(20, 20, width - 40, 40)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, concept)
        
        # Center bubble with gradient
        center_gradient = QLinearGradient(center_x - 60, center_y - 60, center_x + 60, center_y + 60)
        center_gradient.setColorAt(0, QColor('#4facfe'))
        center_gradient.setColorAt(1, QColor('#00f2fe'))
        
        painter.setBrush(QBrush(center_gradient))
        painter.setPen(QPen(QColor(30, 41, 59), 3))
        painter.drawEllipse(center_x - 60, center_y - 60, 120, 120)
        
        # Center text
        painter.setPen(QPen(Qt.GlobalColor.white))
        painter.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        painter.drawText(center_x - 50, center_y - 15, 100, 30, Qt.AlignmentFlag.AlignCenter, "Topic")
        
        # Branches
        for i, point in enumerate(points):
            angle = 2 * math.pi * i / len(points)
            distance = 180
            
            end_x = int(center_x + distance * math.cos(angle))
            end_y = int(center_y + distance * math.sin(angle))
            
            # Get color for this branch
            color_index = (i + 1) % len(colors)
            line_color = QColor(colors[color_index])
            
            # Branch line
            painter.setPen(QPen(line_color, 4))
            painter.drawLine(center_x, center_y, end_x, end_y)
            
            # Get gradient colors for branch node
            if i < len(gradients):
                start_color_hex, end_color_hex = gradients[i % len(gradients)]
            else:
                start_color_hex, end_color_hex = gradients[0]
            
            # Branch node with gradient
            node_gradient = QLinearGradient(end_x - 45, end_y - 45, end_x + 45, end_y + 45)
            node_gradient.setColorAt(0, QColor(start_color_hex))
            node_gradient.setColorAt(1, QColor(end_color_hex))
            
            painter.setBrush(QBrush(node_gradient))
            painter.setPen(QPen(QColor(30, 41, 59), 2))
            node_size = 90
            painter.drawEllipse(end_x - node_size//2, end_y - node_size//2, node_size, node_size)
            
            # Branch text (clear and centered)
            painter.setPen(QPen(Qt.GlobalColor.white))
            painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            
            words = point.split()
            if len(words) <= 2:
                text_rect = QRectF(end_x - node_size//2 + 5, end_y - 15, node_size - 10, 30)
                painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, point)
            else:
                half = len(words) // 2
                line1 = ' '.join(words[:half])
                line2 = ' '.join(words[half:])
                
                text_rect1 = QRectF(end_x - node_size//2 + 5, end_y - 20, node_size - 10, 20)
                text_rect2 = QRectF(end_x - node_size//2 + 5, end_y, node_size - 10, 20)
                
                painter.drawText(text_rect1, Qt.AlignmentFlag.AlignCenter, line1)
                painter.drawText(text_rect2, Qt.AlignmentFlag.AlignCenter, line2)
            
            # Draw arrow at end of line
            ProfessionalVisualRenderer._draw_arrow(painter, center_x, center_y, end_x, end_y, line_color)
    
    @staticmethod
    def _draw_arrow(painter, start_x, start_y, end_x, end_y, color):
        """Draw arrow at end of line"""
        angle = math.atan2(end_y - start_y, end_x - start_x)
        
        arrow_size = 10
        arrow_x1 = end_x - arrow_size * math.cos(angle - math.pi/6)
        arrow_y1 = end_y - arrow_size * math.sin(angle - math.pi/6)
        arrow_x2 = end_x - arrow_size * math.cos(angle + math.pi/6)
        arrow_y2 = end_y - arrow_size * math.sin(angle + math.pi/6)
        
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(color, 2))
        
        points = [
            QPointF(end_x, end_y),
            QPointF(arrow_x1, arrow_y1),
            QPointF(arrow_x2, arrow_y2)
        ]
        
        painter.drawPolygon(points)
    
    @staticmethod
    def _draw_flowchart(painter, data, colors, gradients, width, height):
        """Draw professional flowchart"""
        points = data['points'][:4]  # Max 4 points
        
        # Title
        painter.setPen(QPen(QColor(30, 41, 59)))
        painter.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        concept = data['concept']
        title_rect = QRectF(20, 20, width - 40, 40)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, concept)
        
        # Calculate positions
        start_y = 100
        node_height = 80
        spacing = (height - start_y - 100) // len(points)
        
        for i, point in enumerate(points):
            y = start_y + (i * spacing)
            color_index = i % len(colors)
            
            # Get gradient colors for node
            if i < len(gradients):
                start_color_hex, end_color_hex = gradients[i % len(gradients)]
            else:
                start_color_hex, end_color_hex = gradients[0]
            
            # Node with gradient
            node_gradient = QLinearGradient(0, y, width, y + node_height)
            node_gradient.setColorAt(0, QColor(start_color_hex))
            node_gradient.setColorAt(1, QColor(end_color_hex))
            
            node_width = min(250, width - 100)
            x = (width - node_width) // 2
            
            # Draw node with shadow effect
            painter.setBrush(QBrush(node_gradient))
            painter.setPen(QPen(QColor(30, 41, 59), 2))
            painter.drawRoundedRect(x, y, node_width, node_height, 15, 15)
            
            # Inner highlight
            painter.setBrush(QBrush(QColor(255, 255, 255, 30)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(x + 5, y + 5, node_width - 10, node_height - 10, 10, 10)
            
            # Node text (clear and centered)
            painter.setPen(QPen(Qt.GlobalColor.white))
            painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            
            words = point.split()
            if len(words) <= 3:
                text_rect = QRectF(x + 10, y + 25, node_width - 20, 30)
                painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, point)
            else:
                half = len(words) // 2
                line1 = ' '.join(words[:half])
                line2 = ' '.join(words[half:])
                
                text_rect1 = QRectF(x + 10, y + 20, node_width - 20, 25)
                text_rect2 = QRectF(x + 10, y + 45, node_width - 20, 25)
                
                painter.drawText(text_rect1, Qt.AlignmentFlag.AlignCenter, line1)
                painter.drawText(text_rect2, Qt.AlignmentFlag.AlignCenter, line2)
            
            # Step number
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            painter.setPen(QPen(QColor(255, 255, 255, 200)))
            painter.drawText(x + 15, y + 20, f"Step {i+1}")
            
            # Draw connector arrows between nodes (except last)
            if i < len(points) - 1:
                next_y = start_y + ((i + 1) * spacing)
                arrow_x = x + node_width // 2
                
                painter.setPen(QPen(QColor(start_color_hex), 3))
                painter.drawLine(arrow_x, y + node_height, arrow_x, next_y)
                
                # Draw arrow head
                ProfessionalVisualRenderer._draw_arrow_head(painter, arrow_x, next_y, False)
    
    @staticmethod
    def _draw_arrow_head(painter, x, y, pointing_up=True):
        """Draw simple arrow head"""
        size = 8
        if pointing_up:
            points = [
                QPointF(x, y),
                QPointF(x - size, y + size),
                QPointF(x + size, y + size)
            ]
        else:
            points = [
                QPointF(x, y),
                QPointF(x - size, y - size),
                QPointF(x + size, y - size)
            ]
        
        painter.setBrush(QBrush(QColor(100, 116, 139)))
        painter.setPen(QPen(QColor(100, 116, 139), 2))
        painter.drawPolygon(points)

# ==========================================================
# Enhanced Firebase Student Transcript Listener with Chat
# ==========================================================
class StudentTranscriptListener(QThread):
    new_transcript = pyqtSignal(str)
    new_chat_message = pyqtSignal(dict)
    connection_status = pyqtSignal(bool)
    student_info_updated = pyqtSignal(str)
    
    def __init__(self, session_id):
        super().__init__()
        self.session_id = session_id
        self.running = True
        self.last_transcript = ""
        self.last_chat_count = 0
        self.last_chat_message = ""
        self.student_name = "Student"
        
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
                        new_messages = chat_messages[self.last_chat_count:]
                        for message in new_messages:
                            if message.get("sender") == "student":
                                current_message = message.get("message", "")
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
    session_created = pyqtSignal(str, str)
    
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
# Optimized Whisper STT Processor
# ==========================================================
class WhisperSTTProcessor(QThread):
    model_loaded = pyqtSignal(bool, str)
    transcription_ready = pyqtSignal(str)
    
    def __init__(self, model_size="base"):
        super().__init__()
        self.model_size = model_size
        self.model = None
        self.audio_buffer = []
        self.sample_rate = 16000
        self.buffer_duration = 3
        self.last_processing_time = 0
        self.processing_interval = 2
        self.is_loading = False
        self.last_transcription = ""
        
    def run(self):
        """Load model in background thread"""
        try:
            self.is_loading = True
            print(f"Loading Whisper {self.model_size} model...")
            
            self.model = whisper.load_model(self.model_size)
            
            print(f"✅ Whisper {self.model_size} model loaded successfully!")
            self.model_loaded.emit(True, f"Whisper {self.model_size} model loaded")
            self.is_loading = False
            
        except Exception as e:
            print(f"❌ Failed to load Whisper model: {e}")
            self.model_loaded.emit(False, f"Failed to load model: {e}")
    
    def add_audio_chunk(self, audio_bytes):
        """Add audio chunk for processing - NON-BLOCKING"""
        if self.model is None or self.is_loading:
            return False
            
        audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        self.audio_buffer.append(audio_np)
        
        current_time = time.time()
        total_samples = sum(len(chunk) for chunk in self.audio_buffer)
        
        if (total_samples >= self.sample_rate * self.buffer_duration and 
            current_time - self.last_processing_time >= self.processing_interval):
            
            threading.Thread(target=self._process_buffer, daemon=True).start()
            return True
            
        return False
    
    def _process_buffer(self):
        """Process audio buffer and emit result"""
        if self.model is None or not self.audio_buffer:
            return
            
        try:
            buffer_to_process = self.audio_buffer.copy()
            audio = np.concatenate(buffer_to_process)
            
            if len(audio) < self.sample_rate * 0.8:
                return
            
            result = self.model.transcribe(
                audio,
                language="en",
                task="transcribe",
                fp16=False,
                temperature=0.2,
                best_of=3,
                beam_size=3,
                condition_on_previous_text=False,
                repetition_penalty=1.5,
                no_repeat_ngram_size=3
            )
            
            text = result.get("text", "").strip()
            
            if text:
                text = self._clean_transcription(text)
                
                if self._is_too_similar(text, self.last_transcription):
                    return
                
                print(f"🎤 Whisper: {text[:80]}..." if len(text) > 80 else f"🎤 Whisper: {text}")
                
                self.last_transcription = text
                
                keep_samples = int(self.sample_rate * 1.0)
                if len(audio) > keep_samples:
                    self.audio_buffer = [audio[-keep_samples:]]
                else:
                    self.audio_buffer = [audio]
                
                self.last_processing_time = time.time()
                self.transcription_ready.emit(text)
                
        except Exception as e:
            print(f"❌ Whisper transcription error: {e}")
            self.audio_buffer = []
    
    def _clean_transcription(self, text):
        """Clean up transcription text"""
        if not text:
            return ""
        
        words = text.split()
        if len(words) > 10:
            unique_words = set(words)
            if len(unique_words) / len(words) < 0.3:
                seen = set()
                cleaned = []
                for word in words:
                    if word not in seen:
                        cleaned.append(word)
                        seen.add(word)
                text = " ".join(cleaned[:20])
        
        text = text.replace(" . . .", "...")
        text = text.replace("..", ".")
        text = text.replace("  ", " ")
        
        return text.strip()
    
    def _is_too_similar(self, text1, text2, threshold=0.7):
        """Check if two texts are too similar"""
        if not text1 or not text2:
            return False
            
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return False
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        if union == 0:
            return False
            
        similarity = intersection / union
        return similarity > threshold

# ==========================================================
# Optimized Firebase Listener for Student Page
# ==========================================================
class FirebaseListener(QThread):
    new_transcript = pyqtSignal(str)
    new_chat_message = pyqtSignal(dict)
    connection_status = pyqtSignal(bool)
    
    def __init__(self, session_code):
        super().__init__()
        self.session_code = session_code
        self.running = True
        self.last_transcript = ""
        self.last_chat_count = 0
        self.session_id = None
        
    def run(self):
        while self.running:
            try:
                response = requests.get(f"{FIREBASE_URL}/sessions.json", timeout=5)
                if response.status_code == 200:
                    self.connection_status.emit(True)
                    sessions = response.json() or {}
                    
                    for session_id, session_data in sessions.items():
                        if session_data and session_data.get("session_code") == self.session_code:
                            self.session_id = session_id
                            
                            transcript = session_data.get("current_transcript", "")
                            if transcript and transcript != self.last_transcript:
                                self.last_transcript = transcript
                                self.new_transcript.emit(transcript)
                            
                            chat_messages = session_data.get("chat_messages", [])
                            current_chat_count = len(chat_messages) if chat_messages else 0
                            
                            if current_chat_count > self.last_chat_count:
                                new_messages = chat_messages[self.last_chat_count:]
                                for message in new_messages:
                                    if message and isinstance(message, dict):
                                        self.new_chat_message.emit(message)
                                self.last_chat_count = current_chat_count
                            break
                else:
                    self.connection_status.emit(False)
                    
            except Exception as e:
                print("Firebase listener error:", e)
                self.connection_status.emit(False)
            
            QThread.msleep(200)

    def stop(self):
        self.running = False

# ==========================================================
# Enhanced Student Page with Professional Visualizations and Chat Panel
# ==========================================================
class StudentPage(QWidget):
    def __init__(self):
        super().__init__()
        self.session_code = None
        self.student_name = None
        self.firebase_listener = None
        self.is_in_session = False
        self.visual_generator = ProfessionalVisualGenerator()
        self.visual_renderer = ProfessionalVisualRenderer()
        
        # Word counting with proper state tracking
        self.word_buffer = []
        self.total_words_processed = 0
        self.word_count_threshold = 20  # Generate visualization every 20 words
        self.last_visualization_time = 0
        self.visualization_cooldown = 10  # Minimum seconds between visualizations
        self.is_generating_visual = False  # Prevent overlapping generations
        
        # Cache for generated visuals to avoid re-generation
        self.visual_cache = {}
        
        # Chat panel visibility
        self.chat_panel_visible = False
        
        self.setup_join_interface()

    def setup_join_interface(self):
        """Setup the premium join session interface"""
        if hasattr(self, 'main_layout'):
            for i in reversed(range(self.main_layout.count())):
                widget = self.main_layout.itemAt(i).widget()
                if widget:
                    widget.deleteLater()
        
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #667eea, stop:1 #764ba2);
            }
        """)
        
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        scroll_area = QWidget()
        scroll_area.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(scroll_area)
        scroll_layout.setContentsMargins(40, 40, 40, 40)
        scroll_layout.setSpacing(0)
        scroll_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        content_card = QWidget()
        content_card.setFixedSize(500, 650)
        content_card.setStyleSheet("""
            QWidget {
                background: white;
                border-radius: 24px;
                border: none;
            }
        """)
        
        content_layout = QVBoxLayout(content_card)
        content_layout.setContentsMargins(50, 60, 50, 60)
        content_layout.setSpacing(0)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_label = QLabel("👋")
        icon_label.setFont(QFont("Segoe UI", 64))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("margin-bottom: 20px;")
        content_layout.addWidget(icon_label)

        title_label = QLabel("Join Classroom")
        title_label.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            color: #2D3748;
            margin-bottom: 10px;
        """)
        content_layout.addWidget(title_label)

        subtitle_label = QLabel("Enter your details to connect with your teacher")
        subtitle_label.setFont(QFont("Segoe UI", 14))
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("""
            color: #718096;
            margin-bottom: 50px;
            line-height: 1.4;
        """)
        content_layout.addWidget(subtitle_label)

        form_layout = QVBoxLayout()
        form_layout.setSpacing(25)

        name_container = QVBoxLayout()
        name_container.setSpacing(8)

        name_label = QLabel("Your Name")
        name_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Medium))
        name_label.setStyleSheet("color: #4A5568;")
        name_container.addWidget(name_label)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter your full name...")
        self.name_input.setFont(QFont("Segoe UI", 14))
        self.name_input.setMinimumHeight(55)
        self.name_input.setStyleSheet("""
            QLineEdit {
                background-color: #F7FAFC;
                color: #2D3748;
                padding: 16px 20px;
                border-radius: 12px;
                border: 2px solid #E2E8F0;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #4299E1;
                background-color: #FFFFFF;
            }
            QLineEdit::placeholder {
                color: #A0AEC0;
            }
        """)
        name_container.addWidget(self.name_input)
        form_layout.addLayout(name_container)

        code_container = QVBoxLayout()
        code_container.setSpacing(8)

        code_label = QLabel("Session Code")
        code_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Medium))
        code_label.setStyleSheet("color: #4A5568;")
        code_container.addWidget(code_label)

        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("Enter 6-digit code from your teacher...")
        self.code_input.setFont(QFont("Segoe UI", 14))
        self.code_input.setMinimumHeight(55)
        self.code_input.setStyleSheet("""
            QLineEdit {
                background-color: #F7FAFC;
                color: #2D3748;
                padding: 16px 20px;
                border-radius: 12px;
                border: 2px solid #E2E8F0;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #4299E1;
                background-color: #FFFFFF;
            }
            QLineEdit::placeholder {
                color: #A0AEC0;
            }
        """)
        code_container.addWidget(self.code_input)
        form_layout.addLayout(code_container)

        self.join_button = QPushButton("Join Classroom")
        self.join_button.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.join_button.setMinimumHeight(60)
        self.join_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.join_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4299E1, stop:1 #3182CE);
                color: white;
                border: none;
                border-radius: 12px;
                padding: 16px 24px;
                font-weight: bold;
                margin-top: 10px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3182CE, stop:1 #2B6CB0);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2B6CB0, stop:1 #2C5282);
            }
            QPushButton:disabled {
                background: #CBD5E0;
                color: #A0AEC0;
            }
        """)
        self.join_button.clicked.connect(self.check_session)
        form_layout.addWidget(self.join_button)

        content_layout.addLayout(form_layout)
        content_layout.addStretch()

        self.status_label = QLabel("Enter your name and session code to join")
        self.status_label.setFont(QFont("Segoe UI", 12))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("""
            color: #718096;
            padding: 20px;
            background-color: #F7FAFC;
            border-radius: 12px;
            border: 1px solid #E2E8F0;
            line-height: 1.4;
            margin-top: 30px;
        """)
        self.status_label.setWordWrap(True)
        content_layout.addWidget(self.status_label)

        scroll_layout.addWidget(content_card, alignment=Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(scroll_area)
        self.setLayout(self.main_layout)
        self.is_in_session = False

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
            color: #D69E2E;
            padding: 20px;
            background-color: #FEFCBF;
            border-radius: 12px;
            border: 2px solid #F6E05E;
        """)

        QTimer.singleShot(100, lambda: self._check_session_async(name, code))

    def _check_session_async(self, name, code):
        try:
            session = requests.Session()
            test_response = session.get(f"{FIREBASE_URL}/.json", timeout=10)
            
            if test_response.status_code != 200:
                self.show_error("Connection failed. Please check your internet connection.")
                return

            response = session.get(f"{FIREBASE_URL}/sessions.json", timeout=10)
            if response.status_code == 200:
                data = response.json() or {}
                session_found = False
                
                for session_id, session_data in data.items():
                    if session_data and session_data.get("session_code") == code:
                        session_found = True
                        
                        update_data = {
                            "deaf_student_name": name,
                            "last_updated": int(time.time())
                        }
                        
                        patch_response = session.patch(
                            f"{FIREBASE_URL}/sessions/{session_id}.json",
                            json=update_data,
                            timeout=5
                        )
                        
                        if patch_response.status_code == 200:
                            print(f"✅ Student '{name}' joined session {code}")
                            self.setup_live_session()
                        else:
                            self.show_error("Failed to join session. Please try again.")
                        break

                if not session_found:
                    self.show_error("Session not found. Please check the code and make sure your teacher has created the session.")
            else:
                self.show_error("Failed to connect to classroom sessions.")

        except requests.exceptions.Timeout:
            self.show_error("Connection timeout. Please check your internet connection.")
        except requests.exceptions.ConnectionError:
            self.show_error("Connection error. Please check your internet connection.")
        except Exception as e:
            self.show_error(f"Connection error: {str(e)}")

    def show_error(self, message):
        """Show error message with premium styling"""
        self.status_label.setText(f"❌ {message}")
        self.status_label.setStyleSheet("""
            color: #E53E3E;
            padding: 20px;
            background-color: #FED7D7;
            border-radius: 12px;
            border: 2px solid #FEB2B2;
        """)
        self.join_button.setEnabled(True)
        self.join_button.setText("Join Classroom")

    def setup_live_session(self):
        """Setup the live session view with professional visualization and chat panel"""
        # Reset visualization state
        self.word_buffer = []
        self.total_words_processed = 0
        self.is_generating_visual = False
        self.chat_panel_visible = False
        
        for i in reversed(range(self.main_layout.count())):
            widget = self.main_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        self.setStyleSheet("""
            QWidget {
                background: #F8F9FA;
            }
        """)

        # Create splitter for main content and chat panel
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        
        # Main content widget
        main_content_widget = QWidget()
        main_content_layout = QVBoxLayout(main_content_widget)
        main_content_layout.setSpacing(10)
        main_content_layout.setContentsMargins(15, 10, 15, 10)

        header = QFrame()
        header.setFixedHeight(60)
        header.setStyleSheet("""
            QFrame {
                background: white;
                border-radius: 8px;
                border: 1px solid #E2E8F0;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(15, 8, 15, 8)
        
        session_info = QVBoxLayout()
        session_title = QLabel("Live Classroom Session")
        session_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        session_title.setStyleSheet("color: #2D3748; margin-bottom: 2px;")
        session_info.addWidget(session_title)
        
        session_details = QLabel(f"Session: {self.session_code} | Student: {self.student_name}")
        session_details.setFont(QFont("Segoe UI", 9))
        session_details.setStyleSheet("color: #718096;")
        session_info.addWidget(session_details)
        
        header_layout.addLayout(session_info)
        header_layout.addStretch()

        self.connection_label = QLabel("🟢 Connected")
        self.connection_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        self.connection_label.setStyleSheet("""
            color: #38A169;
            background: rgba(72, 187, 120, 0.1);
            padding: 5px 10px;
            border-radius: 12px;
            border: 1px solid rgba(72, 187, 120, 0.3);
        """)
        header_layout.addWidget(self.connection_label)

        # Chat toggle button
        self.chat_toggle_btn = QPushButton("💬 Chat")
        self.chat_toggle_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        self.chat_toggle_btn.setFixedSize(80, 30)
        self.chat_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chat_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #4299E1;
                color: white;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #3182CE;
            }
        """)
        self.chat_toggle_btn.clicked.connect(self.toggle_chat_panel)
        header_layout.addWidget(self.chat_toggle_btn)

        leave_btn = QPushButton("Leave")
        leave_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        leave_btn.setFixedSize(70, 30)
        leave_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        leave_btn.setStyleSheet("""
            QPushButton {
                background-color: #E53E3E;
                color: white;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #C53030;
            }
        """)
        leave_btn.clicked.connect(self.leave_session)
        header_layout.addWidget(leave_btn)

        main_content_layout.addWidget(header)

        viz_container = QVBoxLayout()
        viz_container.setSpacing(5)
        
        viz_title = QLabel("🎨 AI Whiteboard - Visualizing Teacher's Explanation")
        viz_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        viz_title.setStyleSheet("color: #2D3748; background: transparent;")
        viz_container.addWidget(viz_title)
        
        self.viz_frame = QFrame()
        self.viz_frame.setMinimumHeight(450)  # Increased for better visualization
        self.viz_frame.setStyleSheet("""
            QFrame {
                background: white;
                border: 3px solid #E2E8F0;
                border-radius: 12px;
            }
        """)
        
        viz_layout = QVBoxLayout(self.viz_frame)
        viz_layout.setContentsMargins(10, 10, 10, 10)
        viz_layout.setSpacing(5)
        
        self.viz_label = QLabel()
        self.viz_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.viz_label.setStyleSheet("""
            QLabel {
                background: white;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        self.viz_label.setMinimumSize(700, 400)
        self.viz_label.setText("⏳ Waiting for teacher's explanation...\n\n✨ AI will create professional visualizations\nevery 20 words for better understanding.\n\n📊 Expecting: Clear diagrams • Readable text • Beautiful designs")
        self.viz_label.setFont(QFont("Segoe UI", 12))
        self.viz_label.setWordWrap(True)
        viz_layout.addWidget(self.viz_label)
        
        self.viz_status = QLabel("Ready for professional 20-word visualization")
        self.viz_status.setFont(QFont("Segoe UI", 10))
        self.viz_status.setStyleSheet("color: #718096; text-align: center;")
        self.viz_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        viz_layout.addWidget(self.viz_status)
        
        viz_container.addWidget(self.viz_frame)
        main_content_layout.addLayout(viz_container, 8)

        subtitle_container = QVBoxLayout()
        subtitle_container.setSpacing(3)
        
        self.subtitle_display = QLabel("Waiting for teacher's speech...")
        self.subtitle_display.setFont(QFont("Segoe UI", 16, QFont.Weight.Medium))
        self.subtitle_display.setMinimumHeight(40)
        self.subtitle_display.setMaximumHeight(80)
        self.subtitle_display.setStyleSheet("""
            QLabel {
                background: rgba(0, 0, 0, 0.7);
                color: white;
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 8px;
                padding: 10px 15px;
                font-weight: 500;
            }
        """)
        self.subtitle_display.setWordWrap(True)
        self.subtitle_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_container.addWidget(self.subtitle_display)
        
        main_content_layout.addLayout(subtitle_container, 1)

        # Chat panel widget (initially hidden)
        self.chat_panel = QWidget()
        self.chat_panel.setMinimumWidth(300)
        self.chat_panel.setMaximumWidth(400)
        self.chat_panel.setStyleSheet("""
            QWidget {
                background: white;
                border-left: 1px solid #E2E8F0;
            }
        """)
        chat_panel_layout = QVBoxLayout(self.chat_panel)
        chat_panel_layout.setSpacing(0)
        chat_panel_layout.setContentsMargins(0, 0, 0, 0)
        
        # Chat header
        chat_header = QFrame()
        chat_header.setFixedHeight(50)
        chat_header.setStyleSheet("""
            QFrame {
                background: #4299E1;
                border: none;
            }
        """)
        chat_header_layout = QHBoxLayout(chat_header)
        chat_header_layout.setContentsMargins(15, 0, 15, 0)
        
        chat_title = QLabel("💬 Live Chat")
        chat_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        chat_title.setStyleSheet("color: white;")
        chat_header_layout.addWidget(chat_title)
        chat_header_layout.addStretch()
        
        close_chat_btn = QPushButton("✕")
        close_chat_btn.setFixedSize(24, 24)
        close_chat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_chat_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: white;
                border: none;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #E2E8F0;
            }
        """)
        close_chat_btn.clicked.connect(self.toggle_chat_panel)
        chat_header_layout.addWidget(close_chat_btn)
        
        chat_panel_layout.addWidget(chat_header)
        
        # Chat display area
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Segoe UI", 9))
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background: white;
                color: #2D3748;
                border: none;
                padding: 10px;
            }
        """)
        chat_panel_layout.addWidget(self.chat_display, 1)
        
        # Chat input area
        chat_input_frame = QFrame()
        chat_input_frame.setFixedHeight(60)
        chat_input_frame.setStyleSheet("""
            QFrame {
                background: #F7FAFC;
                border-top: 1px solid #E2E8F0;
            }
        """)
        chat_input_layout = QHBoxLayout(chat_input_frame)
        chat_input_layout.setContentsMargins(10, 10, 10, 10)
        chat_input_layout.setSpacing(5)
        
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Type message...")
        self.chat_input.setFont(QFont("Segoe UI", 9))
        self.chat_input.setStyleSheet("""
            QLineEdit {
                background: white;
                color: #2D3748;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                padding: 8px 10px;
            }
            QLineEdit:focus {
                border-color: #4299E1;
            }
        """)
        self.chat_input.returnPressed.connect(self.send_chat_message)
        chat_input_layout.addWidget(self.chat_input)
        
        self.send_btn = QPushButton("Send")
        self.send_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        self.send_btn.setFixedSize(60, 30)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #4299E1;
                color: white;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #3182CE;
            }
        """)
        self.send_btn.clicked.connect(self.send_chat_message)
        chat_input_layout.addWidget(self.send_btn)
        
        chat_panel_layout.addWidget(chat_input_frame)
        
        # Add widgets to splitter
        self.splitter.addWidget(main_content_widget)
        self.splitter.addWidget(self.chat_panel)
        
        # Initially hide chat panel
        self.chat_panel.hide()
        self.splitter.setSizes([1000, 0])
        
        self.main_layout.addWidget(self.splitter)
        self.start_firebase_listener()
        self.is_in_session = True

    def toggle_chat_panel(self):
        """Toggle chat panel visibility"""
        self.chat_panel_visible = not self.chat_panel_visible
        
        if self.chat_panel_visible:
            self.chat_panel.show()
            self.splitter.setSizes([700, 300])
            self.chat_toggle_btn.setText("💬 Close Chat")
            self.chat_toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3182CE;
                    color: white;
                    border-radius: 6px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #2B6CB0;
                }
            """)
        else:
            self.chat_panel.hide()
            self.splitter.setSizes([1000, 0])
            self.chat_toggle_btn.setText("💬 Chat")
            self.chat_toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4299E1;
                    color: white;
                    border-radius: 6px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #3182CE;
                }
            """)

    def send_chat_message(self):
        """Send chat message to Firebase"""
        message = self.chat_input.text().strip()
        if not message:
            return
        
        self.chat_input.clear()
        QTimer.singleShot(10, lambda: self._send_chat_to_firebase(message))

    def _send_chat_to_firebase(self, message):
        """Send chat message to Firebase with proper error handling"""
        try:
            response = requests.get(f"{FIREBASE_URL}/sessions.json")
            if response.status_code == 200:
                sessions = response.json() or {}
                
                for session_id, session_data in sessions.items():
                    if session_data and session_data.get("session_code") == self.session_code:
                        existing_chat = session_data.get("chat_messages", [])
                        if not isinstance(existing_chat, list):
                            existing_chat = []
                        
                        chat_data = {
                            "sender": "student",
                            "student_name": self.student_name,
                            "message": message,
                            "timestamp": int(time.time())
                        }
                        existing_chat.append(chat_data)
                        
                        update_data = {
                            "chat_messages": existing_chat,
                            "last_updated": int(time.time())
                        }
                        
                        patch_response = requests.patch(
                            f"{FIREBASE_URL}/sessions/{session_id}.json",
                            json=update_data
                        )
                        
                        if patch_response.status_code == 200:
                            print(f"✅ Chat message sent: {self.student_name}: {message}")
                        break
                    
        except Exception as e:
            print(f"❌ Failed to send chat: {e}")

    def update_chat_display(self, message_data):
        """Update chat display with new messages from Firebase"""
        try:
            sender = message_data.get("sender", "")
            student_name = message_data.get("student_name", "")
            message = message_data.get("message", "")
            timestamp_int = message_data.get("timestamp", time.time())
            
            timestamp = time.strftime("%H:%M", time.localtime(timestamp_int))
            
            if sender == "student" and student_name == self.student_name:
                formatted_message = f'<div style="color: #2B6CB0; margin: 3px 0; padding: 4px; background: #BEE3F8; border-radius: 4px;"><b>You [{timestamp}]:</b> {message}</div>'
            elif sender == "teacher":
                formatted_message = f'<div style="color: #22543D; margin: 3px 0; padding: 4px; background: #C6F6D5; border-radius: 4px;"><b>👨‍🏫 Teacher [{timestamp}]:</b> {message}</div>'
            elif sender == "student":
                formatted_message = f'<div style="color: #744210; margin: 3px 0; padding: 4px; background: #FEEBC8; border-radius: 4px;"><b>👤 {student_name} [{timestamp}]:</b> {message}</div>'
            else:
                formatted_message = f'<div style="color: #4A5568; margin: 3px 0; padding: 4px; background: #EDF2F7; border-radius: 4px;"><b>{sender} [{timestamp}]:</b> {message}</div>'
            
            self.chat_display.append(formatted_message)
            
            scrollbar = self.chat_display.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
            
        except Exception as e:
            print(f"Error updating chat: {e}")

    def leave_session(self):
        """Leave session and reset processors"""
        if self.firebase_listener:
            self.firebase_listener.stop()
            self.firebase_listener.wait(1000)
            self.firebase_listener = None
        
        self.word_buffer = []
        self.total_words_processed = 0
        self.is_generating_visual = False
        self.setup_join_interface()

    def start_firebase_listener(self):
        """Start optimized Firebase listener"""
        self.firebase_listener = FirebaseListener(self.session_code)
        self.firebase_listener.new_transcript.connect(self.update_display)
        self.firebase_listener.new_chat_message.connect(self.update_chat_display)
        self.firebase_listener.connection_status.connect(self.update_connection_status)
        self.firebase_listener.start()

    def update_connection_status(self, connected):
        """Update connection status"""
        if connected:
            self.connection_label.setText("🟢 Connected")
            self.connection_label.setStyleSheet("""
                color: #38A169;
                background: rgba(72, 187, 120, 0.1);
                padding: 5px 10px;
                border-radius: 12px;
                border: 1px solid rgba(72, 187, 120, 0.3);
            """)
        else:
            self.connection_label.setText("🔴 Connecting...")
            self.connection_label.setStyleSheet("""
                color: #D69E2E;
                background: rgba(214, 158, 46, 0.1);
                padding: 5px 10px;
                border-radius: 12px;
                border: 1px solid rgba(214, 158, 46, 0.3);
            """)

    def update_display(self, transcript):
        """Process transcript with 20-word chunk visualization"""
        if not transcript or not transcript.strip():
            return
        
        # Clean the transcript
        clean_transcript = self._clean_transcript(transcript)
        
        # Display transcript
        self.subtitle_display.setText(clean_transcript[:100] + ("..." if len(clean_transcript) > 100 else ""))
        
        # Process for 20-word visualization
        self.process_for_visualization(clean_transcript)
    
    def _clean_transcript(self, text):
        """Clean transcript text"""
        if not text:
            return ""
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r'[^\w\s.,!?]', '', text)
        return text[:200]
    
    def process_for_visualization(self, transcript):
        """Process transcript in 20-word chunks"""
        current_time = time.time()
        
        # Check cooldown and if already generating
        if (current_time - self.last_visualization_time < self.visualization_cooldown or 
            self.is_generating_visual):
            return
        
        # Add words to buffer
        words = transcript.split()
        new_word_count = len(words)
        
        if new_word_count == 0:
            return
        
        # Add new words to buffer
        self.word_buffer.extend(words)
        self.total_words_processed += new_word_count
        
        # Check if we have accumulated enough NEW words
        if len(self.word_buffer) >= self.word_count_threshold:
            # Check if we should generate a visualization
            chunks_needed = self.total_words_processed // self.word_count_threshold
            chunks_generated = (self.total_words_processed - len(self.word_buffer)) // self.word_count_threshold
            
            if chunks_needed > chunks_generated:
                print(f"📊 Generating professional visualization for chunk {chunks_needed} (total words: {self.total_words_processed})")
                
                # Take exactly 20 words for visualization
                chunk_words = self.word_buffer[:self.word_count_threshold]
                chunk_text = " ".join(chunk_words)
                
                print(f"📊 Processing 20-word chunk: {chunk_text[:50]}...")
                
                # Generate visualization
                self.generate_visualization(chunk_text)
                
                # Remove processed words from buffer
                self.word_buffer = self.word_buffer[self.word_count_threshold:]
                
                self.last_visualization_time = current_time
                self.is_generating_visual = True
                
                # Schedule reset of generation flag
                QTimer.singleShot(2000, self._reset_generation_flag)
    
    def _reset_generation_flag(self):
        """Reset the generation flag after visualization is complete"""
        self.is_generating_visual = False
        print("🔄 Visualization generation ready for next chunk")
    
    def generate_visualization(self, chunk_text):
        """Generate professional visualization for 20-word chunk"""
        self.viz_status.setText("✨ AI creating professional visualization...")
        
        # Create a cache key from the chunk text
        cache_key = hash(chunk_text[:50])  # Use first 50 chars as key
        
        # Check cache first
        if cache_key in self.visual_cache:
            print("✅ Using cached professional visualization")
            pixmap = self.visual_cache[cache_key]
            self.viz_label.setPixmap(pixmap)
            self.viz_status.setText(f"✅ Professional 20-word visualization (cached)")
            return
        
        # Generate visual concept in background
        QTimer.singleShot(50, lambda: self._generate_visual_async(chunk_text, cache_key))
    
    def _generate_visual_async(self, chunk_text, cache_key):
        """Async visualization generation"""
        try:
            # Generate professional concept
            visual_concept = self.visual_generator.generate_professional_concept(chunk_text)
            
            if visual_concept:
                print(f"🎨 Generated professional visual concept")
                
                # Create professional visualization
                pixmap = self.visual_renderer.create_professional_visual(visual_concept, 700, 400)
                
                if pixmap and not pixmap.isNull():
                    # Cache the visualization
                    self.visual_cache[cache_key] = pixmap
                    
                    # Limit cache size
                    if len(self.visual_cache) > 10:
                        # Remove oldest entry
                        self.visual_cache.pop(next(iter(self.visual_cache)))
                    
                    # Display immediately
                    self.viz_label.setPixmap(pixmap)
                    self.viz_status.setText(f"✅ Professional 20-word visualization")
                    print(f"✅ Professional visualization displayed and cached")
                else:
                    self.viz_status.setText("✨ Creating fallback visualization...")
                    self._show_fallback_visual()
            else:
                self._show_fallback_visual()
                
        except Exception as e:
            print(f"❌ Visualization error: {e}")
            self._show_fallback_visual()
    
    def _show_fallback_visual(self):
        """Show beautiful fallback visualization"""
        try:
            # Create professional fallback visual
            pixmap = QPixmap(700, 400)
            
            # Create gradient background
            gradient = QLinearGradient(0, 0, 700, 400)
            gradient.setColorAt(0, QColor(248, 249, 250))
            gradient.setColorAt(1, QColor(241, 243, 245))
            pixmap.fill(QColor(248, 249, 250))
            
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Draw subtle grid
            painter.setPen(QPen(QColor(229, 231, 235, 50), 1))
            grid_size = 40
            for x in range(0, 701, grid_size):
                painter.drawLine(x, 0, x, 400)
            for y in range(0, 401, grid_size):
                painter.drawLine(0, y, 700, y)
            
            # Draw central concept
            center_x, center_y = 350, 200
            
            # Draw main circle with gradient
            main_gradient = QLinearGradient(center_x - 100, center_y - 100, center_x + 100, center_y + 100)
            main_gradient.setColorAt(0, QColor('#667eea'))
            main_gradient.setColorAt(1, QColor('#764ba2'))
            
            painter.setBrush(QBrush(main_gradient))
            painter.setPen(QPen(QColor(30, 41, 59), 3))
            painter.drawEllipse(center_x - 100, center_y - 100, 200, 200)
            
            # Draw inner circle
            painter.setBrush(QBrush(QColor(255, 255, 255, 50)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(center_x - 80, center_y - 80, 160, 160)
            
            # Text
            painter.setPen(QPen(Qt.GlobalColor.white))
            painter.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
            painter.drawText(center_x - 80, center_y - 30, 160, 60, Qt.AlignmentFlag.AlignCenter, "Learning\nVisualized")
            
            # Add decorative elements
            colors = ['#4facfe', '#00f2fe', '#43e97b', '#38f9d7']
            for i in range(4):
                angle = math.pi * 2 * i / 4
                x = center_x + int(180 * math.cos(angle))
                y = center_y + int(180 * math.sin(angle))
                
                painter.setBrush(QBrush(QColor(colors[i])))
                painter.setPen(QPen(QColor(30, 41, 59), 2))
                painter.drawEllipse(x - 30, y - 30, 60, 60)
                
                # Connection line
                painter.setPen(QPen(QColor(colors[i], 150), 3))
                painter.drawLine(center_x, center_y, x, y)
            
            # Add subtitle
            painter.setPen(QPen(QColor(100, 116, 139)))
            painter.setFont(QFont("Segoe UI", 12))
            painter.drawText(center_x - 150, center_y + 120, 300, 30, Qt.AlignmentFlag.AlignCenter, "Next visualization in 10 seconds...")
            
            painter.end()
            self.viz_label.setPixmap(pixmap)
            self.viz_status.setText("📊 Next professional visualization in 10 seconds...")
            
        except Exception as e:
            print(f"Fallback visual error: {e}")

    def closeEvent(self, event):
        """Cleanup on close"""
        if self.firebase_listener:
            self.firebase_listener.stop()
            self.firebase_listener.wait(1000)
        event.accept()

# ==========================================================
# Teacher Session Page (Updated with Chat Panel)
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
        
        # Initialize Whisper
        print("Initializing Whisper STT...")
        self.whisper_processor = WhisperSTTProcessor(model_size="base")
        self.whisper_processor.model_loaded.connect(self.on_whisper_loaded)
        self.whisper_processor.transcription_ready.connect(self.on_transcription_ready)
        self.whisper_loaded = False
        self.whisper_processor.start()
        
        # TTS tracking
        self.last_spoken_content = ""
        self.last_spoken_time = 0
        self.min_speech_interval = 2.0
        self.student_name = "Student"
        
        # Chat panel visibility
        self.chat_panel_visible = False
        
        # Create session
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

    def on_whisper_loaded(self, success, message):
        """Called when Whisper is loaded"""
        if success:
            print(f"✅ {message}")
            self.whisper_loaded = True
        else:
            print(f"❌ {message}")

    def on_transcription_ready(self, text):
        """Handle completed transcription"""
        if text and text.strip():
            self.current_transcript = text
            self.teacher_transcript_label.setText(text)
            self.update_transcript_in_firebase(text)

    def init_ui(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #FAFAFA;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # App Bar
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
        
        session_info = QLabel(f"Session: {self.session_code}")
        session_info.setFont(QFont("Segoe UI", 12))
        session_info.setStyleSheet("""
            color: rgba(255,255,255,0.9); 
            background: rgba(255,255,255,0.15); 
            padding: 8px 16px; 
            border-radius: 16px;
        """)
        app_bar_layout.addWidget(session_info)
        
        self.stt_status = QLabel("🤖 Loading Whisper...")
        self.stt_status.setFont(QFont("Segoe UI", 11))
        self.stt_status.setStyleSheet("""
            color: white; 
            background: rgba(255,255,255,0.15); 
            padding: 8px 16px; 
            border-radius: 16px;
        """)
        app_bar_layout.addWidget(self.stt_status)
        
        self.connection_status = QLabel("🟢 Connected")
        self.connection_status.setFont(QFont("Segoe UI", 11))
        self.connection_status.setStyleSheet("""
            color: white; 
            background: rgba(255,255,255,0.15); 
            padding: 8px 16px; 
            border-radius: 16px;
        """)
        app_bar_layout.addWidget(self.connection_status)
        
        # Chat toggle button
        self.chat_toggle_btn = QPushButton("💬 Chat")
        self.chat_toggle_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        self.chat_toggle_btn.setFixedSize(80, 36)
        self.chat_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chat_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255,255,255,0.2);
                color: white;
                border: 1px solid rgba(255,255,255,0.3);
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: rgba(255,255,255,0.3);
            }
        """)
        self.chat_toggle_btn.clicked.connect(self.toggle_chat_panel)
        app_bar_layout.addWidget(self.chat_toggle_btn)
        
        layout.addWidget(app_bar)

        # Create splitter for main content and chat panel
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        
        # Main Content Widget
        main_content_widget = QWidget()
        main_content_widget.setStyleSheet("background-color: #FAFAFA;")
        content_layout = QVBoxLayout(main_content_widget)
        content_layout.setSpacing(20)
        content_layout.setContentsMargins(25, 25, 25, 25)

        # Controls
        controls_card = QWidget()
        controls_card.setFixedHeight(140)
        controls_card.setStyleSheet("""
            QWidget {
                background: white;
                border-radius: 16px;
                border: none;
            }
        """)
        controls_layout = QHBoxLayout(controls_card)
        controls_layout.setContentsMargins(30, 25, 30, 25)
        
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

        main_content = QHBoxLayout()
        main_content.setSpacing(25)

        left_panel = QVBoxLayout()
        left_panel.setSpacing(25)

        student_card = QWidget()
        student_card.setStyleSheet("""
            QWidget {
                background: white;
                border-radius: 16px;
                border: none;
            }
        """)
        student_layout = QVBoxLayout(student_card)
        student_layout.setContentsMargins(25, 25, 25, 25)
        student_layout.setSpacing(20)
        
        student_header = QHBoxLayout()
        student_title = QLabel("Student Communication")
        student_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        student_title.setStyleSheet("color: #1976D2;")
        student_header.addWidget(student_title)
        student_header.addStretch()
        
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
        signs_section.addWidget(self.student_transcript_label)
        student_layout.addLayout(signs_section)

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

        teacher_card = QWidget()
        teacher_card.setStyleSheet("""
            QWidget {
                background: white;
                border-radius: 16px;
                border: none;
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
        teacher_layout.addWidget(self.teacher_transcript_label)
        
        left_panel.addWidget(teacher_card)

        main_content.addLayout(left_panel, 1)

        right_panel = QVBoxLayout()
        right_panel.setSpacing(25)

        status_card = QWidget()
        status_card.setStyleSheet("""
            QWidget {
                background: white;
                border-radius: 16px;
                border: none;
            }
        """)
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(25, 25, 25, 25)
        status_layout.setSpacing(20)
        
        status_title = QLabel("Session Status")
        status_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        status_title.setStyleSheet("color: #1976D2;")
        status_layout.addWidget(status_title)
        
        status_info = QLabel("• Session is active\n• Student can join using code\n• Chat is available\n• Voice output is enabled")
        status_info.setFont(QFont("Segoe UI", 12))
        status_info.setStyleSheet("""
            QLabel {
                color: #616161;
                line-height: 1.6;
            }
        """)
        status_info.setWordWrap(True)
        status_layout.addWidget(status_info)
        
        right_panel.addWidget(status_card)

        main_content.addLayout(right_panel, 1)
        content_layout.addLayout(main_content)
        
        # Add main content widget to splitter
        self.splitter.addWidget(main_content_widget)
        
        # Chat Panel Widget (initially hidden)
        self.chat_panel = QWidget()
        self.chat_panel.setMinimumWidth(300)
        self.chat_panel.setMaximumWidth(400)
        self.chat_panel.setStyleSheet("""
            QWidget {
                background: white;
                border-left: 1px solid #E2E8F0;
            }
        """)
        chat_panel_layout = QVBoxLayout(self.chat_panel)
        chat_panel_layout.setSpacing(0)
        chat_panel_layout.setContentsMargins(0, 0, 0, 0)
        
        # Chat header
        chat_header = QFrame()
        chat_header.setFixedHeight(50)
        chat_header.setStyleSheet("""
            QFrame {
                background: #2196F3;
                border: none;
            }
        """)
        chat_header_layout = QHBoxLayout(chat_header)
        chat_header_layout.setContentsMargins(15, 0, 15, 0)
        
        chat_title = QLabel("💬 Live Chat")
        chat_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        chat_title.setStyleSheet("color: white;")
        chat_header_layout.addWidget(chat_title)
        chat_header_layout.addStretch()
        
        close_chat_btn = QPushButton("✕")
        close_chat_btn.setFixedSize(24, 24)
        close_chat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_chat_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: white;
                border: none;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #E3F2FD;
            }
        """)
        close_chat_btn.clicked.connect(self.toggle_chat_panel)
        chat_header_layout.addWidget(close_chat_btn)
        
        chat_panel_layout.addWidget(chat_header)
        
        # Chat display area
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Segoe UI", 12))
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background: white;
                color: #424242;
                border: none;
                padding: 16px;
                line-height: 1.4;
            }
        """)
        chat_panel_layout.addWidget(self.chat_display, 1)
        
        # Chat input area
        chat_input_frame = QFrame()
        chat_input_frame.setFixedHeight(80)
        chat_input_frame.setStyleSheet("""
            QFrame {
                background: #F5F5F5;
                border-top: 1px solid #E0E0E0;
            }
        """)
        chat_input_layout = QVBoxLayout(chat_input_frame)
        chat_input_layout.setContentsMargins(15, 10, 15, 10)
        chat_input_layout.setSpacing(8)
        
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
        
        send_button_layout = QHBoxLayout()
        send_button_layout.addStretch()
        
        self.send_chat_button = QPushButton("Send")
        self.send_chat_button.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.send_chat_button.setFixedSize(80, 36)
        self.send_chat_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_chat_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.send_chat_button.clicked.connect(self.send_chat_message)
        send_button_layout.addWidget(self.send_chat_button)
        
        chat_input_layout.addLayout(send_button_layout)
        chat_panel_layout.addWidget(chat_input_frame)
        
        # Add chat panel to splitter
        self.splitter.addWidget(self.chat_panel)
        
        # Initially hide chat panel
        self.chat_panel.hide()
        self.splitter.setSizes([1000, 0])
        
        layout.addWidget(self.splitter)
        self.setLayout(layout)
        self.timer = QTimer()
        self.timer.timeout.connect(self.process_audio)
        self.timer.start(100)

    def toggle_chat_panel(self):
        """Toggle chat panel visibility"""
        self.chat_panel_visible = not self.chat_panel_visible
        
        if self.chat_panel_visible:
            self.chat_panel.show()
            self.splitter.setSizes([700, 300])
            self.chat_toggle_btn.setText("💬 Close Chat")
            self.chat_toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255,255,255,0.3);
                    color: white;
                    border: 1px solid rgba(255,255,255,0.4);
                    border-radius: 8px;
                }
                QPushButton:hover {
                    background-color: rgba(255,255,255,0.4);
                }
            """)
        else:
            self.chat_panel.hide()
            self.splitter.setSizes([1000, 0])
            self.chat_toggle_btn.setText("💬 Chat")
            self.chat_toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255,255,255,0.2);
                    color: white;
                    border: 1px solid rgba(255,255,255,0.3);
                    border-radius: 8px;
                }
                QPushButton:hover {
                    background-color: rgba(255,255,255,0.3);
                }
            """)

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
            
        # Check if this is a system message (not actual student content)
        system_phrases = [
            "student has not started", 
            "waiting for student", 
            "session created",
            "share the code",
            "waiting for student...",
            "has not started signing"
        ]
        
        transcript_lower = transcript.lower()
        if any(phrase in transcript_lower for phrase in system_phrases):
            print("Skipping system message TTS")
            return
        
        new_words = self.get_new_words(transcript)
        self.last_full_transcript = transcript
        
        for word in new_words:
            if len(word) > 1 and word.lower() not in system_phrases:
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
        """Speak student's chat message"""
        if not self.tts_enabled or not message.strip():
            return
            
        current_time = time.time()
        
        # Format: "Student says: hello"
        chat_content = f"{self.student_name} says {message}"
        
        if (chat_content == self.last_spoken_content and 
            current_time - self.last_spoken_time < self.min_speech_interval):
            return
            
        self.last_spoken_content = chat_content
        self.last_spoken_time = current_time
        
        print(f"Speaking chat message: {chat_content}")
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
            
            # DO NOT speak teacher's own messages
            print("Teacher message sent (not spoken)")
        else:
            print("Failed to send chat message")

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
        student_name = message_data.get("student_name", "")
        message = message_data.get("message", "")
        timestamp = time.strftime("%H:%M:%S", time.localtime(message_data.get("timestamp", time.time())))
        
        if sender == "student":
            display_name = student_name if student_name else self.student_name
            self.chat_display.append(f'<div style="color: #1976D2; margin: 10px 0;"><b>[{timestamp}] {display_name}:</b> {message}</div>')
            self.chat_display.verticalScrollBar().setValue(
                self.chat_display.verticalScrollBar().maximum()
            )
            
            # Only speak student messages
            self.speak_chat_message(message)
            
        elif sender == "teacher":
            # Teacher's messages - just display, don't speak
            self.chat_display.append(f'<div style="color: #424242; margin: 10px 0;"><b>[{timestamp}] You:</b> {message}</div>')
            self.chat_display.verticalScrollBar().setValue(
                self.chat_display.verticalScrollBar().maximum()
            )

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
            if self.whisper_loaded:
                self.stt_status.setText("🤖 Whisper Ready")
                self.stt_status.setStyleSheet("color: white; background: rgba(255,255,255,0.15); padding: 8px 16px; border-radius: 16px;")
        else:
            self.connection_status.setText("🔴 Connecting...")
            self.connection_status.setStyleSheet("color: white; background: rgba(255,255,255,0.15); padding: 8px 16px; border-radius: 16px;")

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
        if self.whisper_processor:
            self.whisper_processor.quit()

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
        if not self.listening or not self.whisper_loaded:
            return
            
        chunks_processed = 0
        max_chunks_per_cycle = 5
        
        while (not audio_queue.empty() and 
               chunks_processed < max_chunks_per_cycle and
               self.whisper_processor.model is not None):
            
            data = audio_queue.get()
            should_process = self.whisper_processor.add_audio_chunk(data)
            
            if should_process:
                chunks_processed += 1
            
            time.sleep(0.01)
        
        if chunks_processed > 0:
            self.timer.setInterval(50)
        else:
            self.timer.setInterval(100)

    def closeEvent(self, event):
        """Handle window close event"""
        self.cleanup_firebase_session()
        event.accept()

# ==========================================================
# Main Teacher Widget
# ==========================================================
class TeacherPage(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.stacked_widget = QStackedWidget()
        
        self.session_creation_page = SessionCreationPage()
        self.teacher_session_page = None
        
        self.session_creation_page.session_created.connect(self.on_session_created)
        
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