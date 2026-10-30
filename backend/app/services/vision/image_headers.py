"""Bounded image container and dimension checks before calling vision providers.

This validates container structure and dimensions, not full pixel decoding.
"""
from __future__ import annotations

import struct
import zlib


class InvalidImage(ValueError):
    pass


def image_dimensions(content: bytes, mime: str) -> tuple[int, int]:
    if mime == "image/png":
        return _png_dimensions(content)
    if mime == "image/jpeg":
        return _jpeg_dimensions(content)
    if mime == "image/webp":
        return _webp_dimensions(content)
    raise InvalidImage("unsupported format")


def detect_image_mime(content: bytes) -> str | None:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "image/webp"
    return None


def _png_dimensions(data: bytes) -> tuple[int, int]:
    pos = 8
    dimensions = None
    has_data = False
    while pos + 12 <= len(data):
        length = int.from_bytes(data[pos:pos + 4], "big")
        end = pos + 12 + length
        if end > len(data):
            raise InvalidImage("truncated PNG")
        kind = data[pos + 4:pos + 8]
        payload = data[pos + 8:pos + 8 + length]
        expected_crc = int.from_bytes(data[pos + 8 + length:end], "big")
        if zlib.crc32(kind + payload) & 0xFFFFFFFF != expected_crc:
            raise InvalidImage("invalid PNG checksum")
        if pos == 8:
            if kind != b"IHDR" or length != 13:
                raise InvalidImage("missing PNG header")
            dimensions = struct.unpack(">II", payload[:8])
        elif kind == b"IHDR":
            raise InvalidImage("duplicate PNG header")
        elif kind == b"IDAT":
            has_data = True
        elif kind == b"IEND":
            if length != 0 or not has_data or end != len(data):
                raise InvalidImage("invalid PNG end")
            return dimensions
        pos = end
    raise InvalidImage("incomplete PNG")


def _jpeg_dimensions(data: bytes) -> tuple[int, int]:
    pos = 2
    sof = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
    dimensions = None
    while pos + 3 < len(data):
        if data[pos] != 0xFF:
            raise InvalidImage("invalid JPEG marker")
        while pos < len(data) and data[pos] == 0xFF:
            pos += 1
        if pos >= len(data):
            break
        marker = data[pos]
        pos += 1
        if marker == 0xDA:
            if dimensions is None or pos + 2 > len(data):
                break
            scan_header_length = int.from_bytes(data[pos:pos + 2], "big")
            scan_start = pos + scan_header_length
            if scan_header_length < 2 or scan_start >= len(data) or data.find(b"\xff\xd9", scan_start) < 0:
                raise InvalidImage("incomplete JPEG scan")
            return dimensions
        if marker in {0x01, 0xD8, *range(0xD0, 0xD8)}:
            continue
        if pos + 2 > len(data):
            break
        length = int.from_bytes(data[pos:pos + 2], "big")
        if length < 2 or pos + length > len(data):
            raise InvalidImage("invalid JPEG segment")
        if marker in sof:
            if length < 8:
                raise InvalidImage("invalid JPEG frame")
            height, width = struct.unpack(">HH", data[pos + 3:pos + 7])
            frame_dimensions = (width, height)
            if dimensions is not None and dimensions != frame_dimensions:
                raise InvalidImage("conflicting JPEG frame dimensions")
            dimensions = frame_dimensions
        pos += length
    raise InvalidImage("missing JPEG frame")


def _webp_dimensions(data: bytes) -> tuple[int, int]:
    if len(data) < 20 or int.from_bytes(data[4:8], "little") + 8 != len(data):
        raise InvalidImage("incomplete WebP")
    pos = 12
    dimensions = None
    frame_dimensions = None
    has_image = False
    while pos + 8 <= len(data):
        kind = data[pos:pos + 4]
        size = int.from_bytes(data[pos + 4:pos + 8], "little")
        end = pos + 8 + size
        if end > len(data) or end + (size & 1) > len(data):
            raise InvalidImage("truncated WebP chunk")
        chunk = data[pos + 8:end]
        if kind == b"VP8X" and len(chunk) >= 10:
            if chunk[0] & 0x02:
                raise InvalidImage("animated WebP is not supported")
            dimensions = (1 + int.from_bytes(chunk[4:7], "little"), 1 + int.from_bytes(chunk[7:10], "little"))
        elif kind == b"VP8 " and len(chunk) >= 10 and chunk[3:6] == b"\x9d\x01\x2a":
            if has_image:
                raise InvalidImage("multiple WebP image frames are not supported")
            has_image = True
            frame_dimensions = (int.from_bytes(chunk[6:8], "little") & 0x3FFF, int.from_bytes(chunk[8:10], "little") & 0x3FFF)
        elif kind == b"VP8L" and len(chunk) >= 5 and chunk[0] == 0x2F:
            if has_image:
                raise InvalidImage("multiple WebP image frames are not supported")
            has_image = True
            bits = int.from_bytes(chunk[1:5], "little")
            frame_dimensions = ((bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1)
        elif kind == b"ANMF":
            raise InvalidImage("animated WebP is not supported")
        pos = end + (size & 1)
    if dimensions is None:
        dimensions = frame_dimensions
    if pos != len(data) or not dimensions or not has_image or dimensions != frame_dimensions:
        raise InvalidImage("missing WebP image")
    return dimensions
