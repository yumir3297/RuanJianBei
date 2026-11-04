class StreamingTTSBuffer:
    """Buffer generated text until the existing streaming TTS phrase boundary."""

    def __init__(self) -> None:
        self._text = ""

    @property
    def text(self) -> str:
        return self._text

    def append(self, text: str) -> None:
        self._text += text

    def ready(self) -> bool:
        if not self._text:
            return False
        if self._text[-1] in "。！？!?；;\n":
            return True
        if self._text[-1] in "，、," and len(self._text) >= 8:
            return True
        return len(self._text) >= 16

    def take_ready(self) -> str | None:
        if not self.ready():
            return None
        return self._take()

    def drain(self) -> str | None:
        if not self._text:
            return None
        return self._take()

    def _take(self) -> str:
        text, self._text = self._text, ""
        return text
