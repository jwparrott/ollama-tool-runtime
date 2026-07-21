from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import scrolledtext

from agent_runtime.engine import ToolChatSession
from agent_runtime.voice import SpeechToText, TextToSpeech, VoiceFeatureError


class ChatWindow:
    def __init__(
        self,
        session: ToolChatSession,
        model: str,
        max_steps: int,
        enable_voice: bool = True,
        speak_replies_default: bool = False,
    ) -> None:
        self._session = session
        self._max_steps = max_steps
        self._reply_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self._busy = False
        self._listening = False
        self._speak_replies: tk.BooleanVar
        self._tts: TextToSpeech | None = None
        self._stt: SpeechToText | None = None

        self.root = tk.Tk()
        self.root.title(f"Ollama Tool Runtime Chat - {model}")
        self.root.geometry("900x600")
        self._speak_replies = tk.BooleanVar(value=speak_replies_default)

        self.chat_box = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, state=tk.DISABLED)
        self.chat_box.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 5))

        self.status_var = tk.StringVar(value="Ready")
        status = tk.Label(self.root, textvariable=self.status_var, anchor="w")
        status.pack(fill=tk.X, padx=10, pady=(0, 5))

        input_frame = tk.Frame(self.root)
        input_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.prompt_entry = tk.Entry(input_frame)
        self.prompt_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.prompt_entry.bind("<Return>", self._on_send)

        self.send_button = tk.Button(input_frame, text="Send", command=self._send_prompt)
        self.send_button.pack(side=tk.LEFT, padx=(8, 0))

        self.listen_button = tk.Button(input_frame, text="Listen", command=self._listen_prompt)
        self.listen_button.pack(side=tk.LEFT, padx=(8, 0))

        self.speak_checkbox = tk.Checkbutton(input_frame, text="Speak replies", variable=self._speak_replies)
        self.speak_checkbox.pack(side=tk.LEFT, padx=(8, 0))

        if enable_voice:
            self._initialize_voice()
        else:
            self.listen_button.configure(state=tk.DISABLED)
            self.speak_checkbox.configure(state=tk.DISABLED)

        self._append_message("system", "Interactive session started.")
        self.root.after(100, self._poll_replies)

    def run(self) -> None:
        self.root.mainloop()

    def _append_message(self, role: str, content: str) -> None:
        self.chat_box.configure(state=tk.NORMAL)
        self.chat_box.insert(tk.END, f"{role}> {content}\n\n")
        self.chat_box.see(tk.END)
        self.chat_box.configure(state=tk.DISABLED)

    def _on_send(self, _event: tk.Event) -> None:
        self._send_prompt()

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        state = tk.DISABLED if (busy or self._listening) else tk.NORMAL
        self.prompt_entry.configure(state=state)
        self.send_button.configure(state=state)
        if self._listening:
            self.listen_button.configure(state=tk.DISABLED)
            self.status_var.set("Listening...")
        else:
            self.listen_button.configure(state=tk.NORMAL if not busy else tk.DISABLED)
            self.status_var.set("Thinking..." if busy else "Ready")

    def _send_prompt(self) -> None:
        if self._busy or self._listening:
            return
        prompt = self.prompt_entry.get().strip()
        if not prompt:
            return

        self.prompt_entry.delete(0, tk.END)
        self._begin_model_request(prompt=prompt, speaker="you")

    def _begin_model_request(self, prompt: str, speaker: str) -> None:
        self._append_message(speaker, prompt)
        self._set_busy(True)
        worker = threading.Thread(target=self._ask_model, args=(prompt,), daemon=True)
        worker.start()

    def _ask_model(self, prompt: str) -> None:
        try:
            reply = self._session.ask(prompt, max_steps=self._max_steps)
            self._reply_queue.put(("assistant", reply))
        except Exception as exc:
            self._reply_queue.put(("error", str(exc)))

    def _initialize_voice(self) -> None:
        try:
            self._tts = TextToSpeech()
            self._stt = SpeechToText()
        except VoiceFeatureError as exc:
            self._speak_replies.set(False)
            self.listen_button.configure(state=tk.DISABLED)
            self._reply_queue.put(("error", str(exc)))

    def _listen_prompt(self) -> None:
        if self._busy or self._listening:
            return
        if self._stt is None:
            self._reply_queue.put(("error", "Speech-to-text is unavailable in this environment."))
            return
        self._listening = True
        self._set_busy(False)
        worker = threading.Thread(target=self._capture_voice_prompt, daemon=True)
        worker.start()

    def _capture_voice_prompt(self) -> None:
        try:
            assert self._stt is not None
            spoken_text = self._stt.listen_once()
            self._reply_queue.put(("voice_prompt", spoken_text))
        except VoiceFeatureError as exc:
            self._reply_queue.put(("error", str(exc)))
        finally:
            self._reply_queue.put(("listening_done", ""))

    def _speak_async(self, text: str) -> None:
        if self._tts is None:
            return
        worker = threading.Thread(target=self._speak_reply, args=(text,), daemon=True)
        worker.start()

    def _speak_reply(self, text: str) -> None:
        try:
            assert self._tts is not None
            self._tts.speak(text)
        except VoiceFeatureError as exc:
            self._reply_queue.put(("error", str(exc)))

    def _poll_replies(self) -> None:
        try:
            while True:
                role, content = self._reply_queue.get_nowait()
                if role == "assistant":
                    self._append_message(role, content)
                    self._set_busy(False)
                    if self._speak_replies.get() and self._tts is not None:
                        self._speak_async(content)
                    continue
                if role == "voice_prompt":
                    self._begin_model_request(prompt=content, speaker="you(voice)")
                    continue
                if role == "listening_done":
                    self._listening = False
                    self._set_busy(self._busy)
                    continue
                self._append_message(role, content)
                self._set_busy(False)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._poll_replies)


def run_chat_gui(
    session: ToolChatSession,
    model: str,
    max_steps: int,
    enable_voice: bool = True,
    speak_replies_default: bool = False,
) -> None:
    window = ChatWindow(
        session=session,
        model=model,
        max_steps=max_steps,
        enable_voice=enable_voice,
        speak_replies_default=speak_replies_default,
    )
    window.run()
