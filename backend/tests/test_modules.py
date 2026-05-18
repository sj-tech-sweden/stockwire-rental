from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_bootstrap_modules() -> None:
    paths = [
        "/api/v1/auth/bootstrap",
        "/api/v1/inventory/bootstrap",
        "/api/v1/jobs/bootstrap",
        "/api/v1/finance/bootstrap",
    ]

    for path in paths:
        response = client.get(path)
        assert response.status_code == 200
        assert response.json()["status"] == "scaffolded"
