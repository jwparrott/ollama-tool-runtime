# GUI and Voice Features

GUI implementation: [agent_runtime/gui.py](../agent_runtime/gui.py)
Voice implementation: [agent_runtime/voice.py](../agent_runtime/voice.py)

## GUI behavior

The GUI provides:

- scrollable chat transcript
- text input + send
- optional listen (speech-to-text)
- optional speak replies (text-to-speech)
- background worker threads for responsiveness

Start it:

```powershell
python main.py gui --model llama3.1
```

Disable voice explicitly:

```powershell
python main.py gui --model llama3.1 --no-voice
```

## Speech-to-text (STT)

Class: `SpeechToText`

- calibrates ambient noise briefly
- captures a single utterance
- converts speech to text (Google recognizer backend via `SpeechRecognition`)

Errors are surfaced as `VoiceFeatureError` (missing dependency, no mic, timeout, recognition service failures).

## Text-to-speech (TTS)

Class: `TextToSpeech`

- uses `pyttsx3`
- serializes speech playback with a lock

## Dependencies

```powershell
pip install pyttsx3 SpeechRecognition pyaudio
```

If voice dependencies are unavailable, GUI still works for text chat.

