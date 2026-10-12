"""Regression tests for single-job GET and requirements creation."""
from app.domain.jobs.models import Job


def test_get_single_job(client, db_session):
    job = Job(job_code="SINGLE-1", description="d")
    db_session.add(job)
    db_session.commit()

    # Specific routes must keep working (list of requirements).
    resp = client.get("/api/v1/jobs/requirements")
    assert resp.status_code == 200

    # Single-job GET (was missing -> 405 before).
    resp = client.get(f"/api/v1/jobs/{job.id}")
    assert resp.status_code == 200
    assert resp.json()["job_code"] == "SINGLE-1"

    resp = client.get("/api/v1/jobs/999999")
    assert resp.status_code == 404


def test_create_requirement_requires_a_source(client, db_session):
    job = Job(job_code="SINGLE-2")
    db_session.add(job)
    db_session.commit()

    # Neither product_id nor vendor_product_id -> 422.
    resp = client.post("/api/v1/jobs/requirements", json={"job_id": job.id, "quantity_required": 1})
    assert resp.status_code == 422
