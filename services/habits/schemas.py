import re
from typing import Annotated

from pydantic import BaseModel, Field, field_validator, model_validator

TIME_PATTERN = re.compile(r"^([01][0-9]|2[0-3]):[0-5][0-9]$")

ShortText = Annotated[str, Field(min_length=1, max_length=255)]


class CreateHabitIn(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=120)]
    anchor: ShortText
    tiny_behavior: ShortText
    celebration: ShortText
    cue_time: Annotated[str, Field(max_length=5)] = ""

    @field_validator("cue_time")
    @classmethod
    def cue_time_is_hhmm_or_empty(cls, value: str) -> str:
        if value and not TIME_PATTERN.match(value):
            raise ValueError("cue_time must be HH:MM (24h) or empty")
        return value

    @field_validator("anchor", "tiny_behavior", "celebration", "name")
    @classmethod
    def strip_blanks(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped


class HabitOut(BaseModel):
    id: int
    name: str
    anchor: str
    tiny_behavior: str
    celebration: str
    if_then: str
    cue_time: str
    created_at: str

    model_config = {"from_attributes": True}


class UpdateHabitIn(BaseModel):
    """Partial update: only the keys present in the payload are applied.

    Sending an explicit ``null`` for a required text field is rejected;
    to clear ``cue_time`` send an empty string.
    """

    name: Annotated[str | None, Field(min_length=1, max_length=120)] = None
    anchor: Annotated[str | None, Field(min_length=1, max_length=255)] = None
    tiny_behavior: Annotated[
        str | None, Field(min_length=1, max_length=255)
    ] = None
    celebration: Annotated[str | None, Field(min_length=1, max_length=255)] = (
        None
    )
    cue_time: Annotated[str | None, Field(max_length=5)] = None

    @field_validator("name", "anchor", "tiny_behavior", "celebration")
    @classmethod
    def strip_blanks(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("must not be blank")
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped

    @field_validator("cue_time")
    @classmethod
    def cue_time_is_hhmm_or_empty(cls, value: str | None) -> str | None:
        if value is None:
            return ""
        if value and not TIME_PATTERN.match(value):
            raise ValueError("cue_time must be HH:MM (24h) or empty")
        return value

    @model_validator(mode="after")
    def at_least_one_field(self) -> "UpdateHabitIn":
        if not self.model_fields_set:
            raise ValueError("nothing to update")
        return self
