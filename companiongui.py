import sys
import os
import random
import threading
import re
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QTextEdit, QLineEdit, QVBoxLayout, QPushButton
from PyQt5.QtGui import QPixmap, QMovie, QColor
from PyQt5.QtCore import Qt, QPoint, QEvent, QTimer, QThread, pyqtSignal, QObject
from Cerebras import generate_response
from elevenLabsVoice import playVoice, recognize_speech_from_mic
from PyQt5.QtMultimedia import QSoundEffect
from PyQt5.QtCore import QUrl


#from playsound import playsound

class AIWorker(QObject):
    finished = pyqtSignal(str, str)  # response, emotion

    def __init__(self, inputtxt, ai_func):
        super().__init__()
        self.inputtxt = inputtxt
        self.ai_func = ai_func

    def run(self):
        response, emotion = self.ai_func(self.inputtxt)
        self.finished.emit(response, emotion)

class DesktopCompanion(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
        self.resize(300, 400)

        self.offset = QPoint(0, 0)
        self.chat_visible = False
        self.movie = None

        self.coolString = ""
        self.lineBean = 0

        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.emotion_dirs = {
            "neutral": "assets/neutral",
            "happy": "assets/happy",
            "sad": "assets/sad",
            "angry": "assets/angry",
            "thinking": "assets/thinking",
            "confused": "assets/confused"
        }

        # Character image
        self.label = QLabel(self)
        self.label.setGeometry(0, 0, 300, 400)
        self.label.setStyleSheet("background: transparent;")
        self.label.mouseDoubleClickEvent = self.toggle_chat  # 👈 We'll use double-click now

        # Chat box container
        self.text_edit = QTextEdit(self)
        self.text_edit.setGeometry(0, -120, 300, 100)  # Position ABOVE character
        self.text_edit.setReadOnly(True)
        self.text_edit.hide()

        self.input_line = QLineEdit(self)
        self.input_line.setGeometry(0, -20, 240, 20)  # Just above the character
        self.input_line.returnPressed.connect(self.on_enter)
        self.input_line.hide()

        self.micButton = QLabel(self)
        self.micButton.setGeometry(250, -20, 32, 32)
        self.micButton.setPixmap(QPixmap("assets/micIconS.webp"))
        self.micButton.mousePressEvent = self.getMicInput
        self.micButton.hide()

        self.exit_sound = QSoundEffect()
        self.exit_sound.setSource(QUrl.fromLocalFile(os.path.join(self.base_dir, "assets/exit_sound.wav")))
        self.exit_sound.setVolume(0.25)  # volume between 0.0 and 1.0


        # Styles
        self.text_edit.setStyleSheet("""
            background-color: rgba(30, 30, 30, 200);
            color: white;
            border: 1px solid #555;
            padding: 4px;
        """)

        self.input_line.setStyleSheet("""
            background-color: rgba(30, 30, 30, 220);
            color: white;
            border: 1px solid #555;
            padding: 2px;
        """)


        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.layout.addWidget(self.text_edit)
        self.layout.addWidget(self.input_line)
        self.layout.addWidget(self.micButton)
        self.layout.addWidget(self.label)

        self.setLayout(self.layout)

        self.current_image_path = self.get_random_image("neutral")
        self.load_character_image()

        self.installEventFilter(self)

    def eventFilter(self, source, event):
        if event.type() == QEvent.KeyPress and event.key() == Qt.Key_Escape:
            self.exit_sound.play()
            QTimer.singleShot(1000, QApplication.quit)  # 500ms delay to let sound finish
            return True
        return super().eventFilter(source, event)


    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.offset = event.pos()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.offset)

    def toggle_chat(self, event):
        self.chat_visible = not self.chat_visible
        self.text_edit.setVisible(self.chat_visible)
        self.input_line.setVisible(self.chat_visible)
        self.micButton.setVisible(self.chat_visible)
        if self.chat_visible:
            QTimer.singleShot(100, self.input_line.setFocus)

    def get_random_image(self, emotion):
        folder = os.path.join(self.base_dir, self.emotion_dirs.get(emotion, self.emotion_dirs["neutral"]))
        if not os.path.exists(folder):
            print(f"Missing folder: {folder}")
            return ""
        files = [f for f in os.listdir(folder) if f.endswith(".png") or f.endswith(".gif")]
        if not files:
            return ""
        return os.path.join(folder, random.choice(files))

    def load_character_image(self):
        if self.movie:
            self.movie.stop()
            self.movie = None

        if not self.current_image_path:
            return

        if self.current_image_path.endswith(".gif"):
            self.movie = QMovie(self.current_image_path)
            self.label.setMovie(self.movie)
            self.movie.start()
        else:
            pixmap = QPixmap(self.current_image_path)
            mask = pixmap.createMaskFromColor(QColor("#00FF22"), Qt.MaskOutColor)
            pixmap.setMask(mask)
            self.label.setPixmap(pixmap)

    def on_enter(self):
        user_input = self.input_line.text().strip()
        if not user_input:
            return
        self.input_line.clear()
        self.text_edit.append(f"You: {user_input}")

        self.thread = QThread()
        self.worker = AIWorker(user_input, self.aiOutput)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.handle_ai_result)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def handle_ai_result(self, response, emotion):
        self.text_edit.append(f"AI: {response}")
        self.update_emotion(emotion)
        
        # Start a background thread to play voice
        threading.Thread(target=self.voice, args=(response,), daemon=True).start()

    def voice(self, response):
        playVoice(response)


    def update_emotion(self, emotion):
        self.current_image_path = self.get_random_image(emotion)
        self.load_character_image()

    def aiOutput(self, inputtxt):
        self.coolString += inputtxt + "\n"
        if self.lineBean >= 20:
            self.coolString = self.coolString[self.coolString.index("\n") + 1:]
            self.coolString = self.coolString[self.coolString.index("\n") + 1:]
        else:
            self.lineBean += 1
        inputWHistory = self.coolString

        aiText = generate_response(inputWHistory) + "\n"
        emotion = aiText[aiText.find("[") + 1:aiText.find("]")]
        aiText = aiText[:aiText.find("[" + emotion + "]") - 1]
        self.coolString += aiText

        return aiText, emotion

    def getMicInput(self, event):
        user_input = recognize_speech_from_mic()
        if user_input:
            self.input_line.setText(user_input)
            #self.text_edit.append(f"You: {user_input}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    companion = DesktopCompanion()
    companion.show()
    sys.exit(app.exec_())
