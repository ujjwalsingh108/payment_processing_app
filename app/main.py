from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import logging

from app.database import get_db, init_db
from app.models import Transaction, TransactionStatus
from app.schemas import (
    WebhookRequest,
    WebhookResponse,
    HealthCheckResponse,
    TransactionResponse
)
from app.tasks import process_transaction

# setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# create the FastAPI app
app = FastAPI(
    title="Payment Webhook Processing Service",
    description="Service to receive and process payment transaction webhooks",
    version="1.0.0"
)


@app.on_event("startup")
async def startup_event():
    # initialize the database tables when app starts
    init_db()
    logger.info("Database initialized")


@app.get("/", response_model=HealthCheckResponse)
async def health_check():
    # simple health check - just returns current time and status
    return HealthCheckResponse(
        status="HEALTHY",
        current_time=datetime.utcnow().isoformat() + "Z"
    )


@app.post(
    "/v1/webhooks/transactions",
    response_model=WebhookResponse,
    status_code=status.HTTP_202_ACCEPTED
)
async def receive_webhook(
    webhook: WebhookRequest,
    db: Session = Depends(get_db)
):
    """
    Main webhook endpoint - receives transaction webhooks and queues them for processing.
    Returns 202 immediately to meet the <500ms requirement.
    """
    try:
        # first check if we've already seen this transaction (idempotency check)
        existing_transaction = db.query(Transaction).filter(
            Transaction.transaction_id == webhook.transaction_id
        ).first()
        
        if existing_transaction:
            # already got this one, just return success
            logger.info(f"Duplicate webhook received for transaction: {webhook.transaction_id}")
            return WebhookResponse(
                message="Transaction already received",
                transaction_id=webhook.transaction_id
            )
        
        # create new transaction in the database
        new_transaction = Transaction(
            transaction_id=webhook.transaction_id,
            source_account=webhook.source_account,
            destination_account=webhook.destination_account,
            amount=webhook.amount,
            currency=webhook.currency,
            status=TransactionStatus.PROCESSING
        )
        
        db.add(new_transaction)
        db.commit()
        db.refresh(new_transaction)
        
        # queue it up for background processing with celery
        process_transaction.delay(webhook.transaction_id)
        
        logger.info(f"Webhook accepted for transaction: {webhook.transaction_id}")
        
        return WebhookResponse(
            message="Transaction accepted for processing",
            transaction_id=webhook.transaction_id
        )
        
    except IntegrityError:
        # race condition - another request inserted the same transaction between our check and insert
        # this is fine, just rollback and return success
        db.rollback()
        logger.info(f"Race condition handled for transaction: {webhook.transaction_id}")
        return WebhookResponse(
            message="Transaction already received",
            transaction_id=webhook.transaction_id
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.get(
    "/v1/transactions/{transaction_id}",
    response_model=TransactionResponse
)
async def get_transaction(
    transaction_id: str,
    db: Session = Depends(get_db)
):
    """Get transaction status by ID - useful for testing and monitoring"""
    transaction = db.query(Transaction).filter(
        Transaction.transaction_id == transaction_id
    ).first()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {transaction_id} not found"
        )
    
    return transaction
