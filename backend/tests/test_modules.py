def test_bootstrap_modules(client) -> None:
    auth_response = client.get("/api/v1/auth/bootstrap-status")
    assert auth_response.status_code == 200
    assert "setup_needed" in auth_response.json()

    paths = [
        "/api/v1/inventory/bootstrap",
        "/api/v1/customers/bootstrap",
        "/api/v1/companies/bootstrap",
        "/api/v1/persons/bootstrap",
        "/api/v1/jobs/bootstrap",
        "/api/v1/venues/bootstrap",
        "/api/v1/finance/bootstrap",
    ]

    for path in paths:
        response = client.get(path)
        assert response.status_code == 200
        assert response.json()["status"] == "scaffolded"
