from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class AccountCreate(BaseModel):
    owner_name: str = Field(..., min_length=1, max_length=255, description="Account owner's name")
    initial_balance: float = Field(default=0.0, ge=0, description="Initial account balance")

    @field_validator("owner_name")
    @classmethod
    def validate_owner_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Owner name cannot be empty or whitespace only")
        return v


class AccountResponse(BaseModel):
    id: int
    owner_name: str
    balance: float
    created_at: datetime

    model_config = {"from_attributes": True}


class BalanceResponse(BaseModel):
    account_id: int
    owner_name: str
    balance: float


class DepositRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Amount to deposit (must be positive)")


class WithdrawRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Amount to withdraw (must be positive)")


class TransactionResponse(BaseModel):
    id: int
    account_id: int
    type: str
    amount: float
    timestamp: datetime

    model_config = {"from_attributes": True}


class TransactionListResponse(BaseModel):
    account_id: int
    transactions: List[TransactionResponse]
    total_count: int


class MessageResponse(BaseModel):
    message: str
    account_id: int
    new_balance: float


class ErrorResponse(BaseModel):
    detail: str


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
