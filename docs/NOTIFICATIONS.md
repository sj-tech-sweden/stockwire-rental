# Notifications

> Last reviewed: 2026-08-06

## Overview

The Notifications system provides push notifications and email dispatch for job updates, maintenance alerts, and other events.

**Frontend:** Push notification subscriptions  
**Backend:** `/api/v1/notifications/*`

---

## Features

- **Web Push Notifications** - Browser-based push notifications
- **Email Dispatch** - Send emails via SMTP or Resend
- **Templates** - Reusable notification templates
- **Logs** - Track notification history
- **VAPID Authentication** - Secure push notification delivery

---

## Concepts

### Push Subscriptions

Browser push notification registrations:

- Stored per user
- Includes endpoint and keys
- Used for Web Push API delivery

### Notification Templates

Reusable message templates:

- Define subject and body
- Support variable substitution
- Categorized by event type

### Notification Logs

History of sent notifications:

- Track delivery status
- Record timestamps
- Link to entities

---

## Push Notifications

### Setup

1. Browser requests permission
2. User grants permission
3. Browser generates subscription
4. Subscription sent to Stockwire
5. Stockwire stores subscription

### Delivery

1. Event occurs (job assigned, etc.)
2. Backend creates notification
3. Sends push via Web Push API
4. Browser displays notification
5. User clicks to open app

### VAPID Keys

VAPID (Voluntary Application Server Identification):

- Public key: included in frontend
- Private key: stored on backend
- Used to sign push requests

---

## Email Notifications

### SMTP Configuration

```bash
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=user@example.com
SMTP_PASSWORD=password
SMTP_FROM_EMAIL=noreply@stockwire.app
SMTP_FROM_NAME=Stockwire Rental
SMTP_USE_TLS=true
```

### Resend Alternative

```bash
RESEND_API_KEY=re_xxxxx
```

### Email Templates

Templates support HTML and text:

- Subject line
- HTML body
- Text body
- Variable substitution

---

## UI Overview

### Push Subscription

1. Browser prompts for permission
2. User allows notifications
3. Subscription created automatically
4. Managed in Profile → Notifications

### Template Management

1. Navigate to Settings → Notifications → Templates
2. View existing templates
3. Click "Add Template" to create
4. Configure subject, body, variables
5. Save template

### Notification Logs

1. Navigate to Settings → Notifications → Logs
2. View sent notifications
3. Filter by type, status, date
4. Click to view details

---

## API Endpoints

### Push Subscriptions

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/notifications/vapid-public-key` | Get VAPID public key |
| `GET` | `/notifications/subscriptions` | List subscriptions |
| `POST` | `/notifications/subscriptions` | Create subscription |
| `DELETE` | `/notifications/subscriptions/{id}` | Delete subscription |

### Templates

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/notifications/templates` | List templates |
| `POST` | `/notifications/templates` | Create template |
| `PUT` | `/notifications/templates/{id}` | Update template |

### Logs & Dispatch

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/notifications/logs` | List logs |
| `POST` | `/notifications/dispatch` | Send notification |

---

## Data Model

### Push Subscription

```json
{
  "id": "uuid",
  "user_id": "uuid",
  "endpoint": "https://fcm.googleapis.com/...",
  "keys": {
    "p256dh": "...",
    "auth": "..."
  },
  "created_at": "2026-08-06T10:00:00Z"
}
```

### Notification Template

```json
{
  "id": "uuid",
  "name": "Job Assigned",
  "subject": "You've been assigned to job {{job_code}}",
  "body": "Hello {{user_name}},\n\nYou've been assigned to job {{job_code}}: {{job_title}}.\n\nStart: {{start_date}}\nEnd: {{end_date}}\n\nView job: {{job_url}}",
  "type": "job_assignment",
  "channel": "push",
  "created_at": "2026-08-06T10:00:00Z"
}
```

### Notification Log

```json
{
  "id": "uuid",
  "template_id": "uuid",
  "user_id": "uuid",
  "channel": "push",
  "status": "delivered",
  "entity_type": "job",
  "entity_id": "uuid",
  "sent_at": "2026-08-06T10:00:00Z",
  "error": null
}
```

---

## Template Variables

### Job Variables

| Variable | Description |
|----------|-------------|
| `{{job_code}}` | Job code |
| `{{job_title}}` | Job title |
| `{{job_status}}` | Job status |
| `{{start_date}}` | Start date |
| `{{end_date}}` | End date |
| `{{job_url}}` | Link to job |

### User Variables

| Variable | Description |
|----------|-------------|
| `{{user_name}}` | User's name |
| `{{user_email}}` | User's email |
| `{{role}}` | User's role |

### Entity Variables

| Variable | Description |
|----------|-------------|
| `{{entity_type}}` | Entity type |
| `{{entity_name}}` | Entity name |
| `{{entity_url}}` | Link to entity |

---

## Workflow Example

### Job Assignment Notification

1. **Admin assigns crew to job**
   - Crew member selected
   - Assignment created

2. **System triggers notification**
   - Event: `job_assignment`
   - Template: "Job Assigned"
   - Recipient: Assigned crew member

3. **Notification sent**
   - Push notification sent via Web Push
   - Email sent via SMTP

4. **User receives notification**
   - Browser displays push notification
   - Email arrives in inbox

5. **User clicks notification**
   - Opens job detail page
   - Views assignment details

---

## Configuration

### Environment Variables

```bash
# Web Push
WEB_PUSH_VAPID_PUBLIC_KEY=BNx...
WEB_PUSH_VAPID_PRIVATE_KEY=xxx...
WEB_PUSH_VAPID_SUBJECT=mailto:noreply@stockwire.app

# Email
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=user@example.com
SMTP_PASSWORD=password

# Or Resend
RESEND_API_KEY=re_xxxxx
```

### Browser Requirements

- Service Worker support
- Push API support
- Notification permission granted

---

## Limitations

- No SMS notifications
- No in-app notification center
- No notification preferences per event type
- No notification batching/digest
- No notification scheduling
- No notification priority levels
