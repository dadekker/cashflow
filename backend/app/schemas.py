from pydantic import BaseModel, Field
from typing import Literal

class AnchorIn(BaseModel):
    date: str
    amount: float
    note: str | None = None
class AnchorOut(AnchorIn):
    id: int
    class Config: from_attributes = True

class CashflowIn(BaseModel):
    label: str
    amount: float = Field(gt=0)
    direction: Literal['income','expense']
    kind: Literal['one_off','recurring']
    frequency: Literal['weekly','fortnightly','monthly','quarterly','annually'] | None = None
    start_date: str
    end_type: Literal['never','end_date','occurrences'] = 'never'
    end_date: str | None = None
    end_occurrences: int | None = None
    active: bool = True
class CashflowOut(CashflowIn):
    id: int
    class Config: from_attributes = True

class HoldingIn(BaseModel):
    ticker: str
    shares: float = Field(gt=0)
    cost_per_share: float = Field(ge=0)
    currency: Literal['AUD','USD','EUR']
    opened_date: str | None = None
class HoldingOut(HoldingIn):
    id: int
    class Config: from_attributes = True

class OverwriteIn(BaseModel):
    amount: float
    note: str | None = "Overwrite balance as of today"

class CredentialNameIn(BaseModel):
    name: str | None = None
