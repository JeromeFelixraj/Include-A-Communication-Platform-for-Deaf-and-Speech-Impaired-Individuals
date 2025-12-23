import sys
import os
import google.generativeai as genai
from dotenv import load_dotenv
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QStackedWidget, QLabel, QFrame, QTextEdit, QLineEdit, QScrollArea
)
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect
from teacher_page import TeacherPage
from deaf_student_page import StudentPage
from mute_studentpage import MuteStudentPage
from ai_assistant_page import AIAssistantPage  # Import the speaking AI assistant

# Load environment variables
load_dotenv()

class AIWorker(QThread):
    """Worker thread for AI processing to prevent UI freezing"""
    response_received = pyqtSignal(str, bool)  # message, success
    
    def __init__(self, user_id, message):
        super().__init__()
        self.user_id = user_id
        self.message = message
    
    def run(self):
        try:
            # Get response from Gemini
            response = AIAssistant.get_instance().send_message(self.user_id, self.message)
            if response['success']:
                self.response_received.emit(response['response'], True)
            else:
                error_msg = response.get('error', 'Unknown error occurred')
                self.response_received.emit(f"AI Error: {error_msg}", False)
                
        except Exception as e:
            error_msg = f"Connection error: {str(e)}"
            self.response_received.emit(error_msg, False)

class AIAssistant:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = AIAssistant()
        return cls._instance
    
    def __init__(self):
        if AIAssistant._instance is not None:
            raise Exception("This class is a singleton!")
        
        # Configure Gemini
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in .env file. Please add it to your .env file.")
        
        genai.configure(api_key=api_key)
        
        # Use the working model that was found in your console
        self.model_name = "gemini-2.5-flash"  # Updated to stable model
        self.model = genai.GenerativeModel(self.model_name)
        
        # Store chats by user ID
        self.user_chats = {}
        
        print(f"🤖 Gemini AI Assistant initialized successfully with model: {self.model_name}")
    
    def get_chat(self, user_id):
        """Get or create a chat session for a user"""
        if user_id not in self.user_chats:
            self.user_chats[user_id] = self.model.start_chat(history=[])
        return self.user_chats[user_id]
    
    def send_message(self, user_id, message):
        """Send message to AI and get response"""
        try:
            chat = self.get_chat(user_id)
            response = chat.send_message(message)
            return {
                'success': True,
                'response': response.text
            }
        except Exception as e:
            error_msg = str(e)
            # Provide more user-friendly error messages
            if "API_KEY_INVALID" in error_msg:
                error_msg = "Invalid API key. Please check your GEMINI_API_KEY in the .env file."
            elif "quota" in error_msg.lower():
                error_msg = "API quota exceeded. Please try again later."
            elif "503" in error_msg:
                error_msg = "Service temporarily unavailable. Please try again."
            elif "429" in error_msg:
                error_msg = "Too many requests. Please wait a moment."
            
            return {
                'success': False,
                'error': error_msg
            }
    
    def clear_chat(self, user_id):
        """Clear chat history for a user"""
        if user_id in self.user_chats:
            self.user_chats[user_id] = self.model.start_chat(history=[])
            return True
        return False

class CollapsibleAIAssistant(QWidget):
    def __init__(self):
        super().__init__()
        self.is_expanded = False
        self.animation_duration = 300
        self.init_ui()
        
    def init_ui(self):
        # Main layout for the collapsible assistant
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Toggle button (always visible)
        self.toggle_btn = QPushButton("🤖")
        self.toggle_btn.setFixedSize(50, 50)
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #4299E1;
                color: white;
                border: none;
                border-radius: 25px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3182CE;
            }
        """)
        self.toggle_btn.clicked.connect(self.toggle_assistant)
        
        # AI Assistant Widget
        self.assistant_widget = AIAssistantWidget()
        self.assistant_widget.setMinimumWidth(350)
        self.assistant_widget.setMaximumWidth(450)
        self.assistant_widget.hide()
        
        # Add widgets to layout
        main_layout.addWidget(self.assistant_widget)
        main_layout.addWidget(self.toggle_btn)
        
        self.setLayout(main_layout)
        
        # Set initial state
        self.update_toggle_button()
    
    def toggle_assistant(self):
        """Toggle the assistant visibility with animation"""
        self.is_expanded = not self.is_expanded
        
        if self.is_expanded:
            self.expand_assistant()
        else:
            self.collapse_assistant()
        
        self.update_toggle_button()
    
    def expand_assistant(self):
        """Show and expand the assistant"""
        self.assistant_widget.show()
    
    def collapse_assistant(self):
        """Hide and collapse the assistant"""
        self.assistant_widget.hide()
    
    def update_toggle_button(self):
        """Update toggle button appearance based on state"""
        if self.is_expanded:
            self.toggle_btn.setText("❌")
            self.toggle_btn.setToolTip("Close Assistant")
        else:
            self.toggle_btn.setText("🤖")
            self.toggle_btn.setToolTip("Open Assistant")

class AIAssistantWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.current_user_id = "student_user"  # You can make this dynamic based on login
        self.ai_worker = None
        self.typing_indicator_added = False
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        # Header with title and close button
        header_layout = QHBoxLayout()
        
        title = QLabel("🤖 Classroom Assistant")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #2D3748;")
        
        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(30, 30)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #E53E3E;
                color: white;
                border-radius: 15px;
                border: none;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #C53030;
            }
        """)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.close_btn)
        layout.addLayout(header_layout)
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setFont(QFont("Segoe UI", 9))
        self.status_label.setStyleSheet("color: #718096; text-align: center;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Clear chat button
        clear_btn = QPushButton("Clear Chat")
        clear_btn.setFont(QFont("Segoe UI", 10))
        clear_btn.setFixedHeight(30)
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #718096;
                color: white;
                border-radius: 6px;
                border: none;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #4A5568;
            }
        """)
        clear_btn.clicked.connect(self.clear_chat)
        layout.addWidget(clear_btn)
        
        # Chat display area
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Segoe UI", 11))
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: #FFFFFF;
                color: #2D3748;
                border: 2px solid #E2E8F0;
                border-radius: 12px;
                padding: 15px;
                min-height: 300px;
            }
        """)
        layout.addWidget(self.chat_display)
        
        # Chat input area
        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)
        
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Ask me anything...")
        self.chat_input.setFont(QFont("Segoe UI", 11))
        self.chat_input.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                color: #2D3748;
                border: 2px solid #E2E8F0;
                border-radius: 8px;
                padding: 12px 15px;
            }
            QLineEdit:focus {
                border-color: #4299E1;
            }
            QLineEdit::placeholder {
                color: #A0AEC0;
            }
        """)
        self.chat_input.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.chat_input)
        
        self.send_btn = QPushButton("Send")
        self.send_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        self.send_btn.setFixedSize(80, 45)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #4299E1;
                color: white;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background-color: #3182CE;
            }
            QPushButton:disabled {
                background-color: #CBD5E0;
            }
        """)
        self.send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_btn)
        
        layout.addLayout(input_layout)
        
        self.setLayout(layout)
        self.show_welcome_message()
        self.update_status("Ready to help!")
        
        # Set up close button connection
        self.close_btn.clicked.connect(self.hide_assistant)
    
    def hide_assistant(self):
        """Hide the assistant - signal for parent to handle"""
        self.parent().parent().toggle_assistant()
    
    def update_status(self, message):
        """Update the status label"""
        self.status_label.setText(message)
    
    def show_welcome_message(self):
        """Show welcome message in chat"""
        welcome_html = """
        <div style='text-align: center; color: #718096; padding: 10px; margin-bottom: 15px;'>
            <b>Welcome to Classroom Assistant!</b>
        </div>
        <div style='background: #EBF8FF; color: #2B6CB0; padding: 12px; border-radius: 8px; margin: 8px 0; border-left: 4px solid #4299E1;'>
            <b>Assistant:</b> Hello! I'm your AI classroom assistant. I can help you with:
            <ul style='margin: 8px 0; padding-left: 20px;'>
                <li>Homework questions and explanations</li>
                <li>Study techniques and time management</li>
                <li>Concept clarification in any subject</li>
                <li>Assignment planning and guidance</li>
                <li>Technical help with classroom tools</li>
            </ul>
            How can I help you today?
        </div>
        """
        self.chat_display.setHtml(welcome_html)
    
    def send_message(self):
        """Handle sending messages to Gemini AI"""
        try:
            message = self.chat_input.text().strip()
            if not message:
                return
            
            # Disable input while processing
            self.set_input_enabled(False)
            self.update_status("Processing...")
            
            # Add user message to chat
            self.add_message(message, "user")
            self.chat_input.clear()
            
            # Show typing indicator
            self.add_typing_indicator()
            
            # Start AI worker thread
            self.ai_worker = AIWorker(self.current_user_id, message)
            self.ai_worker.response_received.connect(self.handle_ai_response)
            self.ai_worker.start()
            
        except Exception as e:
            print(f"Error sending message: {e}")
            self.set_input_enabled(True)
            self.update_status("Error - try again")
    
    def set_input_enabled(self, enabled):
        """Enable or disable chat input"""
        self.chat_input.setEnabled(enabled)
        self.send_btn.setEnabled(enabled)
        if enabled:
            self.chat_input.setFocus()
    
    def add_typing_indicator(self):
        """Show typing indicator"""
        try:
            typing_html = """
            <div style='background: #F7FAFC; color: #718096; padding: 12px; border-radius: 8px; margin: 8px 0; margin-right: 50px; border-left: 4px solid #CBD5E0; font-style: italic;'>
                <b>Assistant:</b> Thinking...
            </div>
            """
            self.append_to_chat(typing_html)
            self.typing_indicator_added = True
        except Exception as e:
            print(f"Error adding typing indicator: {e}")
    
    def remove_typing_indicator(self):
        """Remove the typing indicator safely"""
        try:
            if not self.typing_indicator_added:
                return
                
            # Get current HTML content
            current_html = self.chat_display.toHtml()
            
            # Safe way to remove typing indicator
            if "Thinking..." in current_html:
                # Split by div tags and filter out the typing indicator
                parts = current_html.split('<div style=')
                new_parts = []
                typing_removed = False
                
                for part in parts:
                    if "Thinking..." in part and not typing_removed:
                        typing_removed = True
                        continue
                    new_parts.append(part)
                
                # Rebuild HTML
                if typing_removed:
                    new_html = '<div style='.join(new_parts)
                    self.chat_display.setHtml(new_html)
            
            self.typing_indicator_added = False
            
        except Exception as e:
            print(f"Error removing typing indicator: {e}")
            # If anything fails, just clear the typing indicator flag
            self.typing_indicator_added = False
    
    def handle_ai_response(self, response, success):
        """Handle AI response from worker thread"""
        try:
            # Remove typing indicator
            self.remove_typing_indicator()
            
            if success:
                self.add_message(response, "assistant")
                self.update_status("Ready to help!")
            else:
                error_html = f"""
                <div style='background: #FED7D7; color: #C53030; padding: 12px; border-radius: 8px; margin: 8px 0; margin-right: 50px; border-left: 4px solid #E53E3E;'>
                    <b>Assistant:</b> {self.escape_html(response)}
                </div>
                """
                self.append_to_chat(error_html)
                self.update_status("Error occurred")
            
        except Exception as e:
            print(f"Error handling AI response: {e}")
            error_html = f"""
            <div style='background: #FED7D7; color: #C53030; padding: 12px; border-radius: 8px; margin: 8px 0; margin-right: 50px; border-left: 4px solid #E53E3E;'>
                <b>Assistant:</b> Error processing response: {self.escape_html(str(e))}
            </div>
            """
            self.append_to_chat(error_html)
            self.update_status("Processing error")
        finally:
            # Always re-enable input
            self.set_input_enabled(True)
    
    def escape_html(self, text):
        """Escape HTML special characters to prevent rendering issues"""
        if not text:
            return ""
        return (text.replace('&', '&amp;')
                  .replace('<', '&lt;')
                  .replace('>', '&gt;')
                  .replace('"', '&quot;')
                  .replace("'", '&#39;'))
    
    def add_message(self, message, sender):
        """Add a message to the chat display"""
        try:
            if sender == "user":
                html = f"""
                <div style='background: #4299E1; color: white; padding: 12px; border-radius: 8px; margin: 8px 0; margin-left: 50px; border-left: 4px solid #2B6CB0;'>
                    <b>You:</b> {self.escape_html(message)}
                </div>
                """
            else:
                # Format AI response with better readability
                formatted_message = self.escape_html(message).replace('\n', '<br>')
                html = f"""
                <div style='background: #F7FAFC; color: #2D3748; padding: 12px; border-radius: 8px; margin: 8px 0; margin-right: 50px; border-left: 4px solid #48BB78;'>
                    <b>Assistant:</b> {formatted_message}
                </div>
                """
            
            self.append_to_chat(html)
            
        except Exception as e:
            print(f"Error adding message: {e}")
            # Fallback: add plain text message
            fallback_html = f"""
            <div style='background: #F7FAFC; color: #2D3748; padding: 12px; border-radius: 8px; margin: 8px 0; margin-right: 50px; border-left: 4px solid #48BB78;'>
                <b>Assistant:</b> Message display error
            </div>
            """
            self.append_to_chat(fallback_html)
    
    def append_to_chat(self, html):
        """Append HTML to chat and scroll to bottom"""
        try:
            current_html = self.chat_display.toHtml()
            new_html = current_html + html
            self.chat_display.setHtml(new_html)
            
            # Auto-scroll to bottom
            scrollbar = self.chat_display.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
            
        except Exception as e:
            print(f"Error appending to chat: {e}")
    
    def clear_chat(self):
        """Clear chat history"""
        try:
            AIAssistant.get_instance().clear_chat(self.current_user_id)
            self.chat_display.clear()
            self.typing_indicator_added = False
            self.show_welcome_message()
            self.update_status("Chat cleared")
        except Exception as e:
            error_html = f"""
            <div style='background: #FED7D7; color: #C53030; padding: 12px; border-radius: 8px; margin: 8px 0;'>
                <b>Error:</b> Failed to clear chat: {self.escape_html(str(e))}
            </div>
            """
            self.append_to_chat(error_html)

# MainInterface class with collapsible AI Assistant
class MainInterface(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Include Educational Platform")
        self.setGeometry(100, 50, 1400, 900)
        self.setMinimumSize(1200, 700)
        
        # Initialize AI Assistant
        try:
            self.ai_assistant_instance = AIAssistant.get_instance()
        except Exception as e:
            print(f"AI Assistant initialization failed: {e}")
            # Continue without AI functionality
        
        self.init_ui()
        self.setup_connections()

    def init_ui(self):
        # Main layout
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left side: Main content
        self.left_container = QWidget()
        self.left_container.setStyleSheet("background-color: #F8F9FA;")
        left_layout = QVBoxLayout(self.left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        # Navigation header
        nav_header = QFrame()
        nav_header.setFixedHeight(80)
        nav_header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                border: none;
            }
        """)
        nav_layout = QVBoxLayout(nav_header)
        nav_layout.setContentsMargins(25, 12, 25, 12)
        
        # App title
        title_label = QLabel(" Include Classroom Platform")
        title_label.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        title_label.setStyleSheet("color: white;")
        nav_layout.addWidget(title_label)
        
        # Subtitle
        subtitle_label = QLabel("Real-time transcription & communication")
        subtitle_label.setFont(QFont("Segoe UI", 12))
        subtitle_label.setStyleSheet("color: rgba(255,255,255,0.9);")
        nav_layout.addWidget(subtitle_label)
        
        left_layout.addWidget(nav_header)

        # Role selection buttons
        button_container = QFrame()
        button_container.setFixedHeight(70)
        button_container.setStyleSheet("""
            QFrame {
                background: white;
                border-bottom: 1px solid #E2E8F0;
            }
        """)
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(20, 12, 20, 12)
        button_layout.setSpacing(15)

        self.teacher_btn = self.create_role_button(" Teacher", "#4299E1")
        self.student_btn = self.create_role_button(" Deaf Student", "#48BB78") 
        self.mute_student_btn = self.create_role_button(" Mute Student", "#ED8936")
        self.ai_assistant_btn = self.create_role_button(" AI Assistant", "#9F7AEA")  # New AI Assistant button

        for btn in [self.teacher_btn, self.student_btn, self.mute_student_btn, self.ai_assistant_btn]:
            button_layout.addWidget(btn)

        button_layout.addStretch()
        left_layout.addWidget(button_container)

        # Pages container
        self.pages = QStackedWidget()
        self.pages.setStyleSheet("background: transparent;")
        
        # Initialize pages
        try:
            self.teacher_page = TeacherPage()
            self.student_page = StudentPage()
            self.mute_student_page = MuteStudentPage()
            self.ai_assistant_page = AIAssistantPage()  # Now using the speaking AI assistant page
            
            self.pages.addWidget(self.teacher_page)
            self.pages.addWidget(self.student_page)
            self.pages.addWidget(self.mute_student_page)
            self.pages.addWidget(self.ai_assistant_page)  # Add AI Assistant page
        except Exception as e:
            print(f"Error initializing pages: {e}")
            # Create fallback pages if imports fail
            self.pages.addWidget(QLabel("Teacher Page - Module not found"))
            self.pages.addWidget(QLabel("Deaf Student Page - Module not found"))
            self.pages.addWidget(QLabel("Mute Student Page - Module not found"))
            self.pages.addWidget(QLabel("AI Assistant Page - Module not found"))
        
        left_layout.addWidget(self.pages)

        # Right side: Collapsible AI Assistant
        self.ai_assistant = CollapsibleAIAssistant()
        self.ai_assistant.setMinimumWidth(50)  # Only toggle button width when collapsed
        self.ai_assistant.setMaximumWidth(500)  # Maximum width when expanded

        # Add to main layout
        main_layout.addWidget(self.left_container)
        main_layout.addWidget(self.ai_assistant)

        self.setLayout(main_layout)
        self.current_page_index = 0

    def create_role_button(self, text, color):
        """Create styled role selection buttons"""
        button = QPushButton(text)
        button.setFont(QFont("Segoe UI", 13, QFont.Weight.Medium))
        button.setMinimumHeight(45)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setStyleSheet(f"""
            QPushButton {{
                background: white;
                color: #4A5568;
                border: 2px solid #E2E8F0;
                border-radius: 10px;
                padding: 10px 20px;
            }}
            QPushButton:hover {{
                background: {color};
                color: white;
                border-color: {color};
            }}
        """)
        return button

    def setup_connections(self):
        """Setup button connections and initial state"""
        self.teacher_btn.clicked.connect(lambda: self.switch_page(0))
        self.student_btn.clicked.connect(lambda: self.switch_page(1))
        self.mute_student_btn.clicked.connect(lambda: self.switch_page(2))
        self.ai_assistant_btn.clicked.connect(lambda: self.switch_page(3))  # AI Assistant page
        
        # Set initial active button
        self.switch_page(0)

    def switch_page(self, index):
        """Switch between pages and update UI state"""
        self.pages.setCurrentIndex(index)
        self.current_page_index = index
        
        # Update button styles
        buttons = [self.teacher_btn, self.student_btn, self.mute_student_btn, self.ai_assistant_btn]
        active_colors = ["#4299E1", "#48BB78", "#ED8936", "#9F7AEA"]
        
        for i, btn in enumerate(buttons):
            if i == index:
                # Active button
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {active_colors[i]};
                        color: white;
                        border: 2px solid {active_colors[i]};
                        border-radius: 10px;
                        padding: 10px 20px;
                    }}
                """)
            else:
                # Inactive button
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: white;
                        color: #4A5568;
                        border: 2px solid #E2E8F0;
                        border-radius: 10px;
                        padding: 10px 20px;
                    }}
                    QPushButton:hover {{
                        background: {active_colors[i]};
                        color: white;
                        border-color: {active_colors[i]};
                    }}
                """)
        
        # Show/hide AI Assistant based on page
        self.update_assistant_visibility()

    def update_assistant_visibility(self):
        """Show AI Assistant toggle for student pages, hide for teacher and AI Assistant page"""
        if self.current_page_index in [1, 2]:  # Student pages
            self.show_assistant_toggle()
        else:  # Teacher page and AI Assistant page
            self.hide_assistant_toggle()

    def show_assistant_toggle(self):
        """Show the AI Assistant toggle"""
        if not self.ai_assistant.isVisible():
            self.ai_assistant.show()

    def hide_assistant_toggle(self):
        """Hide the AI Assistant toggle and collapse if expanded"""
        if self.ai_assistant.isVisible():
            # Collapse the assistant if it's expanded
            if hasattr(self.ai_assistant, 'is_expanded') and self.ai_assistant.is_expanded:
                self.ai_assistant.toggle_assistant()
            self.ai_assistant.hide()

    def resizeEvent(self, event):
        """Handle window resize for better responsiveness"""
        super().resizeEvent(event)
        
        # Adjust assistant width based on window size
        width = self.width()
        if width < 1300:
            self.ai_assistant.setMaximumWidth(400)
        else:
            self.ai_assistant.setMaximumWidth(450)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set application-wide font and style
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet("""
        QWidget {
            font-family: "Segoe UI";
        }
    """)
    
    try:
        window = MainInterface()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"Application error: {e}")
        sys.exit(1)