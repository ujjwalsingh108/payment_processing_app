from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import json
import os

# Simple in-memory storage (in production, use a database)
transactions = {}

app = FastAPI(
    title="Payment Webhook Processing Service",
    description="Service to receive and process payment transaction webhooks",
    version="1.0.0"
)

class WebhookRequest(BaseModel):
    transaction_id: str
    source_account: str
    destination_account: str
    amount: float
    currency: str

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
    status: str
    created_at: str
    processed_at: Optional[str] = None

@app.get("/", response_model=HealthCheckResponse)
async def health_check():
    return HealthCheckResponse(
        status="HEALTHY",
        current_time=datetime.utcnow().isoformat() + "Z"
    )

@app.post("/v1/webhooks/transactions", response_model=WebhookResponse, status_code=202)
async def receive_webhook(webhook: WebhookRequest):
    # Check if transaction already exists (idempotency)
    if webhook.transaction_id in transactions:
        return WebhookResponse(
            message="Transaction already received",
            transaction_id=webhook.transaction_id
        )
    
    # Store transaction (in memory for demo)
    transactions[webhook.transaction_id] = {
        "transaction_id": webhook.transaction_id,
        "source_account": webhook.source_account,
        "destination_account": webhook.destination_account,
        "amount": webhook.amount,
        "currency": webhook.currency,
        "status": "PROCESSED",  # For demo, mark as processed immediately
        "created_at": datetime.utcnow().isoformat() + "Z",
        "processed_at": datetime.utcnow().isoformat() + "Z"
    }
    
    return WebhookResponse(
        message="Transaction accepted for processing",
        transaction_id=webhook.transaction_id
    )

@app.get("/v1/transactions/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(transaction_id: str):
    if transaction_id not in transactions:
        raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")
    
    return TransactionResponse(**transactions[transaction_id])