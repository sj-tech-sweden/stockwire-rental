import json
import socket
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from app.config import settings
from app.domain.settings import router as settings_router


def test_auth_crud(client):
    created = client.post(
        "/api/v1/auth/users",
        json={
            "email": "manager@example.com",
            "password": "test-pass-123",
            "full_name": "Manager User",
            "role": "manager",
            "is_active": True,
        },
    )
    assert created.status_code == 201

    users = client.get("/api/v1/auth/users")
    assert users.status_code == 200
    assert len(users.json()) == 2

    user_id = next(user["id"] for user in users.json() if user["email"] == "manager@example.com")
    fetched = client.get(f"/api/v1/auth/users/{user_id}")
    assert fetched.status_code == 200
    assert fetched.json()["email"] == "manager@example.com"


def test_inventory_crud(client):
    product = client.post(
        "/api/v1/inventory/products",
        json={
            "sku": "SPK-01",
            "name": "Speaker",
            "category": "audio",
            "brand": "d&b",
            "manufacturer": "d&b audiotechnik",
            "product_type": "equipment",
            "weight_kg": "12.500",
            "height_cm": "55.00",
            "width_cm": "34.00",
            "depth_cm": "31.00",
            "maintenance_interval_days": 120,
            "power_consumption_watts": "560.00",
            "daily_rate": "300.00",
            "replace_cost": "1500.00",
        },
    )
    assert product.status_code == 200
    product_id = product.json()["id"]
    assert product.json()["brand"] == "d&b"
    assert product.json()["maintenance_interval_days"] == 120
    assert product.json()["replace_cost"] is not None

    updated_product = client.put(
        f"/api/v1/inventory/products/{product_id}",
        json={"name": "Speaker Pro"},
    )
    assert updated_product.status_code == 200
    assert updated_product.json()["name"] == "Speaker Pro"
    assert updated_product.json()["total_devices"] == 0

    updated_replace_cost = client.put(
        f"/api/v1/inventory/products/{product_id}",
        json={"replace_cost": "1750.55"},
    )
    assert updated_replace_cost.status_code == 200
    assert float(updated_replace_cost.json()["replace_cost"]) == 1750.55

    device = client.post(
        "/api/v1/inventory/devices",
        json={
            "product_id": product_id,
            "asset_tag": "SPK-01-001",
            "serial_number": "SERIAL-1",
            "barcode": "BAR-1001",
            "qr_code": "QR-1001",
            "rfid": "RFID-1001",
            "location_zone_id": 1,
            "status": "available",
            "condition": "good",
            "purchase_date": "2025-01-01",
            "warranty_end_date": "2027-01-01",
            "usage_hours": "15.50",
            "notes": "Test device",
        },
    )
    assert device.status_code == 404

    zone = client.post(
        "/api/v1/inventory/zones",
        json={"code": "A-01", "name": "Main zone", "zone_type": "rack", "sort_order": 0, "is_active": True},
    )
    assert zone.status_code == 200
    zone_id = zone.json()["id"]

    device = client.post(
        "/api/v1/inventory/devices",
        json={
            "product_id": product_id,
            "asset_tag": "SPK-01-001",
            "serial_number": "SERIAL-1",
            "barcode": "BAR-1001",
            "qr_code": "QR-1001",
            "rfid": "RFID-1001",
            "location_zone_id": zone_id,
            "status": "available",
            "condition": "good",
            "purchase_date": "2025-01-01",
            "warranty_end_date": "2027-01-01",
            "usage_hours": "15.50",
            "notes": "Test device",
        },
    )
    assert device.status_code == 200
    assert device.json()["location_zone_id"] == zone_id

    bulk = client.post(
        f"/api/v1/inventory/products/{product_id}/devices",
        json={
            "quantity": 2,
            "auto_generate": True,
            "asset_tag_prefix": "SPK-01",
            "status": "available",
            "condition": "good",
            "location_zone_id": zone_id,
        },
    )
    assert bulk.status_code == 200
    assert len(bulk.json()) == 2

    sub_zone = client.post(
        "/api/v1/inventory/zones",
        json={"code": "A-01-01", "name": "Shelf 1", "zone_type": "shelf", "parent_id": zone_id, "sort_order": 0, "is_active": True},
    )
    assert sub_zone.status_code == 200

    moved_zone = client.post(
        f"/api/v1/inventory/zones/{sub_zone.json()['id']}/move",
        json={"parent_id": None, "before_id": zone_id},
    )
    assert moved_zone.status_code == 200
    assert moved_zone.json()["parent_id"] is None

    updated_zone = client.put(f"/api/v1/inventory/zones/{zone_id}", json={"name": "Main rack"})
    assert updated_zone.status_code == 200

    list_products = client.get("/api/v1/inventory/products")
    list_devices = client.get("/api/v1/inventory/devices")
    list_zones = client.get("/api/v1/inventory/zones")
    zone_tree = client.get("/api/v1/inventory/zones/tree")

    assert list_products.status_code == 200 and len(list_products.json()) == 1
    assert list_devices.status_code == 200 and len(list_devices.json()) == 3
    assert list_zones.status_code == 200 and len(list_zones.json()) == 2
    assert zone_tree.status_code == 200 and len(zone_tree.json()) >= 1
    assert list_products.json()[0]["total_devices"] == 3
    assert list_products.json()[0]["in_store_devices"] == 3


def test_eventory_connection_get_fallback_treats_http_error_as_reachable(client):
    class FakeSocket:
        def getpeername(self):
            return ("1.1.1.1", 443)

    class FakeRaw:
        def __init__(self):
            self._sock = FakeSocket()

    class FakeBuffer:
        def __init__(self):
            self.raw = FakeRaw()

    class FakeFp:
        def __init__(self):
            self.fp = FakeBuffer()

        def close(self):
            return None

    class FakeOpener:
        def open(self, req, timeout=0):
            if req.get_method() == "HEAD":
                raise URLError("head unsupported")
            raise HTTPError(req.full_url, 302, "redirect blocked", None, FakeFp())

    with patch("app.domain.settings.router.socket.getaddrinfo") as mock_getaddrinfo, patch(
        "app.domain.settings.router.build_opener", return_value=FakeOpener()
    ):
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("1.1.1.1", 443)),
        ]
        response = client.post(
            "/api/v1/settings/integrations/eventory/test",
            json={"config": {"api_url": "https://api.eventory.se"}},
        )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "plugin": "eventory",
        "message": "Connection reached endpoint (GET status 302)",
        "status_code": 302,
    }


def test_eventory_connection_private_peer_returns_structured_error(client):
    class FakeSocket:
        def getpeername(self):
            return ("127.0.0.1", 443)

    class FakeRaw:
        def __init__(self):
            self._sock = FakeSocket()

    class FakeBuffer:
        def __init__(self):
            self.raw = FakeRaw()

    class FakeResponse:
        def __init__(self):
            self.status = 200
            self.fp = FakeBuffer()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeOpener:
        def open(self, req, timeout=0):
            return FakeResponse()

    with patch("app.domain.settings.router.socket.getaddrinfo") as mock_getaddrinfo, patch(
        "app.domain.settings.router.build_opener", return_value=FakeOpener()
    ):
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("1.1.1.1", 443)),
        ]
        response = client.post(
            "/api/v1/settings/integrations/eventory/test",
            json={"config": {"api_url": "https://api.eventory.se"}},
        )

    assert response.status_code == 200
    assert response.json() == {
        "ok": False,
        "plugin": "eventory",
        "message": "API URL connected to a non-public IP address",
        "status_code": None,
    }


def test_eventory_connection_disallowed_head_peer_does_not_retry_get(client):
    calls: list[str] = []

    class FakeOpener:
        def open(self, req, timeout=0):
            calls.append(req.get_method())
            raise URLError("Outbound connection resolved to a disallowed network address")

    with patch("app.domain.settings.router.socket.getaddrinfo") as mock_getaddrinfo, patch(
        "app.domain.settings.router.build_opener", return_value=FakeOpener()
    ):
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("1.1.1.1", 443)),
        ]
        response = client.post(
            "/api/v1/settings/integrations/eventory/test",
            json={"config": {"api_url": "https://api.eventory.se"}},
        )

    assert calls == ["HEAD"]
    assert response.status_code == 200
    assert response.json() == {
        "ok": False,
        "plugin": "eventory",
        "message": "API URL connected to a non-public IP address",
        "status_code": None,
    }


def test_customers_and_venues_crud(client):
    customer = client.post(
        "/api/v1/customers",
        json={"name": "Tsunami Events", "email": "info@example.com", "phone": "+46 70 123 45 67"},
    )
    assert customer.status_code == 200
    customer_id = customer.json()["id"]

    updated_customer = client.put(f"/api/v1/customers/{customer_id}", json={"name": "Tsunami Events AB"})
    assert updated_customer.status_code == 200
    assert updated_customer.json()["name"] == "Tsunami Events AB"

    venue = client.post(
        "/api/v1/venues",
        json={"name": "Main Hall", "address": "Main Street 1", "city": "Stockholm"},
    )
    assert venue.status_code == 200
    venue_id = venue.json()["id"]

    updated_venue = client.put(f"/api/v1/venues/{venue_id}", json={"city": "Gothenburg"})
    assert updated_venue.status_code == 200
    assert updated_venue.json()["city"] == "Gothenburg"

    customers = client.get("/api/v1/customers")
    venues = client.get("/api/v1/venues")

    assert customers.status_code == 200 and len(customers.json()) == 1
    assert venues.status_code == 200 and len(venues.json()) == 1


def test_jobs_and_finance_crud(client):
    product = client.post(
        "/api/v1/inventory/products",
        json={"sku": "LGT-01", "name": "Light", "category": "lighting", "daily_rate": "250.00"},
    )
    assert product.status_code == 200
    product_id = product.json()["id"]

    customer = client.post(
        "/api/v1/customers",
        json={"name": "Customer One", "email": "customer@example.com"},
    )
    customer_id = customer.json()["id"]

    venue = client.post(
        "/api/v1/venues",
        json={"name": "Venue One", "city": "Malmö"},
    )
    venue_id = venue.json()["id"]

    job = client.post(
        "/api/v1/jobs",
        json={
            "job_code": "JOB-1",
            "customer_id": customer_id,
            "venue_id": venue_id,
            "status": "draft",
            "description": "Test job",
            "sales_price": "4200.00",
            "invoice_paid": False,
        },
    )
    assert job.status_code == 200
    job_id = job.json()["id"]
    assert job.json()["customer_name"] == "Customer One"
    assert job.json()["venue_name"] == "Venue One"

    updated_job = client.put(f"/api/v1/jobs/{job_id}", json={"status": "confirmed"})
    assert updated_job.status_code == 200
    assert updated_job.json()["status"] == "confirmed"

    paid_job = client.put(
        f"/api/v1/jobs/{job_id}",
        json={"invoice_paid": True, "invoice_paid_at": "2026-01-15"},
    )
    assert paid_job.status_code == 200
    assert paid_job.json()["invoice_paid"] is True

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
            "currency": "sek",
        },
    )
    assert tx.status_code == 200
    tx_id = tx.json()["id"]
    assert tx.json()["currency"] == "SEK"

    tx_updated = client.put(f"/api/v1/finance/transactions/{tx_id}", json={"status": "completed"})
    assert tx_updated.status_code == 200
    assert tx_updated.json()["status"] == "completed"

    tx_two = client.post(
        "/api/v1/finance/transactions",
        json={
            "job_id": job_id,
            "transaction_type": "deposit",
            "status": "pending",
            "amount": "500.00",
            "currency": "eur",
            "transaction_date": "2026-01-01T10:00:00Z",
            "due_date": "2026-01-10T10:00:00Z",
        },
    )
    assert tx_two.status_code == 200
    tx_two_id = tx_two.json()["id"]
    assert tx_two.json()["job_code"] == "JOB-1"
    assert tx_two.json()["currency"] == "EUR"

    invalid_currency = client.post(
        "/api/v1/finance/transactions",
        json={
            "job_id": job_id,
            "transaction_type": "payment",
            "status": "pending",
            "amount": "100.00",
            "currency": "EU",
        },
    )
    assert invalid_currency.status_code == 422

    filtered = client.get("/api/v1/finance/transactions", params={"transaction_type": "deposit"})
    assert filtered.status_code == 200
    assert len(filtered.json()) == 1
    assert filtered.json()[0]["id"] == tx_two_id

    settled = client.post(f"/api/v1/finance/transactions/{tx_two_id}/settle")
    assert settled.status_code == 200
    assert settled.json()["status"] == "completed"

    summary = client.get("/api/v1/finance/summary")
    assert summary.status_code == 200
    assert summary.json()["total_transactions"] == 2
    assert summary.json()["completed_count"] == 2

    insights = client.get("/api/v1/finance/job-insights")
    assert insights.status_code == 200
    assert insights.json()["jobs_total"] == 1
    assert insights.json()["projected_total_value"] is not None
    assert insights.json()["invoice_paid_jobs"] == 1
    assert insights.json()["sales_total_value"] is not None
    assert len(insights.json()["top_jobs"]) == 1
    assert insights.json()["top_jobs"][0]["job_code"] == "JOB-1"

    deleted = client.delete(f"/api/v1/finance/transactions/{tx_two_id}")
    assert deleted.status_code == 204

    jobs = client.get("/api/v1/jobs")
    reqs = client.get("/api/v1/jobs/requirements")
    txs = client.get("/api/v1/finance/transactions")

    assert jobs.status_code == 200 and len(jobs.json()) == 1
    assert reqs.status_code == 200 and len(reqs.json()) == 1
    assert txs.status_code == 200 and len(txs.json()) == 1


def test_company_profile_currency_settings(client):
    initial = client.get("/api/v1/settings/company-profile")
    assert initial.status_code == 200
    assert initial.json()["currency"] == "SEK"

    updated = client.put(
        "/api/v1/settings/company-profile",
        json={
            "company_name": "Tsunami Events",
            "default_language": "sv",
            "currency": "eur",
            "city": "Stockholm",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["currency"] == "EUR"
    assert updated.json()["default_language"] == "sv"

    persisted = client.get("/api/v1/settings/company-profile")
    assert persisted.status_code == 200
    assert persisted.json()["currency"] == "EUR"

    fallback = client.put(
        "/api/v1/settings/company-profile",
        json={
            "currency": "   ",
        },
    )
    assert fallback.status_code == 200
    assert fallback.json()["currency"] == "SEK"


def test_settings_modules_crud(client):
    location_types = client.get("/api/v1/settings/location-types")
    assert location_types.status_code == 200
    assert isinstance(location_types.json().get("options"), list)

    updated_location_types = client.put(
        "/api/v1/settings/location-types",
        json={"options": ["rack", "shelf", "truck"]},
    )
    assert updated_location_types.status_code == 200
    assert updated_location_types.json()["options"] == ["rack", "shelf", "truck"]

    category_prefill = client.get("/api/v1/settings/category-prefill")
    assert category_prefill.status_code == 200
    assert isinstance(category_prefill.json().get("paths"), list)

    updated_category_prefill = client.put(
        "/api/v1/settings/category-prefill",
        json={"paths": [["Audio", "Speakers"], ["Lighting", "Fixtures"]]},
    )
    assert updated_category_prefill.status_code == 200
    assert updated_category_prefill.json()["paths"] == [["Audio", "Speakers"], ["Lighting", "Fixtures"]]

    product_defaults = client.get("/api/v1/settings/product-defaults")
    assert product_defaults.status_code == 200
    assert product_defaults.json()["brand_options"] == settings_router.DEFAULT_BRAND_OPTIONS
    assert product_defaults.json()["manufacturer_options"] == settings_router.DEFAULT_MANUFACTURER_OPTIONS
    assert product_defaults.json()["brand_manufacturer_map"] == settings_router.DEFAULT_BRAND_MANUFACTURER_MAP
    assert product_defaults.json()["brand_links"] == settings_router.DEFAULT_BRAND_LINKS
    assert product_defaults.json()["manufacturer_links"] == settings_router.DEFAULT_MANUFACTURER_LINKS

    updated_product_defaults = client.put(
        "/api/v1/settings/product-defaults",
        json={
            "brand_options": ["generic", "yamaha"],
            "manufacturer_options": ["generic", "yamaha"],
            "default_brand": "yamaha",
            "default_manufacturer": "yamaha",
            "brand_manufacturer_map": {"yamaha": "yamaha"},
            "brand_links": {"yamaha": "https://example.com/yamaha"},
            "manufacturer_links": {"yamaha": "https://example.com/yamaha-mfg"},
        },
    )
    assert updated_product_defaults.status_code == 200
    assert updated_product_defaults.json()["default_brand"] == "yamaha"
    assert updated_product_defaults.json()["default_manufacturer"] == "yamaha"

    integrations = client.get("/api/v1/settings/integrations")
    assert integrations.status_code == 200
    assert isinstance(integrations.json().get("eventory_instances"), list)

    updated_integrations = client.put(
        "/api/v1/settings/integrations",
        json={
            "eventory_instances": [
                {
                    "id": "eventory-main",
                    "name": "Eventory Main",
                    "enabled": False,
                    "api_url": "https://api.eventory.se",
                    "api_key": "",
                    "username": "",
                    "password": "",
                    "token_endpoint": "",
                    "supplier_name": "Eventory",
                    "sync_interval_minutes": 60,
                    "price_margin_percent": 5,
                    "last_sync_at": None,
                    "last_sync_imported": 0,
                    "last_sync_updated": 0,
                    "last_sync_skipped": 0,
                    "last_sync_total": 0,
                    "sync_running": False,
                    "sync_started_at": None,
                    "sync_finished_at": None,
                    "sync_progress_current": 0,
                    "sync_progress_total": 0,
                    "sync_progress_percent": 0,
                    "sync_message": None,
                }
            ]
        },
    )
    assert updated_integrations.status_code == 200
    assert updated_integrations.json()["eventory_instances"][0]["sync_interval_minutes"] == 60

    invalid_port_integrations = client.put(
        "/api/v1/settings/integrations",
        json={
            "eventory_instances": [
                {
                    "id": "eventory-main",
                    "name": "Eventory Main",
                    "enabled": False,
                    "api_url": "https://api.eventory.se:0",
                    "api_key": "",
                    "username": "",
                    "password": "",
                    "token_endpoint": "",
                    "supplier_name": "Eventory",
                    "sync_interval_minutes": 60,
                    "price_margin_percent": 5,
                }
            ]
        },
    )
    assert invalid_port_integrations.status_code == 422
    assert invalid_port_integrations.json() == {"detail": "API URL contains an invalid port"}

    with patch("app.domain.settings.router.socket.getaddrinfo") as mock_getaddrinfo:
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("1.1.1.1", 443)),
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("127.0.0.1", 443)),
        ]
        mixed_dns = client.post(
            "/api/v1/settings/integrations/eventory/test",
            json={"config": {"api_url": "https://api.eventory.se"}},
        )
    assert mixed_dns.status_code == 200
    assert mixed_dns.json() == {
        "ok": False,
        "plugin": "eventory",
        "message": "API URL resolves to a non-public IP address",
        "status_code": None,
    }

    with patch("app.domain.settings.router.socket.getaddrinfo") as mock_getaddrinfo:
        zero_port = client.post(
            "/api/v1/settings/integrations/eventory/test",
            json={"config": {"api_url": "https://api.eventory.se:0"}},
        )
    assert zero_port.status_code == 200
    assert zero_port.json() == {
        "ok": False,
        "plugin": "eventory",
        "message": "API URL port is invalid",
        "status_code": None,
    }
    mock_getaddrinfo.assert_not_called()

    auth_sso = client.get("/api/v1/settings/auth-sso")
    assert auth_sso.status_code == 200

    updated_auth_sso = client.put(
        "/api/v1/settings/auth-sso",
        json={
            "enabled": True,
            "auto_create_users": True,
            "sync_roles_on_login": True,
            "default_role": "viewer",
            "group_role_map": {"warehouse-admins": "admin"},
            "oidc_providers": [],
            "saml_providers": [],
        },
    )
    assert updated_auth_sso.status_code == 200
    assert updated_auth_sso.json()["enabled"] is True
    assert updated_auth_sso.json()["group_role_map"]["warehouse-admins"] == "admin"

    templates = client.get("/api/v1/settings/label-templates")
    assert templates.status_code == 200

    created_template = client.post(
        "/api/v1/settings/label-templates",
        json={
            "name": "Default Product Label",
            "entity_type": "product",
            "print_preset": "62x29",
            "visibility": "all",
            "edit_roles": ["admin", "manager"],
            "canvas": {"width": 420, "height": 280},
            "elements": [
                {
                    "id": "name",
                    "kind": "field",
                    "source": "name",
                    "x": 10,
                    "y": 10,
                    "w": 200,
                    "h": 30,
                    "fontSize": 12,
                }
            ],
        },
    )
    assert created_template.status_code == 200
    template_id = created_template.json()["id"]

    updated_template = client.put(
        f"/api/v1/settings/label-templates/{template_id}",
        json={
            "name": "Default Product Label v2",
            "entity_type": "product",
            "print_preset": "62x29",
            "visibility": "all",
            "edit_roles": ["admin", "manager"],
            "canvas": {"width": 420, "height": 280},
            "elements": [
                {
                    "id": "name",
                    "kind": "field",
                    "source": "name",
                    "x": 12,
                    "y": 10,
                    "w": 220,
                    "h": 30,
                    "fontSize": 12,
                }
            ],
        },
    )
    assert updated_template.status_code == 200
    assert updated_template.json()["name"] == "Default Product Label v2"

    deleted_template = client.delete(f"/api/v1/settings/label-templates/{template_id}")
    assert deleted_template.status_code == 200


def test_inventory_category_move_and_custom_fields(client):
    root_audio = client.post(
        "/api/v1/inventory/categories",
        json={"name": "Audio", "parent_id": None, "sort_order": 0, "is_active": True},
    )
    assert root_audio.status_code == 201
    audio_id = root_audio.json()["id"]

    root_lighting = client.post(
        "/api/v1/inventory/categories",
        json={"name": "Lighting", "parent_id": None, "sort_order": 1, "is_active": True},
    )
    assert root_lighting.status_code == 201

    child = client.post(
        "/api/v1/inventory/categories",
        json={"name": "Speakers", "parent_id": audio_id, "sort_order": 0, "is_active": True},
    )
    assert child.status_code == 201
    child_id = child.json()["id"]

    moved_to_root = client.post(
        f"/api/v1/inventory/categories/{child_id}/move",
        json={"parent_id": None, "before_id": root_lighting.json()["id"]},
    )
    assert moved_to_root.status_code == 200
    assert moved_to_root.json()["parent_id"] is None

    product = client.post(
        "/api/v1/inventory/products",
        json={
            "sku": "CF-01",
            "name": "Custom Field Product",
            "category_id": moved_to_root.json()["id"],
            "daily_rate": "10.00",
        },
    )
    assert product.status_code == 200
    product_id = product.json()["id"]

    definition = client.post(
        "/api/v1/custom-fields/definitions",
        json={
            "entity_type": "product",
            "key": "serial_batch",
            "label": "Serial batch",
            "value_type": "text",
            "options": [],
            "is_required": False,
            "is_active": True,
        },
    )
    assert definition.status_code == 201
    definition_id = definition.json()["id"]

    upsert = client.put(
        f"/api/v1/custom-fields/values/product/{product_id}",
        json={"values": [{"field_definition_id": definition_id, "value": "Batch-A"}]},
    )
    assert upsert.status_code == 200
    assert upsert.json()["values"][0]["value"] == "Batch-A"

    cable_prefill = client.post("/api/v1/custom-fields/definitions/prefill-product-cable")
    assert cable_prefill.status_code == 200
    keys = {item["key"] for item in cable_prefill.json()}
    assert "cable_type" in keys
    assert "length_m" in keys


def test_settings_lists_and_defaults(client):
    initial_types = client.get("/api/v1/settings/location-types")
    assert initial_types.status_code == 200
    assert "warehouse" in initial_types.json()["options"]

    location_types = client.put(
        "/api/v1/settings/location-types",
        json={"options": ["rack", "warehouse", "stage"]},
    )
    assert location_types.status_code == 200
    assert "warehouse" in location_types.json()["options"]

    created_zone = client.post(
        "/api/v1/inventory/zones",
        json={"code": "W-01", "name": "Warehouse", "zone_type": "warehouse", "sort_order": 0, "is_active": True},
    )
    assert created_zone.status_code == 200

    listed_types = client.get("/api/v1/settings/location-types")
    assert listed_types.status_code == 200
    assert "warehouse" in listed_types.json()["options"]

    category_paths = [
        ["Warehouse", "Shelving"],
        ["Warehouse", "Packing"],
    ]
    updated_paths = client.put(
        "/api/v1/settings/category-prefill",
        json={"paths": category_paths},
    )
    assert updated_paths.status_code == 200
    assert updated_paths.json()["paths"] == category_paths

    prefill_categories = client.post("/api/v1/inventory/categories/prefill")
    assert prefill_categories.status_code == 200
    names = {item["name"] for item in prefill_categories.json()}
    assert "Warehouse" in names

    updated_defaults = client.put(
        "/api/v1/settings/product-defaults",
        json={
            "brand_options": ["Generic", "Yamaha"],
            "manufacturer_options": ["Generic", "Yamaha Corp"],
            "default_brand": "Yamaha",
            "default_manufacturer": "Yamaha Corp",
        },
    )
    assert updated_defaults.status_code == 200
    assert updated_defaults.json()["default_brand"] == "Yamaha"
    assert updated_defaults.json()["default_manufacturer"] == "Yamaha Corp"


def test_settings_version(client):
    response = client.get("/api/v1/settings/version")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert isinstance(data["version"], str)
    assert data["version"]
    assert data.get("backend_version") == data["version"]
    assert "postgres_version" in data
    assert data.get("valkey_version") is None or isinstance(data.get("valkey_version"), str)
    # Without check_updates the update fields should be absent / null
    assert data.get("latest_version") is None
    assert data.get("up_to_date") is None


def test_settings_version_check_updates_network_error(client):
    """When GitHub is unreachable the endpoint still returns 200 with only the current version."""
    with patch("app.domain.settings.router.build_opener") as mock_opener:
        mock_opener.return_value.open.side_effect = URLError("network error")
        response = client.get("/api/v1/settings/version", params={"check_updates": "true"})

    assert response.status_code == 200
    data = response.json()
    assert data["version"]
    assert data.get("backend_version") == data["version"]
    assert data.get("latest_version") is None
    assert data.get("up_to_date") is None


def test_inventory_maintenance_system(client):
    product = client.post(
        "/api/v1/inventory/products",
        json={
            "sku": "MNT-01",
            "name": "Maintenance Device Product",
            "maintenance_interval_days": 90,
            "daily_rate": "50.00",
        },
    )
    assert product.status_code == 200
    product_id = product.json()["id"]

    device = client.post(
        "/api/v1/inventory/devices",
        json={
            "product_id": product_id,
            "asset_tag": "MNT-01-001",
            "status": "available",
            "condition": "good",
            "purchase_date": "2026-01-01",
            "warranty_end_date": "2029-01-01",
        },
    )
    assert device.status_code == 200
    device_id = device.json()["id"]

    created = client.post(
        "/api/v1/inventory/maintenance",
        json={
            "device_id": device_id,
            "maintenance_type": "inspection",
            "status": "scheduled",
            "scheduled_date": "2026-06-01",
            "notes": "Initial check",
        },
    )
    assert created.status_code == 200
    maintenance_id = created.json()["id"]
    assert created.json()["asset_tag"] == "MNT-01-001"

    listed = client.get("/api/v1/inventory/maintenance")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    filtered = client.get("/api/v1/inventory/maintenance", params={"status": "scheduled"})
    assert filtered.status_code == 200
    assert len(filtered.json()) == 1

    updated = client.put(
        f"/api/v1/inventory/maintenance/{maintenance_id}",
        json={"status": "in_progress", "notes": "Technician assigned"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "in_progress"

    completed = client.post(
        f"/api/v1/inventory/maintenance/{maintenance_id}/complete",
        json={"completed_date": "2026-06-02", "notes": "Done"},
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert completed.json()["completed_date"] == "2026-06-02"

    second_device = client.post(
        "/api/v1/inventory/devices",
        json={
            "product_id": product_id,
            "asset_tag": "MNT-01-002",
            "status": "available",
            "condition": "good",
            "usage_hours": "120.00",
        },
    )
    assert second_device.status_code == 200

    bulk_schedule = client.post(
        "/api/v1/inventory/maintenance/bulk-schedule",
        json={
            "device_ids": [device_id, second_device.json()["id"]],
            "maintenance_type": "inspection",
            "interval_mode": "runtime",
            "interval_value": 100,
            "notes": "Runtime cycle",
        },
    )
    assert bulk_schedule.status_code == 200
    assert len(bulk_schedule.json()) == 2
    assert bulk_schedule.json()[0]["interval_mode"] == "runtime"


def test_inventory_defect_reports_comments_timeline(client):
    product = client.post(
        "/api/v1/inventory/products",
        json={
            "sku": "DEF-01",
            "name": "Defect Device Product",
            "daily_rate": "30.00",
        },
    )
    assert product.status_code == 200
    product_id = product.json()["id"]

    device = client.post(
        "/api/v1/inventory/devices",
        json={
            "product_id": product_id,
            "asset_tag": "DEF-01-001",
            "status": "in_service",
            "condition": "fair",
        },
    )
    assert device.status_code == 200
    device_id = device.json()["id"]

    maintenance = client.post(
        "/api/v1/inventory/maintenance",
        json={
            "device_id": device_id,
            "maintenance_type": "repair",
            "status": "in_progress",
            "notes": "Repair ticket",
        },
    )
    assert maintenance.status_code == 200
    maintenance_id = maintenance.json()["id"]

    created_report = client.post(
        "/api/v1/inventory/defect-reports",
        json={
            "device_id": device_id,
            "maintenance_id": maintenance_id,
            "title": "Audio output crackling",
            "description": "Intermittent crackling on channel B",
            "status": "open",
            "severity": "high",
        },
    )
    assert created_report.status_code == 200
    report_id = created_report.json()["id"]
    assert created_report.json()["asset_tag"] == "DEF-01-001"

    updated_report = client.put(
        f"/api/v1/inventory/defect-reports/{report_id}",
        json={
            "status": "in_progress",
            "description": "Inspected connectors and isolation transformer",
        },
    )
    assert updated_report.status_code == 200
    assert updated_report.json()["status"] == "in_progress"

    created_comment = client.post(
        f"/api/v1/inventory/defect-reports/{report_id}/comments",
        json={"comment": "Reproduced issue at 60% master volume"},
    )
    assert created_comment.status_code == 200
    comment_id = created_comment.json()["id"]

    updated_comment = client.put(
        f"/api/v1/inventory/defect-comments/{comment_id}",
        json={"comment": "Reproduced issue at 65% master volume"},
    )
    assert updated_comment.status_code == 200
    assert updated_comment.json()["comment"] == "Reproduced issue at 65% master volume"

    report_comments = client.get(f"/api/v1/inventory/defect-reports/{report_id}/comments")
    assert report_comments.status_code == 200
    assert len(report_comments.json()) == 1

    by_device_timeline = client.get("/api/v1/inventory/defect-timeline", params={"device_id": device_id})
    assert by_device_timeline.status_code == 200
    assert [entry["entry_type"] for entry in by_device_timeline.json()] == ["defect_report", "defect_comment"]
    assert by_device_timeline.json()[0]["status"] == "in_progress"

    by_service_timeline = client.get("/api/v1/inventory/defect-timeline", params={"maintenance_id": maintenance_id})
    assert by_service_timeline.status_code == 200
    assert len(by_service_timeline.json()) == 2

    deleted_comment = client.delete(f"/api/v1/inventory/defect-comments/{comment_id}")
    assert deleted_comment.status_code == 200
    assert deleted_comment.json() == {"ok": True}

    deleted_report = client.delete(f"/api/v1/inventory/defect-reports/{report_id}")
    assert deleted_report.status_code == 200
    assert deleted_report.json() == {"ok": True}


def test_settings_version_check_updates_strips_single_v_prefix(client):
    payload = {
        "tag_name": "vv1.2.3",
        "body": "notes",
        "html_url": "https://example.com/release",
    }

    with patch("app.domain.settings.router.build_opener") as mock_opener:
        response_context = mock_opener.return_value.open.return_value.__enter__.return_value
        response_context.read.return_value = json.dumps(payload).encode()
        response = client.get("/api/v1/settings/version", params={"check_updates": "true"})

    assert response.status_code == 200
    data = response.json()
    assert data.get("latest_version") == "v1.2.3"
    assert data.get("latest_release_url") is None


def test_settings_version_check_updates_single_v_prefix(client):
    payload = {
        "tag_name": "  v1.2.3  ",
        "body": "notes",
        "html_url": "https://github.com/sj-tech-sweden/stockwire-rental/releases/tag/v1.2.3",
    }

    with patch("app.domain.settings.router.build_opener") as mock_opener:
        response_context = mock_opener.return_value.open.return_value.__enter__.return_value
        response_context.read.return_value = json.dumps(payload).encode()
        response = client.get("/api/v1/settings/version", params={"check_updates": "true"})

    assert response.status_code == 200
    data = response.json()
    assert data.get("latest_version") == "1.2.3"
    assert data.get("latest_release_url") == "https://github.com/sj-tech-sweden/stockwire-rental/releases/tag/v1.2.3"


def test_settings_version_check_updates_whitespace_without_prefix(client):
    payload = {
        "tag_name": "  1.2.3  ",
        "body": "notes",
        "html_url": "https://github.com/sj-tech-sweden/stockwire-rental/releases/tag/v1.2.3",
    }

    with patch("app.domain.settings.router.build_opener") as mock_opener:
        response_context = mock_opener.return_value.open.return_value.__enter__.return_value
        response_context.read.return_value = json.dumps(payload).encode()
        response = client.get("/api/v1/settings/version", params={"check_updates": "true"})

    assert response.status_code == 200
    data = response.json()
    assert data.get("latest_version") == "1.2.3"
    assert data.get("latest_release_url") == "https://github.com/sj-tech-sweden/stockwire-rental/releases/tag/v1.2.3"


def test_settings_version_check_updates_rejects_unsafe_release_urls(client):
    for unsafe_url in [
        "http://github.com/sj-tech-sweden/stockwire-rental/releases/tag/v1.2.3",
        "https://malicious-site.com/fake-release",
        "https://attacker@github.com/sj-tech-sweden/stockwire-rental/releases/tag/v1.2.3",
        "https://user:pass@github.com/sj-tech-sweden/stockwire-rental/releases/tag/v1.2.3",
    ]:
        payload = {
            "tag_name": "v1.2.3",
            "body": "notes",
            "html_url": unsafe_url,
        }

        with patch("app.domain.settings.router.build_opener") as mock_opener:
            response_context = mock_opener.return_value.open.return_value.__enter__.return_value
            response_context.read.return_value = json.dumps(payload).encode()
            response = client.get("/api/v1/settings/version", params={"check_updates": "true"})

        assert response.status_code == 200
        data = response.json()
        assert data.get("latest_version") == "1.2.3"
        assert data.get("latest_release_url") is None


def test_scan_operations_and_job_requirement_bulk(client):
    product = client.post(
        "/api/v1/inventory/products",
        json={"sku": "SCN-01", "name": "Scan Product", "daily_rate": "10.00"},
    )
    assert product.status_code == 200
    product_id = product.json()["id"]

    zone = client.post(
        "/api/v1/inventory/zones",
        json={"code": "SCAN-ZONE", "name": "Scan Zone", "zone_type": "warehouse", "sort_order": 0, "is_active": True},
    )
    assert zone.status_code == 200

    device = client.post(
        "/api/v1/inventory/devices",
        json={
            "product_id": product_id,
            "asset_tag": "SCN-01-001",
            "barcode": "BC-SCN-01-001",
            "status": "available",
            "condition": "good",
        },
    )
    assert device.status_code == 200

    customer = client.post(
        "/api/v1/customers",
        json={"name": "Scan Customer", "email": "scan@example.com"},
    )
    assert customer.status_code == 200

    venue = client.post(
        "/api/v1/venues",
        json={"name": "Scan Venue", "city": "Stockholm"},
    )
    assert venue.status_code == 200

    job = client.post(
        "/api/v1/jobs",
        json={
            "job_code": "JOB-SCAN-001",
            "customer_id": customer.json()["id"],
            "venue_id": venue.json()["id"],
            "status": "confirmed",
        },
    )
    assert job.status_code == 200

    lookup = client.post(
        "/api/v1/inventory/scan/process",
        json={"scan_code": "SCN-01-001", "action": "lookup"},
    )
    assert lookup.status_code == 200
    assert lookup.json()["success"] is True

    moved = client.post(
        "/api/v1/inventory/scan/process",
        json={"scan_code": "SCN-01-001", "action": "move", "zone_id": zone.json()["id"]},
    )
    assert moved.status_code == 200
    assert moved.json()["zone_id"] == zone.json()["id"]

    maintenance = client.post(
        "/api/v1/inventory/scan/process",
        json={
            "scan_code": "SCN-01-001",
            "action": "maintenance",
            "maintenance_type": "inspection",
            "interval_mode": "calendar",
            "interval_value": 90,
        },
    )
    assert maintenance.status_code == 200
    assert maintenance.json()["success"] is True

    outtake = client.post(
        "/api/v1/inventory/scan/process",
        json={"scan_code": "SCN-01-001", "action": "job_out", "job_code": "JOB-SCAN-001"},
    )
    assert outtake.status_code == 200
    assert outtake.json()["job_id"] == job.json()["id"]

    intake = client.post(
        "/api/v1/inventory/scan/process",
        json={"scan_code": "SCN-01-001", "action": "job_in", "job_code": "JOB-SCAN-001"},
    )
    assert intake.status_code == 200

    bulk_reqs = client.put(
        f"/api/v1/jobs/{job.json()['id']}/requirements/bulk",
        json={"items": [{"product_id": product_id, "quantity_required": 5, "quantity_picked": 1}]},
    )
    assert bulk_reqs.status_code == 200
    assert len(bulk_reqs.json()) == 1
    assert bulk_reqs.json()[0]["quantity_required"] == 5


def test_inventory_bulk_delete_locations(client):
    # Create parent zone
    parent = client.post(
        "/api/v1/inventory/zones",
        json={"code": "BD-PARENT", "name": "Bulk Delete Parent", "zone_type": "room", "sort_order": 0, "is_active": True},
    )
    assert parent.status_code == 200
    parent_id = parent.json()["id"]

    # Create two child zones
    child1 = client.post(
        "/api/v1/inventory/zones",
        json={"code": "BD-CHILD1", "name": "Bulk Delete Child 1", "zone_type": "rack", "parent_id": parent_id, "sort_order": 0, "is_active": True},
    )
    assert child1.status_code == 200
    child1_id = child1.json()["id"]

    child2 = client.post(
        "/api/v1/inventory/zones",
        json={"code": "BD-CHILD2", "name": "Bulk Delete Child 2", "zone_type": "rack", "parent_id": parent_id, "sort_order": 1, "is_active": True},
    )
    assert child2.status_code == 200
    child2_id = child2.json()["id"]

    # Create a standalone zone to delete
    standalone = client.post(
        "/api/v1/inventory/zones",
        json={"code": "BD-STANDALONE", "name": "Bulk Delete Standalone", "zone_type": "room", "sort_order": 0, "is_active": True},
    )
    assert standalone.status_code == 200
    standalone_id = standalone.json()["id"]

    # Deleting parent when only one child is in the delete set should skip parent
    result = client.post(
        "/api/v1/inventory/locations/bulk-delete",
        json={"ids": [parent_id, child1_id]},
    )
    assert result.status_code == 200
    data = result.json()
    # parent is skipped because child2 is not in the delete set
    assert data["deleted"] == 1
    assert data["skipped"] == 1

    # Deleting parent together with ALL remaining children should succeed
    result2 = client.post(
        "/api/v1/inventory/locations/bulk-delete",
        json={"ids": [parent_id, child2_id]},
    )
    assert result2.status_code == 200
    data2 = result2.json()
    assert data2["deleted"] == 2
    assert data2["skipped"] == 0

    # Deleting a standalone zone succeeds
    result3 = client.post(
        "/api/v1/inventory/locations/bulk-delete",
        json={"ids": [standalone_id]},
    )
    assert result3.status_code == 200
    assert result3.json()["deleted"] == 1


def test_inventory_bulk_delete_locations_skips_zones_with_devices(client):
    # Create a zone
    zone = client.post(
        "/api/v1/inventory/zones",
        json={"code": "BD-DEV-ZONE", "name": "Zone With Device", "zone_type": "rack", "sort_order": 0, "is_active": True},
    )
    assert zone.status_code == 200
    zone_id = zone.json()["id"]

    # Create a product and attach a device to the zone
    product = client.post(
        "/api/v1/inventory/products",
        json={"sku": "BD-DEV-SKU", "name": "BD Test Product", "category": "audio", "product_type": "equipment"},
    )
    assert product.status_code == 200
    product_id = product.json()["id"]

    device = client.post(
        "/api/v1/inventory/devices",
        json={
            "product_id": product_id,
            "asset_tag": "BD-DEV-001",
            "location_zone_id": zone_id,
            "status": "available",
            "condition": "good",
        },
    )
    assert device.status_code == 200

    # Trying to bulk-delete the zone that has a linked device should skip it
    result = client.post(
        "/api/v1/inventory/locations/bulk-delete",
        json={"ids": [zone_id]},
    )
    assert result.status_code == 200
    data = result.json()
    assert data["deleted"] == 0
    assert data["skipped"] == 1


def test_inventory_bulk_create_subzones(client):
    # Create a parent zone
    parent = client.post(
        "/api/v1/inventory/zones",
        json={"code": "BCS-PARENT", "name": "Bulk Create Subzones Parent", "zone_type": "room", "sort_order": 0, "is_active": True},
    )
    assert parent.status_code == 200
    parent_id = parent.json()["id"]

    # Bulk create subzones
    result = client.post(
        f"/api/v1/inventory/locations/{parent_id}/subzones/bulk",
        json=[
            {"code": "BCS-A", "name": "Subzone A", "zone_type": "rack", "sort_order": 0, "is_active": True},
            {"code": "BCS-B", "name": "Subzone B", "zone_type": "rack", "sort_order": 1, "is_active": True},
        ],
    )
    assert result.status_code == 200
    created = result.json()
    assert len(created) == 2
    codes = {z["code"] for z in created}
    assert codes == {"BCS-A", "BCS-B"}
    for zone in created:
        assert zone["parent_id"] == parent_id


def test_inventory_bulk_create_subzones_conflict_within_payload(client):
    # Create a parent zone
    parent = client.post(
        "/api/v1/inventory/zones",
        json={"code": "BCS-DUP-PARENT", "name": "Bulk Create Dup Parent", "zone_type": "room", "sort_order": 0, "is_active": True},
    )
    assert parent.status_code == 200
    parent_id = parent.json()["id"]

    # Payload with duplicate codes should return 409
    result = client.post(
        f"/api/v1/inventory/locations/{parent_id}/subzones/bulk",
        json=[
            {"code": "BCS-DUP", "name": "Subzone Dup 1", "zone_type": "rack", "sort_order": 0, "is_active": True},
            {"code": "BCS-DUP", "name": "Subzone Dup 2", "zone_type": "rack", "sort_order": 1, "is_active": True},
        ],
    )
    assert result.status_code == 409
    detail = result.json()["detail"]
    assert detail["conflicts"] == ["BCS-DUP"]


def test_inventory_bulk_create_subzones_conflict_with_existing(client):
    # Create a parent zone
    parent = client.post(
        "/api/v1/inventory/zones",
        json={"code": "BCS-EX-PARENT", "name": "Bulk Create Existing Parent", "zone_type": "room", "sort_order": 0, "is_active": True},
    )
    assert parent.status_code == 200
    parent_id = parent.json()["id"]

    # Create an existing zone with a code that will conflict
    client.post(
        "/api/v1/inventory/zones",
        json={"code": "BCS-EXISTING", "name": "Existing Zone", "zone_type": "rack", "sort_order": 0, "is_active": True},
    )

    # Trying to bulk-create a subzone with the same code should return 409
    result = client.post(
        f"/api/v1/inventory/locations/{parent_id}/subzones/bulk",
        json=[
            {"code": "BCS-EXISTING", "name": "Conflicting Subzone", "zone_type": "rack", "sort_order": 0, "is_active": True},
        ],
    )
    assert result.status_code == 409
    detail = result.json()["detail"]
    assert "BCS-EXISTING" in detail["conflicts"]


def test_inventory_bulk_create_subzones_parent_not_found(client):
    result = client.post(
        "/api/v1/inventory/locations/999999/subzones/bulk",
        json=[
            {"code": "BCS-NOTFOUND", "name": "Subzone", "zone_type": "rack", "sort_order": 0, "is_active": True},
        ],
    )
    assert result.status_code == 404

def test_bulk_delete_products_skips_when_linked_devices_and_flag_false(client):
    product = client.post(
        "/api/v1/inventory/products",
        json={"sku": "BDP-SKIP-01", "name": "Bulk Delete Skip Product", "daily_rate": "10.00"},
    )
    assert product.status_code == 200
    product_id = product.json()["id"]

    device = client.post(
        "/api/v1/inventory/devices",
        json={"product_id": product_id, "asset_tag": "BDP-SKIP-01-001", "status": "available", "condition": "good"},
    )
    assert device.status_code == 200

    result = client.post(
        "/api/v1/inventory/products/bulk-delete",
        json={"ids": [product_id]},
    )
    assert result.status_code == 200
    assert result.json()["deleted"] == 0
    assert result.json()["skipped"] == 1

    # Verify product still exists in list
    products_list = client.get("/api/v1/inventory/products")
    assert any(p["id"] == product_id for p in products_list.json())


def test_bulk_delete_products_cascades_devices_and_requirements(client):
    product = client.post(
        "/api/v1/inventory/products",
        json={"sku": "BDP-CASCADE-01", "name": "Bulk Delete Cascade Product", "daily_rate": "10.00"},
    )
    assert product.status_code == 200
    product_id = product.json()["id"]

    device = client.post(
        "/api/v1/inventory/devices",
        json={"product_id": product_id, "asset_tag": "BDP-CASCADE-01-001", "status": "available", "condition": "good"},
    )
    assert device.status_code == 200
    device_id = device.json()["id"]

    customer = client.post("/api/v1/customers", json={"name": "Cascade Customer", "email": "cascade@example.com"})
    assert customer.status_code == 200
    venue = client.post("/api/v1/venues", json={"name": "Cascade Venue", "city": "Stockholm"})
    assert venue.status_code == 200
    job = client.post(
        "/api/v1/jobs",
        json={
            "job_code": "JOB-CASCADE-001",
            "customer_id": customer.json()["id"],
            "venue_id": venue.json()["id"],
            "status": "confirmed",
        },
    )
    assert job.status_code == 200

    bulk_reqs = client.put(
        f"/api/v1/jobs/{job.json()['id']}/requirements/bulk",
        json={"items": [{"product_id": product_id, "quantity_required": 2, "quantity_picked": 0}]},
    )
    assert bulk_reqs.status_code == 200
    assert len(bulk_reqs.json()) == 1

    result = client.post(
        "/api/v1/inventory/products/bulk-delete?delete_linked_devices=true",
        json={"ids": [product_id]},
    )
    assert result.status_code == 200
    assert result.json()["deleted"] == 1
    assert result.json()["skipped"] == 0

    # Verify product and device are deleted (not present in list)
    products_list = client.get("/api/v1/inventory/products")
    assert not any(p["id"] == product_id for p in products_list.json())
    devices_list = client.get("/api/v1/inventory/devices")
    assert not any(d["id"] == device_id for d in devices_list.json())

    # Verify linked job requirements are also deleted
    reqs_list = client.get("/api/v1/jobs/requirements")
    assert not any(r["product_id"] == product_id for r in reqs_list.json())


def test_hirehop_preset_endpoint_returns_mapping(client):
    result = client.get("/api/v1/inventory/import/presets/hirehop")
    assert result.status_code == 200
    data = result.json()
    assert isinstance(data, dict)
    assert "product" in data, "Preset must contain a 'product' mapping"
    assert "device" in data, "Preset must contain a 'device' mapping"
    assert isinstance(data["product"], dict), "'product' mapping must be a dict"
    assert isinstance(data["device"], dict), "'device' mapping must be a dict"
    assert data["product"].get("daily_rate") == "PRICE1", "Product mapping must map daily_rate to PRICE1"
    assert data["product"].get("rental_price") == "PRICE2", "Product mapping must map rental_price to PRICE2"


def test_import_inventory_dry_run(client):
    hirehop_data = json.dumps([
        {
            "ID": 101,
            "TITLE": "Test Speaker",
            "REPLACE_COST": 1000,
            "PRICE1": 25.00,
            "PRICE2": 15.00,
            "serialnumbers": [
                {"id": 1, "cell": {"SERIAL": "SN-001", "QTY": 1}},
            ],
        }
    ]).encode()
    result = client.post(
        "/api/v1/inventory/import?preset=hirehop&dry_run=true",
        files={"file": ("test.json", hirehop_data, "application/json")},
    )
    assert result.status_code == 200
    data = result.json()
    assert "products" in data
    assert "devices" in data
    assert data["products"] >= 1
    sample = data["sample_products"][0]
    assert sample.get("daily_rate") == 25.00, "PRICE1 must map to daily_rate"
    assert sample.get("rental_price") == 15.00, "PRICE2 must map to rental_price"


def test_import_inventory_persist(client):
    hirehop_data = json.dumps([
        {
            "ID": 9901,
            "TITLE": "Imported Speaker",
            "REPLACE_COST": 500.567,
            "serialnumbers": [
                {"id": 11, "cell": {"SERIAL": "SN-IMP-001", "QTY": 1}},
            ],
        }
    ]).encode()
    result = client.post(
        "/api/v1/inventory/import?preset=hirehop&dry_run=false",
        files={"file": ("import.json", hirehop_data, "application/json")},
    )
    assert result.status_code == 200
    data = result.json()
    assert data["created_products"] == 1
    assert data["created_devices"] == 1
    assert float(data["products"][0]["replace_cost"]) == 500.57


def test_import_inventory_invalid_json(client):
    result = client.post(
        "/api/v1/inventory/import?preset=hirehop&dry_run=true",
        files={"file": ("bad.json", b"not valid json", "application/json")},
    )
    assert result.status_code == 400


def test_import_inventory_unsupported_preset(client):
    hirehop_data = json.dumps([{"ID": 1}]).encode()
    result = client.post(
        "/api/v1/inventory/import?preset=other&dry_run=true",
        files={"file": ("test.json", hirehop_data, "application/json")},
    )
    assert result.status_code == 400


def test_import_inventory_preserves_zero_dimensions(client):
    hirehop_data = json.dumps([
        {
            "ID": 1234,
            "TITLE": "Zero-Dimension Product",
            "HEIGHT": 0,
            "WIDTH": 0,
            "LENGTH": 0,
        }
    ]).encode()
    result = client.post(
        "/api/v1/inventory/import?preset=hirehop&dry_run=true",
        files={"file": ("zero-dimensions.json", hirehop_data, "application/json")},
    )
    assert result.status_code == 200
    sample = result.json()["sample_products"][0]
    assert sample["height_cm"] == 0.0
    assert sample["width_cm"] == 0.0
    assert sample["depth_cm"] == 0.0


def test_import_inventory_rejects_oversized_file(client):
    with patch.object(settings, "storage_max_upload_mb", 1):
        large_json = b'{"items": [' + (b'{"ID": 1},' * 120000) + b'{"ID": 2}]}'
        result = client.post(
            "/api/v1/inventory/import?preset=hirehop&dry_run=true",
            files={"file": ("large.json", large_json, "application/json")},
        )
    assert result.status_code == 413
    assert "File exceeds 1MB limit" in result.json()["detail"]
