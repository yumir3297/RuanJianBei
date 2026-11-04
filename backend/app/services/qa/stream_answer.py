class StreamAnswerBuffer:
    """Keep the full LLM answer and extract speakable HTTP TTS sentences."""

    def __init__(self) -> None:
        self.full_answer = ""
        self.sentence_buffer = ""

    def append(self, token: str) -> None:
        self.full_answer += token
        self.sentence_buffer += token

    def take_speakable_sentences(self) -> list[str]:
        sentences: list[str] = []
        start = 0
        for index, char in enumerate(self.sentence_buffer):
            if char in "。！？!?；;\n" or (char in "，、," and index - start + 1 >= 8):
                sentence = self.sentence_buffer[start:index + 1].strip()
                if sentence:
                    sentences.append(sentence)
                start = index + 1
        self.sentence_buffer = self.sentence_buffer[start:]
        return sentences
