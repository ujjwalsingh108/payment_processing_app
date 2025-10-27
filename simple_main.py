from fastapi import FastAPI, HTTPException, BackgroundTasks
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
async def receive_webhook(webhook: WebhookRequest, background_tasks: BackgroundTasks):
    # Check if transaction already exists (idempotency)
    if webhook.transaction_id in transactions:
        return WebhookResponse(
            message="Transaction already received",
            transaction_id=webhook.transaction_id
        )

    # Store transaction as PROCESSING
    transactions[webhook.transaction_id] = {
        "transaction_id": webhook.transaction_id,
        "source_account": webhook.source_account,
        "destination_account": webhook.destination_account,
        "amount": webhook.amount,
        "currency": webhook.currency,
        "status": "PROCESSING",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "processed_at": None
    }

    # Schedule background processing
    background_tasks.add_task(process_transaction, webhook.transaction_id)

    return WebhookResponse(
        message="Transaction accepted for processing",
        transaction_id=webhook.transaction_id
    )

def process_transaction(transaction_id: str):
    import time
    time.sleep(30)
    if transaction_id in transactions:
        transactions[transaction_id]["status"] = "PROCESSED"
        transactions[transaction_id]["processed_at"] = datetime.utcnow().isoformat() + "Z"

@app.get("/v1/transactions/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(transaction_id: str):
    if transaction_id not in transactions:
        raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")
    
    return TransactionResponse(**transactions[transaction_id])