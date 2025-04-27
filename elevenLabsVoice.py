import os
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs import play
import time
import speech_recognition as sr

load_dotenv()
client = ElevenLabs(
    api_key=os.getenv("ELEVENLABS_API_KEY", "Place Key Here")
)

def playVoice(textInput):
    audio = client.text_to_speech.convert(
        text=textInput,
        voice_id="bMxLr8fP6hzNRRi9nJxU",
        model_id="eleven_flash_v2_5",
        output_format="mp3_44100_128"
        
    )

    play(audio)

    return 0

def recognize_speech_from_mic():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    with mic as source:
        print("Listening...")
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)

    try:
        text = recognizer.recognize_google(audio)
        print("You said:", text)
        return text
    except sr.UnknownValueError:
        print("Could not understand audio")
        return ""
    except sr.RequestError as e:
        print(f"API error: {e}")
        return ""
