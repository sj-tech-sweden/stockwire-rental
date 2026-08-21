def test_customer_and_job_notification_toggles_are_persisted(client):
    company = client.post(
        "/api/v1/companies",
        json={
            "name": "Notify Company",
            "email_notifications_enabled": False,
        },
    )
    assert company.status_code == 200
    assert company.json()["email_notifications_enabled"] is False

    job = client.post(
        "/api/v1/jobs",
        json={
            "job_code": "JOB-9001",
            "company_id": company.json()["id"],
            "email_notifications_enabled": False,
        },
    )
    assert job.status_code == 200
    assert job.json()["email_notifications_enabled"] is False


def test_profile_notification_channel_can_be_updated(client):
    me_before = client.get("/api/v1/auth/me")
    assert me_before.status_code == 200
    assert me_before.json()["notification_channel"] == "both"

    updated = client.put(
        "/api/v1/auth/me",
        json={
            "email": me_before.json()["email"],
            "full_name": me_before.json()["full_name"],
            "notification_channel": "web_push",
            "password": "",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["notification_channel"] == "web_push"


def test_push_subscription_and_dispatch_logging(client):
    created_user = client.post(
        "/api/v1/auth/users",
        json={
            "email": "staff@example.com",
            "password": "test-pass-123",
            "full_name": "Staff User",
            "role": "manager",
            "notification_channel": "web_push",
            "is_active": True,
        },
    )
    assert created_user.status_code == 201
    user_id = created_user.json()["id"]

    subscription = client.post(
        "/api/v1/notifications/subscriptions",
        json={
            "endpoint": "https://example.com/push/1",
            "keys": {"p256dh": "p256dh-key", "auth": "auth-key"},
            "user_agent": "pytest",
        },
    )
    assert subscription.status_code == 201

    template = client.post(
        "/api/v1/notifications/templates",
        json={
            "template_key": "daily_digest",
            "subject_template": "Digest",
            "text_template": "Hello {{ name }}",
        },
    )
    assert template.status_code == 201

    response = client.post(
        "/api/v1/notifications/dispatch",
        json={
            "template_key": "daily_digest",
            "recipient_type": "staff",
            "recipient_id": user_id,
            "channel": "web_push",
            "context": {"name": "Ops"},
        },
    )
    assert response.status_code == 200
    assert response.json()["results"][0]["channel"] == "web_push"
    assert response.json()["results"][0]["status"] == "skipped_by_preference"

    logs = client.get("/api/v1/notifications/logs")
    assert logs.status_code == 200
    assert any(log["template_key"] == "daily_digest" for log in logs.json())
