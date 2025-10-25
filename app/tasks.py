import time
from datetime import datetime
from sqlalchemy.orm import Session
from app.celery_app import celery_app
from app.database import SessionLocal
from app.models import Transaction, TransactionStatus
import logging

logger = logging.getLogger(__name__)


@celery_app.task(name="process_transaction", bind=True, max_retries=3)
def process_transaction(self, transaction_id: str):
    """
    Background task to process a transaction.
    Includes a 30 second sleep to simulate external API calls.
    """
    db: Session = SessionLocal()
    
    try:
        logger.info(f"Starting processing for transaction: {transaction_id}")
        
        # simulate calling external payment API - takes 30 seconds
        time.sleep(30)
        
        # update the transaction status
        transaction = db.query(Transaction).filter(
            Transaction.transaction_id == transaction_id
        ).first()
        
        if transaction:
            transaction.status = TransactionStatus.PROCESSED
            transaction.processed_at = datetime.utcnow()
            db.commit()
            logger.info(f"Successfully processed transaction: {transaction_id}")
        else:
            logger.error(f"Transaction not found: {transaction_id}")
            
    except Exception as e:
        logger.error(f"Error processing transaction {transaction_id}: {str(e)}")
        db.rollback()
        
        # mark it as failed so we know something went wrong
        try:
            transaction = db.query(Transaction).filter(
                Transaction.transaction_id == transaction_id
            ).first()
            if transaction:
                transaction.status = TransactionStatus.FAILED
                transaction.processed_at = datetime.utcnow()
                db.commit()
        except Exception as update_error:
            logger.error(f"Failed to update transaction status: {str(update_error)}")
            
        # retry the task after a minute
        raise self.retry(exc=e, countdown=60)
        
    finally:
        db.close()
