"""Seed default notification templates and preferences."""

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.domain.notifications.models import NotificationTemplate, NotificationPreference

DEFAULT_TEMPLATES = [
    {
        "template_key": "job.created",
        "locale": "en",
        "recipient_type": "both",
        "subject_template": "New job created: {{ job_code }}",
        "html_template": "<h2>New Job Created</h2><p>Job <strong>{{ job_code }}</strong> has been created.</p><p>Customer: {{ customer_name | default('N/A') }}</p><p>Start: {{ start_date | default('N/A') }}</p><p>End: {{ end_date | default('N/A') }}</p>",
        "text_template": "New job created: {{ job_code }}\nCustomer: {{ customer_name | default('N/A') }}\nStart: {{ start_date | default('N/A') }}\nEnd: {{ end_date | default('N/A') }}",
    },
    {
        "template_key": "job.created",
        "locale": "sv",
        "recipient_type": "both",
        "subject_template": "Nytt jobb skapat: {{ job_code }}",
        "html_template": "<h2>Nytt jobb skapat</h2><p>Jobb <strong>{{ job_code }}</strong> har skapats.</p><p>Kund: {{ customer_name | default('Ej angiven') }}</p><p>Start: {{ start_date | default('Ej angiven') }}</p><p>Slut: {{ end_date | default('Ej angiven') }}</p>",
        "text_template": "Nytt jobb skapat: {{ job_code }}\nKund: {{ customer_name | default('Ej angiven') }}\nStart: {{ start_date | default('Ej angiven') }}\nSlut: {{ end_date | default('Ej angiven') }}",
    },
    {
        "template_key": "job.updated",
        "locale": "en",
        "recipient_type": "staff",
        "subject_template": "Job updated: {{ job_code }}",
        "html_template": "<h2>Job Updated</h2><p>Job <strong>{{ job_code }}</strong> has been updated.</p><p>Status: {{ status | default('N/A') }}</p>",
        "text_template": "Job updated: {{ job_code }}\nStatus: {{ status | default('N/A') }}",
    },
    {
        "template_key": "job.updated",
        "locale": "sv",
        "recipient_type": "staff",
        "subject_template": "Jobb uppdaterat: {{ job_code }}",
        "html_template": "<h2>Jobb uppdaterat</h2><p>Jobb <strong>{{ job_code }}</strong> har uppdaterats.</p><p>Status: {{ status | default('Ej angiven') }}</p>",
        "text_template": "Jobb uppdaterat: {{ job_code }}\nStatus: {{ status | default('Ej angiven') }}",
    },
    {
        "template_key": "job.completed",
        "locale": "en",
        "recipient_type": "both",
        "subject_template": "Job completed: {{ job_code }}",
        "html_template": "<h2>Job Completed</h2><p>Job <strong>{{ job_code }}</strong> has been completed.</p><p>Customer: {{ customer_name | default('N/A') }}</p>",
        "text_template": "Job completed: {{ job_code }}\nCustomer: {{ customer_name | default('N/A') }}",
    },
    {
        "template_key": "job.completed",
        "locale": "sv",
        "recipient_type": "both",
        "subject_template": "Jobb slutfört: {{ job_code }}",
        "html_template": "<h2>Jobb slutfört</h2><p>Jobb <strong>{{ job_code }}</strong> har slutförts.</p><p>Kund: {{ customer_name | default('Ej angiven') }}</p>",
        "text_template": "Jobb slutfört: {{ job_code }}\nKund: {{ customer_name | default('Ej angiven') }}",
    },
    {
        "template_key": "maintenance.scheduled",
        "locale": "en",
        "recipient_type": "staff",
        "subject_template": "Maintenance scheduled: {{ device_name }}",
        "html_template": "<h2>Maintenance Scheduled</h2><p>Maintenance for <strong>{{ device_name }}</strong>.</p><p>Type: {{ maintenance_type | default('Scheduled') }}</p><p>Due: {{ due_date | default('N/A') }}</p>",
        "text_template": "Maintenance scheduled: {{ device_name }}\nType: {{ maintenance_type | default('Scheduled') }}\nDue: {{ due_date | default('N/A') }}",
    },
    {
        "template_key": "maintenance.scheduled",
        "locale": "sv",
        "recipient_type": "staff",
        "subject_template": "Underhåll schemalagt: {{ device_name }}",
        "html_template": "<h2>Underhåll schemalagt</h2><p>Underhåll för <strong>{{ device_name }}</strong>.</p><p>Typ: {{ maintenance_type | default('Schemalagt') }}</p><p>Förfaller: {{ due_date | default('Ej angiven') }}</p>",
        "text_template": "Underhåll schemalagt: {{ device_name }}\nTyp: {{ maintenance_type | default('Schemalagt') }}\nFörfaller: {{ due_date | default('Ej angiven') }}",
    },
    {
        "template_key": "defect.reported",
        "locale": "en",
        "recipient_type": "staff",
        "subject_template": "Defect reported: {{ device_name }}",
        "html_template": "<h2>Defect Reported</h2><p>Defect for <strong>{{ device_name }}</strong>.</p><p>Title: {{ title }}</p><p>Severity: {{ severity | default('Medium') }}</p>",
        "text_template": "Defect reported: {{ device_name }}\nTitle: {{ title }}\nSeverity: {{ severity | default('Medium') }}",
    },
    {
        "template_key": "defect.reported",
        "locale": "sv",
        "recipient_type": "staff",
        "subject_template": "Defekt rapporterad: {{ device_name }}",
        "html_template": "<h2>Defekt rapporterad</h2><p>Defekt för <strong>{{ device_name }}</strong>.</p><p>Titel: {{ title }}</p><p>Allvarlighetsgrad: {{ severity | default('Medium') }}</p>",
        "text_template": "Defekt rapporterad: {{ device_name }}\nTitel: {{ title }}\nAllvarlighetsgrad: {{ severity | default('Medium') }}",
    },
]

DEFAULT_PREFERENCES = [
    {"event_type": "job.created", "label": "Job created", "description": "When a new job is created"},
    {"event_type": "job.updated", "label": "Job updated", "description": "When a job is modified"},
    {"event_type": "job.completed", "label": "Job completed", "description": "When a job is marked as completed"},
    {"event_type": "maintenance.scheduled", "label": "Maintenance scheduled", "description": "When maintenance is scheduled"},
    {"event_type": "defect.reported", "label": "Defect reported", "description": "When a defect is reported"},
    {"event_type": "crew.assigned", "label": "Crew assigned", "description": "When crew is assigned to a job"},
    {"event_type": "invoice.sent", "label": "Invoice sent", "description": "When an invoice is sent"},
]


def seed_notification_defaults(db: Session) -> dict[str, int]:
    """Seed default notification templates and preferences. Returns counts."""
    templates_added = 0
    templates_updated = 0
    preferences_added = 0

    # Ensure the old single-column unique constraint is dropped
    try:
        db.execute(text("ALTER TABLE notification_templates DROP CONSTRAINT IF EXISTS ix_notification_templates_template_key"))
        db.flush()
    except Exception:
        pass  # Constraint may not exist or already dropped

    for tpl_data in DEFAULT_TEMPLATES:
        existing = db.query(NotificationTemplate).filter_by(
            template_key=tpl_data["template_key"],
            locale=tpl_data["locale"],
        ).first()
        if existing:
            if not existing.subject_template and tpl_data.get("subject_template"):
                existing.subject_template = tpl_data["subject_template"]
                existing.html_template = tpl_data.get("html_template")
                existing.text_template = tpl_data.get("text_template")
                if hasattr(existing, "recipient_type"):
                    existing.recipient_type = tpl_data.get("recipient_type", "both")
                templates_updated += 1
        else:
            db.add(NotificationTemplate(**tpl_data))
            templates_added += 1

    for pref_data in DEFAULT_PREFERENCES:
        existing = db.query(NotificationPreference).filter_by(
            event_type=pref_data["event_type"],
        ).first()
        if not existing:
            db.add(NotificationPreference(**pref_data))
            preferences_added += 1

    db.commit()
    return {
        "templates_added": templates_added,
        "templates_updated": templates_updated,
        "preferences_added": preferences_added,
    }
