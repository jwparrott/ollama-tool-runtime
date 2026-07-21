from __future__ import annotations

import threading


class VoiceFeatureError(RuntimeError):
    """Raised when local speech features are unavailable or fail."""


class TextToSpeech:
    def __init__(self) -> None:
        try:
            import pyttsx3
        except ImportError as exc:
            raise VoiceFeatureError("Text-to-speech requires 'pyttsx3'. Install with: pip install pyttsx3") from exc
        self._engine = pyttsx3.init()
        self._lock = threading.Lock()

    def speak(self, text: str) -> None:
        if not text.strip():
            return
        with self._lock:
            self._engine.say(text)
            self._engine.runAndWait()


class SpeechToText:
    def __init__(self, timeout_seconds: int = 8, phrase_time_limit_seconds: int = 20, calibrate_seconds: float = 0.5) -> None:
        try:
            import speech_recognition as sr
        except ImportError as exc:
            raise VoiceFeatureError(
                "Speech-to-text requires 'SpeechRecognition' and microphone backend. "
                "Install with: pip install SpeechRecognition pyaudio"
            ) from exc
        self._sr = sr
        self._timeout = timeout_seconds
        self._phrase_time_limit = phrase_time_limit_seconds
        self._calibrate_seconds = calibrate_seconds
        self._recognizer = sr.Recognizer()

    def listen_once(self) -> str:
        try:
            with self._sr.Microphone() as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=self._calibrate_seconds)
                audio = self._recognizer.listen(
                    source,
                    timeout=self._timeout,
                    phrase_time_limit=self._phrase_time_limit,
                )
        except OSError as exc:
            raise VoiceFeatureError(f"Microphone unavailable: {exc}") from exc
        except self._sr.WaitTimeoutError as exc:
            raise VoiceFeatureError("No speech detected before timeout.") from exc

        try:
            return self._recognizer.recognize_google(audio)
        except self._sr.UnknownValueError as exc:
            raise VoiceFeatureError("Could not understand the spoken audio.") from exc
        except self._sr.RequestError as exc:
            raise VoiceFeatureError(f"Speech recognition service error: {exc}") from exc

