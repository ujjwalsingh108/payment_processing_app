# Payment Webhook Processing Service

A service for receiving and processing payment transaction webhooks from external payment processors (like RazorPay). The main goal is to acknowledge webhooks super fast and then process them in the background without blocking.

## How it Works

The basic flow is:
1. Webhook comes in → API responds immediately with 202 Accepted (takes like <100ms)
2. Transaction gets saved to PostgreSQL database
3. Celery worker picks it up and processes in background (takes ~30 seconds)
4. You can check status anytime via the query endpoint

```
Webhook → FastAPI → PostgreSQL + Redis Queue → Celery Worker → Update Status
```

## Features

- Fast webhook acknowledgment (way under the 500ms requirement)
- Handles duplicate webhooks gracefully (won't process same transaction twice)
- Background processing with Celery
- PostgreSQL for storing everything
- Health check endpoint
- Can query transaction status
- Auto-retry if processing fails
- Everything runs in Docker

## Getting Started

### What you need:
- Docker & Docker Compose
- Git

### Running it:

1. Clone the repo
   ```bash
   git clone https://github.com/ujjwalsingh108/payment_processing_app.git
   cd payment_processing_app
   ```

2. Copy the env file
   ```bash
   cp .env.example .env
   ```

3. Fire up everything with docker-compose
   ```bash
   docker-compose up --build
   ```

   This starts:
   - FastAPI on `http://localhost:8000`
   - PostgreSQL on `localhost:5432`
   - Redis on `localhost:6379`
   - Celery worker running in background

4. Check if it's working
   ```bash
   curl http://localhost:8000/
   ```

   Should return something like:
   ```json
   {
     "status": "HEALTHY",
     "current_time": "2024-01-15T10:30:00Z"
   }
   ```

## API Endpoints

### Health Check
`GET /`

Just checks if the service is alive.

```bash
curl http://localhost:8000/
```

### Webhook Endpoint
`POST /v1/webhooks/transactions`

This is the main one - receives transaction webhooks and returns immediately.

```bash
curl -X POST http://localhost:8000/v1/webhooks/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "txn_abc123def456",
    "source_account": "acc_user_789",
    "destination_account": "acc_merchant_456",
    "amount": 1500,
    "currency": "INR"
  }'
```

Response:
```json
{
  "message": "Transaction accepted for processing",
  "transaction_id": "txn_abc123def456"
}
```

### Get Transaction Status
`GET /v1/transactions/{transaction_id}`

Check what's happening with a transaction.

```bash
curl http://localhost:8000/v1/transactions/txn_abc123def456
```

When it's still processing:
```json
{
  "transaction_id": "txn_abc123def456",
  "source_account": "acc_user_789",
  "destination_account": "acc_merchant_456",
  "amount": 1500.0,
  "currency": "INR",
  "status": "PROCESSING",
  "created_at": "2024-01-15T10:30:00Z",
  "processed_at": null
}
```

After ~30 seconds:
```json
{
  "transaction_id": "txn_abc123def456",
  "source_account": "acc_user_789",
  "destination_account": "acc_merchant_456",
  "amount": 1500.0,
  "currency": "INR",
  "status": "PROCESSED",
  "created_at": "2024-01-15T10:30:00Z",
  "processed_at": "2024-01-15T10:30:30Z"
}
```

## Testing

I included some test scripts to make testing easier.

### Test 1: Single Transaction

```bash
# Send a webhook
curl -X POST http://localhost:8000/v1/webhooks/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "txn_test_001",
    "source_account": "acc_user_001",
    "destination_account": "acc_merchant_001",
    "amount": 1500,
    "currency": "INR"
  }'

# Check status right away (should say PROCESSING)
curl http://localhost:8000/v1/transactions/txn_test_001

# Wait about 30 seconds then check again (should say PROCESSED)
sleep 30
curl http://localhost:8000/v1/transactions/txn_test_001
```

### Test 2: Duplicate Prevention

Send the same webhook multiple times and make sure only one gets processed:

```bash
# Send same webhook 3 times
for i in {1..3}; do
  curl -X POST http://localhost:8000/v1/webhooks/transactions \
    -H "Content-Type: application/json" \
    -d '{
      "transaction_id": "txn_duplicate_test",
      "source_account": "acc_user_002",
      "destination_account": "acc_merchant_002",
      "amount": 2500,
      "currency": "INR"
    }'
done

# Check - should only show ONE transaction
curl http://localhost:8000/v1/transactions/txn_duplicate_test
```

### Test 3: Run All Tests

There's a test script that runs everything:

```bash
python test_service.py
```

### Interactive Testing

Or use the manual test script for a more interactive experience:

```bash
python manual_test.py
```

Also check out the API docs at `http://localhost:8000/docs` - it's pretty handy for testing.

## Why I Chose These Technologies

### FastAPI
I went with FastAPI because it's super fast and has built-in support for async operations. Plus the automatic API documentation is really nice for testing. The type hints make debugging way easier too.

### PostgreSQL
Needed a solid database that could handle concurrent writes (important for webhooks that might arrive at the same time). PostgreSQL's ACID guarantees are important for financial data, and the primary key constraint makes idempotency really simple.

### Celery + Redis
Pretty much the standard for background jobs in Python. Redis is fast for queueing messages, and Celery handles all the retry logic and task management. Could've used something like AWS SQS but wanted to keep it simple to run locally.

### SQLAlchemy
Makes database stuff way easier. The ORM is nice but you can still write raw SQL if you need to optimize something.

### Docker
Everything runs in containers so it's easy to set up and deploy. No "works on my machine" problems.

## Project Structure

```
payment_processing_app/
├── app/
│   ├── main.py           # API endpoints
│   ├── models.py         # Database models
│   ├── schemas.py        # Request/response schemas
│   ├── database.py       # DB connection
│   ├── config.py         # Settings
│   ├── celery_app.py    # Celery setup
│   └── tasks.py         # Background tasks
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

## Configuration

Set these in your `.env` file:

```env
DATABASE_URL=postgresql://postgres:postgres@db:5432/payment_db
REDIS_URL=redis://redis:6379/0
API_VERSION=v1
LOG_LEVEL=INFO
```

## Checking Logs

```bash
# See all logs
docker-compose logs -f

# Just API logs
docker-compose logs -f api

# Worker logs
docker-compose logs -f worker
```

## Deploying to Production

Haven't deployed this yet but here's what I'd probably do:

### Option 1: AWS
- Use ECS or EKS for containers
- RDS for PostgreSQL
- ElastiCache for Redis
- Maybe add an ALB in front

### Option 2: Heroku (easiest)
```bash
heroku create payment-webhook-app
heroku addons:create heroku-postgresql:mini
heroku addons:create heroku-redis:mini
git push heroku main
heroku ps:scale web=1 worker=1
```

### Things to add for production:
- [ ] Proper logging (maybe Datadog or CloudWatch)
- [ ] Webhook signature verification (security!)
- [ ] Rate limiting
- [ ] HTTPS (obviously)
- [ ] More workers if needed
- [ ] Database backups
- [ ] Monitoring/alerts for failed tasks
- [ ] Maybe add authentication

## Known Issues / TODOs

- Need to add webhook signature verification for security
- Should probably add some kind of admin panel to view transactions
- Rate limiting would be good to prevent abuse
- Could optimize the database queries a bit more
- Might want to add some metrics/monitoring

## Troubleshooting

**Services won't start?**
```bash
docker-compose down
docker-compose up --build
```

**Database connection errors?**
```bash
docker-compose restart db
```

**Tasks not processing?**
Check the worker logs:
```bash
docker-compose logs worker
```

## Performance

From my testing:
- Webhook response time: Usually around 50-80ms
- Processing delay: 30 seconds (as required)
- Can handle lots of concurrent webhooks without issues
- Duplicates are handled properly with zero processing

## License

MIT

## Author

Ujjwal Singh

---

Built this as a demo for handling payment webhooks. Let me know if you find any issues!
