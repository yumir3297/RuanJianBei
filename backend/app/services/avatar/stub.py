from __future__ import annotations

from app.services.avatar.base import AvatarPayload, BaseAvatarService


class StubAvatarService(BaseAvatarService):
    async def drive(self, text: str) -> AvatarPayload:
        return AvatarPayload(viseme_text=text, emotion="neutral")

