# Quick Start Guide

## Option 1: Docker (Easiest - Recommended)

```bash
# start everything
docker-compose up --build

# test it
python manual_test.py
```

## Option 2: Local Development (Windows)

If you want to run it locally without Docker:

```powershell
# create virtual environment
python -m venv venv
.\venv\Scripts\activate

# install dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt

# set environment variables
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:5432/payment_db"
$env:REDIS_URL="redis://localhost:6379/0"

# start PostgreSQL (need Docker or local install)
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:15-alpine

# start Redis (need Docker or local install)
docker run -d -p 6379:6379 redis:7-alpine

# run the API
uvicorn app.main:app --reload

# in another terminal, run celery worker
.\venv\Scripts\activate
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:5432/payment_db"
$env:REDIS_URL="redis://localhost:6379/0"
celery -A app.celery_app worker --loglevel=info --pool=solo
```

## Testing

```bash
# comprehensive tests
python test_service.py

# interactive testing
python manual_test.py

# or test specific transaction
python manual_test.py txn_my_custom_id
```

## Useful Commands

```bash
# view all logs
docker-compose logs -f

# specific service logs
docker-compose logs -f api
docker-compose logs -f worker

# stop everything
docker-compose down

# rebuild and restart
docker-compose up --build

# connect to postgres
docker-compose exec db psql -U postgres -d payment_db

# check celery workers
docker-compose exec worker celery -A app.celery_app inspect active
```
