from fastapi import HTTPException, Request, status


async def read_bounded_body(request: Request, max_bytes: int) -> bytes:
    """Read incrementally and reject before buffering more than the allowed body."""
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"上传内容过大（最大 {max_bytes} 字节）。",
            )
        body.extend(chunk)
    return bytes(body)
