from typing import Literal

from pydantic import BaseModel, Field


class PushKeys(BaseModel):
    """Web Push encryption keys from PushSubscription.toJSON().keys."""

    p256dh: str = Field(min_length=1, max_length=128)
    auth: str = Field(min_length=1, max_length=64)


class SubscribeIn(BaseModel):
    endpoint: str = Field(min_length=1, max_length=512)
    keys: PushKeys
    # Minutes east of UTC (-720..+840) for THIS device.
    tz_offset: int = Field(ge=-720, le=840)
    lang: Literal["en", "fr"] = "en"


class UnsubscribeIn(BaseModel):
    endpoint: str = Field(min_length=1, max_length=512)
