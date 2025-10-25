"""
Performance testing script for the payment webhook service.
Tests response time and concurrent request handling.
"""
import requests
import time
import concurrent.futures
from datetime import datetime


BASE_URL = "http://localhost:8000"


def test_health_check():
    """Test the health check endpoint"""
    print("\n=== Testing Health Check ===")
    response = requests.get(f"{BASE_URL}/")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    assert response.json()["status"] == "HEALTHY"
    print("✅ Health check passed")


def send_webhook(transaction_id):
    """Send a single webhook and measure response time"""
    payload = {
        "transaction_id": transaction_id,
        "source_account": f"acc_user_{transaction_id}",
        "destination_account": f"acc_merchant_{transaction_id}",
        "amount": 1500.50,
        "currency": "INR"
    }
    
    start_time = time.time()
    response = requests.post(f"{BASE_URL}/v1/webhooks/transactions", json=payload)
    response_time = (time.time() - start_time) * 1000  # ms
    
    return {
        "transaction_id": transaction_id,
        "status_code": response.status_code,
        "response_time_ms": response_time,
        "response": response.json() if response.status_code == 202 else None
    }


def test_single_transaction():
    """Test 1: Single transaction processing"""
    print("\n=== Test 1: Single Transaction ===")
    
    transaction_id = f"txn_single_{int(time.time())}"
    result = send_webhook(transaction_id)
    
    print(f"Transaction ID: {result['transaction_id']}")
    print(f"Status Code: {result['status_code']}")
    print(f"Response Time: {result['response_time_ms']:.2f}ms")
    print(f"Response: {result['response']}")
    
    assert result['status_code'] == 202
    assert result['response_time_ms'] < 500, f"Response time {result['response_time_ms']}ms exceeds 500ms"
    
    print("\n⏳ Checking initial status (should be PROCESSING)...")
    status_response = requests.get(f"{BASE_URL}/v1/transactions/{transaction_id}")
    print(f"Status: {status_response.json()}")
    assert status_response.json()["status"] == "PROCESSING"
    
    print("\n⏳ Waiting 35 seconds for processing...")
    time.sleep(35)
    
    print("\n📊 Checking final status (should be PROCESSED)...")
    status_response = requests.get(f"{BASE_URL}/v1/transactions/{transaction_id}")
    final_status = status_response.json()
    print(f"Final Status: {final_status}")
    assert final_status["status"] == "PROCESSED"
    assert final_status["processed_at"] is not None
    
    print("✅ Single transaction test passed")


def test_idempotency():
    """Test 2: Duplicate webhook handling"""
    print("\n=== Test 2: Idempotency (Duplicate Prevention) ===")
    
    transaction_id = f"txn_duplicate_{int(time.time())}"
    
    # send same webhook multiple times
    print(f"\n📤 Sending same webhook 5 times for transaction: {transaction_id}")
    results = []
    for i in range(5):
        result = send_webhook(transaction_id)
        results.append(result)
        print(f"  Request {i+1}: {result['status_code']} in {result['response_time_ms']:.2f}ms")
    
    # all should return 202
    for result in results:
        assert result['status_code'] == 202
    
    print("\n⏳ Waiting 35 seconds for processing...")
    time.sleep(35)
    
    # verify only one transaction processed
    print("\n📊 Verifying only one transaction was processed...")
    status_response = requests.get(f"{BASE_URL}/v1/transactions/{transaction_id}")
    final_status = status_response.json()
    print(f"Final Status: {final_status}")
    
    assert final_status["status"] == "PROCESSED"
    print("✅ Idempotency test passed - duplicates handled correctly")


def test_performance():
    """Test 3: Performance under load."""
    print("\n=== Test 3: Performance Under Load ===")
    
    num_requests = 20
    print(f"\n📤 Sending {num_requests} concurrent webhooks...")
    
    transaction_ids = [f"txn_perf_{int(time.time())}_{i}" for i in range(num_requests)]
    
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(send_webhook, transaction_ids))
    
    total_time = time.time() - start_time
    
    # Analyze results
    response_times = [r['response_time_ms'] for r in results]
    avg_response_time = sum(response_times) / len(response_times)
    max_response_time = max(response_times)
    min_response_time = min(response_times)
    
    successful_requests = sum(1 for r in results if r['status_code'] == 202)
    
    print(f"\n📊 Performance Results:")
    print(f"  Total Requests: {num_requests}")
    print(f"  Successful: {successful_requests}")
    print(f"  Total Time: {total_time:.2f}s")
    print(f"  Average Response Time: {avg_response_time:.2f}ms")
    print(f"  Min Response Time: {min_response_time:.2f}ms")
    print(f"  Max Response Time: {max_response_time:.2f}ms")
    
    # All responses should be within 500ms
    assert max_response_time < 500, f"Max response time {max_response_time}ms exceeds 500ms requirement"
    assert successful_requests == num_requests
    
    print("✅ Performance test passed - all requests under 500ms")


def test_error_handling():
    """Test 4: Error handling with invalid data."""
    print("\n=== Test 4: Error Handling ===")
    
    # Test with invalid amount (negative)
    invalid_payload = {
        "transaction_id": "txn_invalid_001",
        "source_account": "acc_user_001",
        "destination_account": "acc_merchant_001",
        "amount": -100,  # Invalid
        "currency": "INR"
    }
    
    response = requests.post(f"{BASE_URL}/v1/webhooks/transactions", json=invalid_payload)
    print(f"Invalid amount test - Status Code: {response.status_code}")
    assert response.status_code == 422  # Validation error
    
    # Test with missing required field
    incomplete_payload = {
        "transaction_id": "txn_invalid_002",
        "source_account": "acc_user_002",
        # Missing destination_account
        "amount": 100,
        "currency": "INR"
    }
    
    response = requests.post(f"{BASE_URL}/v1/webhooks/transactions", json=incomplete_payload)
    print(f"Missing field test - Status Code: {response.status_code}")
    assert response.status_code == 422  # Validation error
    
    print("✅ Error handling test passed")


def test_transaction_query():
    """Test 5: Transaction status query."""
    print("\n=== Test 5: Transaction Query ===")
    
    # Query non-existent transaction
    response = requests.get(f"{BASE_URL}/v1/transactions/txn_nonexistent")
    print(f"Non-existent transaction - Status Code: {response.status_code}")
    assert response.status_code == 404
    
    # Create and query existing transaction
    transaction_id = f"txn_query_{int(time.time())}"
    send_webhook(transaction_id)
    
    response = requests.get(f"{BASE_URL}/v1/transactions/{transaction_id}")
    print(f"Existing transaction - Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    assert response.json()["transaction_id"] == transaction_id
    
    print("✅ Transaction query test passed")


def main():
    """Run all tests"""
    print("=" * 60)
    print("PAYMENT WEBHOOK SERVICE - TEST SUITE")
    print("=" * 60)
    
    try:
        # basic connectivity
        test_health_check()
        
        # run all tests
        test_single_transaction()
        test_idempotency()
        test_performance()
        test_error_handling()
        test_transaction_query()
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        raise
    except requests.exceptions.ConnectionError:
        print("\n❌ Could not connect to the service.")
        print("Make sure the service is running: docker-compose up")
        raise
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        raise


if __name__ == "__main__":
    main()
