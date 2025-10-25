"""
Quick test script for manual webhook testing.
Just sends a webhook and polls for status changes.
"""
import requests
import time
import sys


BASE_URL = "http://localhost:8000"


def send_test_webhook(transaction_id=None):
    """Send a test webhook"""
    if not transaction_id:
        transaction_id = f"txn_manual_{int(time.time())}"
    
    payload = {
        "transaction_id": transaction_id,
        "source_account": "acc_user_manual",
        "destination_account": "acc_merchant_manual",
        "amount": 1500.00,
        "currency": "INR"
    }
    
    print(f"\n📤 Sending webhook for transaction: {transaction_id}")
    print(f"Payload: {payload}\n")
    
    try:
        response = requests.post(f"{BASE_URL}/v1/webhooks/transactions", json=payload)
        print(f"✅ Response Status: {response.status_code}")
        print(f"Response Body: {response.json()}\n")
        
        if response.status_code == 202:
            return transaction_id
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the service.")
        print("Make sure it's running: docker-compose up")
        return None


def check_status(transaction_id):
    """Check transaction status"""
    try:
        response = requests.get(f"{BASE_URL}/v1/transactions/{transaction_id}")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Status check failed: {response.status_code}")
            return None
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the service.")
        return None


def poll_until_processed(transaction_id, max_wait=40):
    """Poll transaction status until it's processed"""
    print(f"⏳ Polling status for transaction: {transaction_id}")
    print(f"Checking every 5 seconds for up to {max_wait} seconds...\n")
    
    start_time = time.time()
    
    while (time.time() - start_time) < max_wait:
        status = check_status(transaction_id)
        
        if status:
            elapsed = time.time() - start_time
            print(f"[{elapsed:.1f}s] Status: {status['status']}")
            
            if status['status'] == 'PROCESSED':
                print(f"\n✅ Transaction PROCESSED!")
                print(f"📊 Final Details:")
                print(f"  - Transaction ID: {status['transaction_id']}")
                print(f"  - Amount: {status['amount']} {status['currency']}")
                print(f"  - Created: {status['created_at']}")
                print(f"  - Processed: {status['processed_at']}")
                return status
            elif status['status'] == 'FAILED':
                print(f"\n❌ Transaction FAILED!")
                return status
        
        time.sleep(5)
    
    print(f"\n⏱️ Timeout after {max_wait} seconds")
    return check_status(transaction_id)


def main():
    """Main function"""
    print("=" * 60)
    print("PAYMENT WEBHOOK - MANUAL TEST")
    print("=" * 60)
    
    # check if transaction ID provided
    transaction_id = None
    if len(sys.argv) > 1:
        transaction_id = sys.argv[1]
        print(f"\nUsing provided transaction ID: {transaction_id}")
    
    # send webhook
    transaction_id = send_test_webhook(transaction_id)
    
    if not transaction_id:
        print("Failed to send webhook. Exiting.")
        return
    
    # initial status check
    print("📊 Initial Status:")
    status = check_status(transaction_id)
    if status:
        print(f"  Status: {status['status']}")
        print(f"  Created: {status['created_at']}")
    
    # ask if user wants to poll
    print("\n" + "=" * 60)
    response = input("Poll for status updates? (y/n): ")
    
    if response.lower() == 'y':
        poll_until_processed(transaction_id)
    else:
        print(f"\nYou can check status manually with:")
        print(f"curl {BASE_URL}/v1/transactions/{transaction_id}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
