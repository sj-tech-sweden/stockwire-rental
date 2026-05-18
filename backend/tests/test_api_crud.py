def test_auth_crud(client):
    created = client.post(
        "/api/v1/auth/users",
        json={
            "email": "admin@example.com",
            "password": "test",
            "full_name": "Admin User",
            "is_active": True,
            "role": "admin",
        },
    )
    assert created.status_code == 201

    users = client.get("/api/v1/auth/users")
    assert users.status_code == 200
    assert len(users.json()) == 1

    user_id = users.json()[0]["id"]
    fetched = client.get(f"/api/v1/auth/users/{user_id}")
    assert fetched.status_code == 200
    assert fetched.json()["email"] == "admin@example.com"


def test_inventory_crud(client):
    product = client.post(
        "/api/v1/inventory/products",
        json={"sku": "SPK-01", "name": "Speaker", "category": "audio", "daily_rate": "300.00"},
    )
    assert product.status_code == 200
    product_id = product.json()["id"]

    updated_product = client.put(
        f"/api/v1/inventory/products/{product_id}",
        json={"name": "Speaker Pro"},
    )
    assert updated_product.status_code == 200
    assert updated_product.json()["name"] == "Speaker Pro"

    device = client.post(
        "/api/v1/inventory/devices",
        json={
            "product_id": product_id,
            "asset_tag": "SPK-01-001",
            "serial_number": "SERIAL-1",
            "status": "available",
            "notes": "Test device",
        },
    )
    assert device.status_code == 200

    zone = client.post(
        "/api/v1/inventory/zones",
        json={"code": "A-01", "name": "Main zone", "zone_type": "rack"},
    )
    assert zone.status_code == 200
    zone_id = zone.json()["id"]

    updated_zone = client.put(f"/api/v1/inventory/zones/{zone_id}", json={"name": "Main rack"})
    assert updated_zone.status_code == 200

    list_products = client.get("/api/v1/inventory/products")
    list_devices = client.get("/api/v1/inventory/devices")
    list_zones = client.get("/api/v1/inventory/zones")

    assert list_products.status_code == 200 and len(list_products.json()) == 1
    assert list_devices.status_code == 200 and len(list_devices.json()) == 1
    assert list_zones.status_code == 200 and len(list_zones.json()) == 1


def test_jobs_and_finance_crud(client):
    product = client.post(
        "/api/v1/inventory/products",
        json={"sku": "LGT-01", "name": "Light", "category": "lighting", "daily_rate": "250.00"},
    )
    product_id = product.json()["id"]

    job = client.post(
        "/api/v1/jobs",
        json={"job_code": "JOB-1", "customer_name": "Customer", "status": "draft"},
    )
    assert job.status_code == 200
    job_id = job.json()["id"]

    updated_job = client.put(f"/api/v1/jobs/{job_id}", json={"status": "confirmed"})
    assert updated_job.status_code == 200
    assert updated_job.json()["status"] == "confirmed"

    req = client.post(
        "/api/v1/jobs/requirements",
        json={"job_id": job_id, "product_id": product_id, "quantity_required": 2, "quantity_picked": 1},
    )
    assert req.status_code == 200
    req_id = req.json()["id"]

    req_updated = client.put(f"/api/v1/jobs/requirements/{req_id}", json={"quantity_picked": 2})
    assert req_updated.status_code == 200
    assert req_updated.json()["quantity_picked"] == 2

    tx = client.post(
        "/api/v1/finance/transactions",
        json={
            "job_id": job_id,
            "transaction_type": "payment",
            "status": "pending",
            "amount": "1200.00",
            "currency": "SEK",
        },
    )
    assert tx.status_code == 200
    tx_id = tx.json()["id"]

    tx_updated = client.put(f"/api/v1/finance/transactions/{tx_id}", json={"status": "completed"})
    assert tx_updated.status_code == 200
    assert tx_updated.json()["status"] == "completed"

    jobs = client.get("/api/v1/jobs")
    reqs = client.get("/api/v1/jobs/requirements")
    txs = client.get("/api/v1/finance/transactions")

    assert jobs.status_code == 200 and len(jobs.json()) == 1
    assert reqs.status_code == 200 and len(reqs.json()) == 1
    assert txs.status_code == 200 and len(txs.json()) == 1
