from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from app.models import TransactionStatus


class WebhookRequest(BaseModel):
    transaction_id: str = Field(..., description="Unique transaction identifier")
    source_account: str = Field(..., description="Source account identifier")
    destination_account: str = Field(..., description="Destination account identifier")
    amount: float = Field(..., gt=0, description="Transaction amount")
    currency: str = Field(..., description="Currency code (e.g., INR, USD)")

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "txn_abc123def456",
                "source_account": "acc_user_789",
                "destination_account": "acc_merchant_456",
                "amount": 1500,
                "currency": "INR"
            }
        }


class WebhookResponse(BaseModel):
    message: str
    transaction_id: str


class HealthCheckResponse(BaseModel):
    status: str
    current_time: str


class TransactionResponse(BaseModel):
    transaction_id: str
    source_account: str
    destination_account: str
    amount: float
    currency: str
    status: TransactionStatus
    created_at: datetime
    processed_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # for SQLAlchemy compatibility
