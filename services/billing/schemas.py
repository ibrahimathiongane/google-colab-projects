from typing import Literal

from pydantic import BaseModel


class CheckoutIn(BaseModel):
    plan: Literal["pro", "lifetime"]
