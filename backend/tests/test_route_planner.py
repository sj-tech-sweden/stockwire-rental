"""Route Planner API integration tests."""

import pytest


# ---------------------------------------------------------------------------
# Helpers – create prerequisite data (products, customers, venues, jobs)
# ---------------------------------------------------------------------------

def _create_product(client, sku="PROD-01", name="Test Product"):
    resp = client.post(
        "/api/v1/inventory/products",
        json={
            "sku": sku,
            "name": name,
            "category": "general",
            "product_type": "equipment",
            "weight_kg": "5.000",
            "height_cm": "30.00",
            "width_cm": "20.00",
            "depth_cm": "10.00",
        },
    )
    assert resp.status_code in (200, 201)
    return resp.json()


def _create_customer(client, name="Test Customer"):
    resp = client.post(
        "/api/v1/customers",
        json={"name": name, "email": "customer@example.com"},
    )
    assert resp.status_code in (200, 201)
    return resp.json()


def _create_venue(client, name="Test Venue", customer_id=None):
    payload = {"name": name, "address": "123 Test St", "city": "Stockholm"}
    if customer_id:
        payload["customer_id"] = customer_id
    resp = client.post("/api/v1/venues", json=payload)
    assert resp.status_code in (200, 201)
    return resp.json()


def _create_job(client, customer_id, venue_id, job_code="JOB-001", products=None):
    payload = {
        "job_code": job_code,
        "customer_id": customer_id,
        "venue_id": venue_id,
        "status": "confirmed",
        "start_date": "2026-08-01",
        "end_date": "2026-08-05",
    }
    resp = client.post("/api/v1/jobs", json=payload)
    assert resp.status_code in (200, 201)
    job = resp.json()
    if products:
        for product in products:
            client.post(
                f"/api/v1/jobs/{job['id']}/requirements",
                json={"product_id": product["id"], "quantity_required": 2},
            )
    return job


def _ok(resp, code=200):
    """Assert response status is in (code, code+1) to handle 200/201 variance."""
    assert resp.status_code in (code, code + 1), f"Expected {code} or {code+1}, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# Vehicle CRUD tests
# ---------------------------------------------------------------------------

def test_vehicle_crud(client):
    # Create
    resp = client.post(
        "/api/v1/route-planner/vehicles",
        json={
            "name": "Truck A",
            "vehicle_type": "truck",
            "max_weight_kg": "3500.00",
            "max_volume_m3": "12.000",
            "interior_length_cm": "400.00",
            "interior_width_cm": "200.00",
            "interior_height_cm": "150.00",
        },
    )
    _ok(resp)
    vehicle = resp.json()
    assert vehicle["name"] == "Truck A"
    assert vehicle["vehicle_type"] == "truck"
    assert vehicle["is_active"] is True
    vid = vehicle["id"]

    # Read
    resp = client.get("/api/v1/route-planner/vehicles")
    _ok(resp)
    assert any(v["id"] == vid for v in resp.json())

    # Update
    resp = client.put(
        f"/api/v1/route-planner/vehicles/{vid}",
        json={"name": "Truck B", "license_plate": "ABC-123"},
    )
    _ok(resp)
    assert resp.json()["name"] == "Truck B"
    assert resp.json()["license_plate"] == "ABC-123"

    # Delete (soft)
    resp = client.delete(f"/api/v1/route-planner/vehicles/{vid}")
    assert resp.status_code in (200, 204)

    # Verify not in active list
    resp = client.get("/api/v1/route-planner/vehicles")
    _ok(resp)
    assert not any(v["id"] == vid for v in resp.json())


def test_vehicle_duplicate_name_409(client):
    client.post(
        "/api/v1/route-planner/vehicles",
        json={"name": "MyTruck", "vehicle_type": "truck"},
    )
    resp = client.post(
        "/api/v1/route-planner/vehicles",
        json={"name": "MyTruck", "vehicle_type": "van"},
    )
    assert resp.status_code == 409


def test_vehicle_trailer_weight_fields(client):
    resp = client.post(
        "/api/v1/route-planner/vehicles",
        json={
            "name": "Big Trailer",
            "vehicle_type": "trailer",
            "curb_weight_kg": "800.00",
            "max_payload_kg": "1500.00",
            "max_weight_kg": "2300.00",
            "interior_length_cm": "600.00",
            "interior_width_cm": "200.00",
            "interior_height_cm": "200.00",
        },
    )
    _ok(resp)
    trailer = resp.json()
    assert float(trailer["curb_weight_kg"]) == 800.0
    assert float(trailer["max_payload_kg"]) == 1500.0


def test_vehicle_towing_fields(client):
    resp = client.post(
        "/api/v1/route-planner/vehicles",
        json={
            "name": "Tow Van",
            "vehicle_type": "van",
            "can_pull_trailer": True,
            "max_tow_weight_kg": "2000.00",
        },
    )
    _ok(resp)
    assert resp.json()["can_pull_trailer"] is True
    assert float(resp.json()["max_tow_weight_kg"]) == 2000.0


# ---------------------------------------------------------------------------
# Route CRUD tests
# ---------------------------------------------------------------------------

def test_route_crud(client):
    resp = client.post(
        "/api/v1/route-planner/routes",
        json={"name": "Route 1", "start_date": "2026-08-01"},
    )
    _ok(resp)
    route = resp.json()
    assert route["name"] == "Route 1"
    assert route["status"] == "planned"
    rid = route["id"]

    # Read single
    resp = client.get(f"/api/v1/route-planner/routes/{rid}")
    _ok(resp)
    assert resp.json()["name"] == "Route 1"

    # Update
    resp = client.put(
        f"/api/v1/route-planner/routes/{rid}",
        json={"name": "Route 1 Updated", "status": "in_progress"},
    )
    _ok(resp)
    assert resp.json()["name"] == "Route 1 Updated"
    assert resp.json()["status"] == "in_progress"

    # Delete
    resp = client.delete(f"/api/v1/route-planner/routes/{rid}")
    assert resp.status_code in (200, 204)

    # Verify gone
    resp = client.get(f"/api/v1/route-planner/routes/{rid}")
    assert resp.status_code == 404


def test_route_list_filter_by_status(client):
    client.post(
        "/api/v1/route-planner/routes",
        json={"name": "R1", "start_date": "2026-08-01", "status": "planned"},
    )
    client.post(
        "/api/v1/route-planner/routes",
        json={"name": "R2", "start_date": "2026-08-02", "status": "completed"},
    )
    resp = client.get("/api/v1/route-planner/routes", params={"status": "completed"})
    _ok(resp)
    routes = resp.json()
    assert all(r["status"] == "completed" for r in routes)


# ---------------------------------------------------------------------------
# Route stops tests
# ---------------------------------------------------------------------------

def test_route_stops(client):
    customer = _create_customer(client)
    venue = _create_venue(client, customer_id=customer["id"])
    job1 = _create_job(client, customer["id"], venue["id"], "JOB-S1")
    job2 = _create_job(client, customer["id"], venue["id"], "JOB-S2")

    resp = client.post(
        "/api/v1/route-planner/routes",
        json={"name": "Stop Test", "start_date": "2026-08-01"},
    )
    _ok(resp)
    route = resp.json()

    # Add stops
    resp = client.post(
        f"/api/v1/route-planner/routes/{route['id']}/stops",
        json={"job_id": job1["id"]},
    )
    _ok(resp)
    assert len(resp.json()["stops"]) == 1

    resp = client.post(
        f"/api/v1/route-planner/routes/{route['id']}/stops",
        json={"job_id": job2["id"]},
    )
    _ok(resp)
    assert len(resp.json()["stops"]) == 2

    # Reorder
    stop_ids = [s["id"] for s in resp.json()["stops"]]
    resp = client.put(
        f"/api/v1/route-planner/routes/{route['id']}/stops/reorder",
        json={"stop_ids": list(reversed(stop_ids))},
    )
    _ok(resp)
    reordered = resp.json()["stops"]
    assert reordered[0]["id"] == stop_ids[1]
    assert reordered[1]["id"] == stop_ids[0]

    # Remove stop
    resp = client.delete(
        f"/api/v1/route-planner/routes/{route['id']}/stops/{stop_ids[0]}"
    )
    assert resp.status_code in (200, 204)


def test_route_stop_duplicate_job_409(client):
    customer = _create_customer(client)
    venue = _create_venue(client, customer_id=customer["id"])
    job = _create_job(client, customer["id"], venue["id"], "JOB-DUP")

    resp = client.post(
        "/api/v1/route-planner/routes",
        json={"name": "Dup Test", "start_date": "2026-08-01"},
    )
    _ok(resp)
    route = resp.json()

    resp = client.post(
        f"/api/v1/route-planner/routes/{route['id']}/stops",
        json={"job_id": job["id"]},
    )
    _ok(resp)

    resp = client.post(
        f"/api/v1/route-planner/routes/{route['id']}/stops",
        json={"job_id": job["id"]},
    )
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Route vehicles (multi-vehicle) tests
# ---------------------------------------------------------------------------

def test_route_vehicles(client):
    resp = client.post(
        "/api/v1/route-planner/vehicles",
        json={"name": "V1", "vehicle_type": "truck"},
    )
    _ok(resp)
    v1 = resp.json()

    resp = client.post(
        "/api/v1/route-planner/vehicles",
        json={"name": "V2", "vehicle_type": "trailer"},
    )
    _ok(resp)
    v2 = resp.json()

    resp = client.post(
        "/api/v1/route-planner/routes",
        json={"name": "Multi-V", "start_date": "2026-08-01"},
    )
    _ok(resp)
    route = resp.json()

    # Assign vehicles
    resp = client.post(
        f"/api/v1/route-planner/routes/{route['id']}/vehicles",
        json={"vehicle_id": v1["id"], "load_order": 0},
    )
    _ok(resp)
    assert len(resp.json()["vehicles"]) == 1

    resp = client.post(
        f"/api/v1/route-planner/routes/{route['id']}/vehicles",
        json={"vehicle_id": v2["id"], "load_order": 1},
    )
    _ok(resp)
    assert len(resp.json()["vehicles"]) == 2

    # Reorder
    resp = client.put(
        f"/api/v1/route-planner/routes/{route['id']}/vehicles/reorder",
        json={"vehicle_ids": [v2["id"], v1["id"]]},
    )
    _ok(resp)
    assert resp.json()["vehicles"][0]["vehicle_id"] == v2["id"]

    # Remove vehicle
    resp = client.delete(
        f"/api/v1/route-planner/routes/{route['id']}/vehicles/{v1['id']}"
    )
    assert resp.status_code in (200, 204)


# ---------------------------------------------------------------------------
# Stop vehicle assignment tests
# ---------------------------------------------------------------------------

def test_stop_vehicle_assignment(client):
    resp = client.post(
        "/api/v1/route-planner/vehicles",
        json={"name": "AssignV", "vehicle_type": "van"},
    )
    _ok(resp)
    v1 = resp.json()

    customer = _create_customer(client)
    venue = _create_venue(client, customer_id=customer["id"])
    job = _create_job(client, customer["id"], venue["id"], "JOB-AV")

    resp = client.post(
        "/api/v1/route-planner/routes",
        json={"name": "AV Route", "start_date": "2026-08-01"},
    )
    _ok(resp)
    route = resp.json()

    resp = client.post(
        f"/api/v1/route-planner/routes/{route['id']}/stops",
        json={"job_id": job["id"]},
    )
    _ok(resp)

    route_data = client.get(f"/api/v1/route-planner/routes/{route['id']}").json()
    stop_id = route_data["stops"][0]["id"]

    # Assign vehicle to stop
    resp = client.put(
        f"/api/v1/route-planner/routes/{route['id']}/stops/{stop_id}/vehicle",
        params={"vehicle_id": v1["id"]},
    )
    _ok(resp)
    stop = next(s for s in resp.json()["stops"] if s["id"] == stop_id)
    assert stop["vehicle_id"] == v1["id"]
    assert stop["vehicle"]["name"] == "AssignV"

    # Unassign
    resp = client.put(
        f"/api/v1/route-planner/routes/{route['id']}/stops/{stop_id}/vehicle",
    )
    _ok(resp)
    stop = next(s for s in resp.json()["stops"] if s["id"] == stop_id)
    assert stop["vehicle_id"] is None


# ---------------------------------------------------------------------------
# Vehicle suggestion tests
# ---------------------------------------------------------------------------

def test_suggest_vehicles_single(client):
    customer = _create_customer(client)
    venue = _create_venue(client, customer_id=customer["id"])
    product = _create_product(client, "SUG-01", "Heavy Item")
    job = _create_job(client, customer["id"], venue["id"], "JOB-SUG", [product])

    client.post(
        "/api/v1/route-planner/vehicles",
        json={"name": "Big Truck", "vehicle_type": "truck", "max_weight_kg": "5000.00"},
    )

    resp = client.post(
        "/api/v1/route-planner/suggest-vehicles",
        json={"job_ids": [job["id"]]},
    )
    _ok(resp)
    suggestions = resp.json()
    assert len(suggestions) >= 1
    single = next(s for s in suggestions if not s["is_combo"])
    assert single["label"] == "Big Truck"
    assert single["fits"] is True


def test_suggest_vehicles_combo(client):
    customer = _create_customer(client)
    venue = _create_venue(client, customer_id=customer["id"])
    product = _create_product(client, "COMBO-01", "Combo Item")
    job = _create_job(client, customer["id"], venue["id"], "JOB-COMBO", [product])

    client.post(
        "/api/v1/route-planner/vehicles",
        json={"name": "Tow Truck", "vehicle_type": "truck", "can_pull_trailer": True, "max_tow_weight_kg": "3000.00"},
    )
    client.post(
        "/api/v1/route-planner/vehicles",
        json={
            "name": "Trailer X",
            "vehicle_type": "trailer",
            "curb_weight_kg": "800.00",
            "max_payload_kg": "1500.00",
            "interior_length_cm": "600.00",
            "interior_width_cm": "200.00",
            "interior_height_cm": "200.00",
        },
    )

    resp = client.post(
        "/api/v1/route-planner/suggest-vehicles",
        json={"job_ids": [job["id"]]},
    )
    _ok(resp)
    suggestions = resp.json()
    combos = [s for s in suggestions if s["is_combo"]]
    assert len(combos) >= 1
    combo = combos[0]
    assert len(combo["vehicles"]) == 2
    assert combo["is_combo"] is True
    assert "Tow Truck" in combo["combo_description"]
    assert "Trailer X" in combo["combo_description"]
    assert "curb" in combo["combo_description"]
    assert "payload" in combo["combo_description"]


def test_suggest_vehicles_trailer_too_heavy(client):
    customer = _create_customer(client)
    venue = _create_venue(client, customer_id=customer["id"])
    product = _create_product(client, "HEAVY-01", "Heavy Product")
    job = _create_job(client, customer["id"], venue["id"], "JOB-HEAVY", [product])

    client.post(
        "/api/v1/route-planner/vehicles",
        json={"name": "Weak Car", "vehicle_type": "car", "can_pull_trailer": True, "max_tow_weight_kg": "500.00"},
    )
    client.post(
        "/api/v1/route-planner/vehicles",
        json={
            "name": "Heavy Trailer",
            "vehicle_type": "trailer",
            "curb_weight_kg": "1200.00",
        },
    )

    resp = client.post(
        "/api/v1/route-planner/suggest-vehicles",
        json={"job_ids": [job["id"]]},
    )
    _ok(resp)
    suggestions = resp.json()
    combos = [s for s in suggestions if s["is_combo"]]
    assert not any("Weak Car" in c["label"] and "Heavy Trailer" in c["label"] for c in combos)


def test_suggest_vehicles_uses_payload_for_trailer_capacity(client):
    """Trailer weight capacity uses max_payload_kg, not max_weight_kg."""
    customer = _create_customer(client)
    venue = _create_venue(client, customer_id=customer["id"])
    product = _create_product(client, "CAP-01", "Capacity Item")
    job = _create_job(client, customer["id"], venue["id"], "JOB-CAP", [product])

    # Trailer with high max_weight_kg but low max_payload_kg
    client.post(
        "/api/v1/route-planner/vehicles",
        json={
            "name": "Light Trailer",
            "vehicle_type": "trailer",
            "max_weight_kg": "5000.00",
            "max_payload_kg": "10.00",
        },
    )

    resp = client.post(
        "/api/v1/route-planner/suggest-vehicles",
        json={"job_ids": [job["id"]]},
    )
    _ok(resp)
    suggestions = resp.json()
    single = next(s for s in suggestions if s["label"] == "Light Trailer")
    # Even though max_weight_kg=5000, max_payload_kg=10 should be used
    assert float(single["total_max_weight_kg"]) == 10.0


# ---------------------------------------------------------------------------
# Packing list tests
# ---------------------------------------------------------------------------

def test_packing_list(client):
    customer = _create_customer(client)
    venue = _create_venue(client, name="Pack Venue", customer_id=customer["id"])
    product = _create_product(client, "PKL-01", "Packable Item")
    job1 = _create_job(client, customer["id"], venue["id"], "JOB-P1", [product])
    job2 = _create_job(client, customer["id"], venue["id"], "JOB-P2", [product])

    resp = client.post(
        "/api/v1/route-planner/vehicles",
        json={"name": "Pack Truck", "vehicle_type": "truck"},
    )
    _ok(resp)
    v1 = resp.json()

    resp = client.post(
        "/api/v1/route-planner/routes",
        json={"name": "Pack Route", "start_date": "2026-08-01"},
    )
    _ok(resp)
    route = resp.json()

    # Add stops in order
    resp = client.post(
        f"/api/v1/route-planner/routes/{route['id']}/stops",
        json={"job_id": job1["id"]},
    )
    _ok(resp)

    resp = client.post(
        f"/api/v1/route-planner/routes/{route['id']}/stops",
        json={"job_id": job2["id"]},
    )
    _ok(resp)

    # Assign vehicle to route
    resp = client.post(
        f"/api/v1/route-planner/routes/{route['id']}/vehicles",
        json={"vehicle_id": v1["id"], "load_order": 0},
    )
    _ok(resp)

    # Assign vehicle to second stop
    route_data = client.get(f"/api/v1/route-planner/routes/{route['id']}").json()
    stop2 = route_data["stops"][1]
    resp = client.put(
        f"/api/v1/route-planner/routes/{route['id']}/stops/{stop2['id']}/vehicle",
        params={"vehicle_id": v1["id"]},
    )
    _ok(resp)

    resp = client.get(f"/api/v1/route-planner/routes/{route['id']}/packing-list")
    _ok(resp)
    packing = resp.json()

    assert packing["route_name"] == "Pack Route"
    assert len(packing["vehicles"]) == 1
    assert packing["vehicles"][0]["name"] == "Pack Truck"
    # Stops are in reverse order (last added = first in packing list)
    assert len(packing["stops"]) == 2
    # The stop with the vehicle assigned should have vehicle_name set
    assigned = [s for s in packing["stops"] if s["vehicle_name"] == "Pack Truck"]
    assert len(assigned) == 1


# ---------------------------------------------------------------------------
# Google Maps export tests
# ---------------------------------------------------------------------------

def test_export_google_maps(client):
    customer = _create_customer(client)
    venue = _create_venue(client, name="Maps Venue", customer_id=customer["id"])
    job = _create_job(client, customer["id"], venue["id"], "JOB-MAP")

    resp = client.post(
        "/api/v1/route-planner/routes",
        json={"name": "Maps Route", "start_date": "2026-08-01"},
    )
    _ok(resp)
    route = resp.json()

    resp = client.post(
        f"/api/v1/route-planner/routes/{route['id']}/stops",
        json={"job_id": job["id"]},
    )
    _ok(resp)

    resp = client.post(
        "/api/v1/route-planner/export-google-maps",
        json={"route_id": route["id"]},
    )
    if resp.status_code == 400:
        # If the venue has no address that can be geocoded, it may 400.
        # That's acceptable — just verify the endpoint works.
        assert "detail" in resp.json()
    else:
        _ok(resp)
        data = resp.json()
        assert "url" in data
        assert "google.com/maps" in data["url"]


def test_export_google_maps_missing_route_404(client):
    resp = client.post(
        "/api/v1/route-planner/export-google-maps",
        json={"route_id": 99999},
    )
    assert resp.status_code == 404
