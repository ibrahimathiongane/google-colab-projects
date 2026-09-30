from datetime import date as date_cls
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

IsoDate = Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")]


class CheckInIn(BaseModel):
    habit_id: int = Field(gt=0)
    date: IsoDate
    completed: bool = True
    automaticity: int | None = Field(default=None, ge=1, le=10)
    note: Annotated[str, Field(max_length=500)] = ""

    @field_validator("date")
    @classmethod
    def real_calendar_date(cls, value: str) -> str:
        try:
            date_cls.fromisoformat(value)
        except ValueError:
            raise ValueError("must be a valid date (YYYY-MM-DD)") from None
        return value

    @field_validator("note")
    @classmethod
    def strip_note(cls, value: str) -> str:
        return value.strip()
