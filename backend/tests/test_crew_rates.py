"""Tests for crew default-rate seeding and quote letterhead opt-out."""
from app.domain.jobs.models import Job
from app.domain.crew.models import CrewRole, CrewMember
from app.domain.customers.models import Person
from app.domain.quotes.templates import ensure_default_quote_template


def test_quote_template_opts_out_of_letterhead(client, db_session):
    template = ensure_default_quote_template(db_session)
    assert template.use_letterhead is False


def test_requirement_seeds_role_default_hourly_rate(client, db_session):
    role = CrewRole(name="Sound Engineer", default_hourly_rate=850)
    db_session.add(role)
    job = Job(job_code="J-SEED", status="planning")
    db_session.add(job)
    db_session.commit()
    db_session.refresh(role)
    db_session.refresh(job)

    resp = client.post(
        f"/api/v1/crew/jobs/{job.id}/crew-requirements",
        json={"job_id": job.id, "crew_role_id": role.id, "quantity": 2},
    )
    assert resp.status_code == 201, resp.text
    assert float(resp.json()["hourly_rate"]) == 850.0


def test_requirement_respects_explicit_hourly_rate(client, db_session):
    role = CrewRole(name="Lighting Designer", default_hourly_rate=900)
    db_session.add(role)
    job = Job(job_code="J-EXP", status="planning")
    db_session.add(job)
    db_session.commit()
    db_session.refresh(role)
    db_session.refresh(job)

    resp = client.post(
        f"/api/v1/crew/jobs/{job.id}/crew-requirements",
        json={"job_id": job.id, "crew_role_id": role.id, "quantity": 1, "hourly_rate": 500},
    )
    assert resp.status_code == 201, resp.text
    assert float(resp.json()["hourly_rate"]) == 500.0


def test_assignment_seeds_member_hourly_rate(client, db_session):
    role = CrewRole(name="Operator")
    db_session.add(role)
    job = Job(job_code="J-ASN", status="planning")
    db_session.add(job)
    person = Person(first_name="Jane", last_name="Doe")
    db_session.add(person)
    db_session.commit()
    db_session.refresh(person)
    member = CrewMember(person_id=person.id, hourly_rate=1200)
    db_session.add(member)
    db_session.commit()
    db_session.refresh(role)
    db_session.refresh(job)
    db_session.refresh(member)

    req = client.post(
        f"/api/v1/crew/jobs/{job.id}/crew-requirements",
        json={"job_id": job.id, "crew_role_id": role.id, "quantity": 1},
    ).json()
    assert req["hourly_rate"] is None

    assign = client.post(
        "/api/v1/crew/assignments",
        json={"job_crew_requirement_id": req["id"], "crew_member_id": member.id},
    )
    assert assign.status_code == 201, assign.text

    reqs = client.get(f"/api/v1/crew/jobs/{job.id}/crew-requirements").json()
    match = next(r for r in reqs if r["id"] == req["id"])
    assert float(match["hourly_rate"]) == 1200.0


def test_requirement_daily_basis_persists(client, db_session):
    role = CrewRole(name="Stagehand", default_daily_rate=1200)
    db_session.add(role)
    job = Job(job_code="J-DAILY", status="planning")
    db_session.add(job)
    db_session.commit()
    db_session.refresh(role)
    db_session.refresh(job)

    resp = client.post(
        f"/api/v1/crew/jobs/{job.id}/crew-requirements",
        json={
            "job_id": job.id,
            "crew_role_id": role.id,
            "quantity": 2,
            "rate_basis": "daily",
            "daily_rate": None,
            "days": 3,
        },
    )
    assert resp.status_code == 201, resp.text
    req = resp.json()
    # Daily rate should be seeded from the role default.
    assert req["rate_basis"] == "daily"
    assert float(req["daily_rate"]) == 1200.0
    assert float(req["days"]) == 3.0

    reqs = client.get(f"/api/v1/crew/jobs/{job.id}/crew-requirements").json()
    match = next(r for r in reqs if r["id"] == req["id"])
    assert match["rate_basis"] == "daily"
    assert float(match["daily_rate"]) == 1200.0


def test_quote_template_labour_table_has_days_column(client, db_session):
    template = ensure_default_quote_template(db_session)
    import json

    body = json.loads(template.body_json)
    flowables = body.get("flowables", []) if isinstance(body, dict) else body
    labour = next(
        f for f in flowables if f.get("type") == "table" and f.get("source") == "crew_lines"
    )
    keys = {c["key"] for c in labour["columns"]}
    assert "days" in keys
    assert "rate" in keys
    # Old hourly_rate key should have been replaced.
    assert "hourly_rate" not in keys

    # The quote template should be available in both English and Swedish.
    translations = json.loads(template.translations_json or "{}")
    assert "sv" in translations

