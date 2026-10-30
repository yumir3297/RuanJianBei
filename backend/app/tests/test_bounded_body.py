import asyncio

import pytest
from fastapi import HTTPException

from app.api.bounded_body import read_bounded_body


class ChunkedRequest:
    def __init__(self, chunks):
        self.chunks = chunks
        self.consumed = 0

    async def stream(self):
        for chunk in self.chunks:
            self.consumed += 1
            yield chunk


def test_body_limit_stops_reading_when_stream_exceeds_limit():
    request = ChunkedRequest([b"1234", b"5678", b"must-not-be-read"])
    with pytest.raises(HTTPException) as exc:
        asyncio.run(read_bounded_body(request, 7))
    assert exc.value.status_code == 413
    assert request.consumed == 2


def test_body_accepts_chunked_data_at_exact_limit():
    request = ChunkedRequest([b"123", b"4567"])
    assert asyncio.run(read_bounded_body(request, 7)) == b"1234567"
