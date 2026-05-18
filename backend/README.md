# Backend

FastAPI backend for Stockwire Rental.

## Run locally

```bash
pip install -e .[dev]
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Test

```bash
pytest
```
