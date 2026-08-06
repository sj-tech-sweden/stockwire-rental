# Crew Management

> Last reviewed: 2026-08-06

## Overview

The Crew Management module handles crew members, roles, skills, certifications, and job assignments.

**Frontend:** `/crew` (CrewPage.vue, CrewDetailPage.vue)  
**Backend:** `/api/v1/crew/*`

---

## Features

- **Crew Members** - Manage crew member profiles
- **Roles** - Define crew roles (Technician, Driver, Rigger, etc.)
- **Skills** - Registry of skills crew members can have
- **Certifications** - Track certifications and expiry dates
- **Job Requirements** - Define crew requirements for jobs
- **Assignments** - Assign crew members to jobs
- **Suggestions** - AI-powered crew suggestions based on requirements

---

## Concepts

### Crew Members

Crew members are people who work on jobs:

- Have a primary role
- Can have multiple skills
- Can have multiple certifications
- Can be assigned to multiple jobs
- Have an hourly rate

### Roles

Roles define crew member positions:

- Technician
- Driver
- Rigger
- Project Manager
- etc.

### Skills

Skills are capabilities crew members can have:

- LED Programming
- Forklift Operation
- First Aid
- etc.

### Certifications

Certifications are formal qualifications:

- OSHA 10
- Forklift License
- etc.

---

## UI Overview

### Crew List

1. Navigate to `/crew`
2. View all crew members in a table
3. Click "Add Crew Member" to create new
4. Click row to view details

### Crew Detail

1. Click crew member from list
2. View profile information
3. Edit details in the dialog
4. Manage skills and certifications
5. View assignment history

### Skills Management

1. Go to Settings → Crew → Skills
2. Add new skills
3. Assign skills to crew members

### Certification Management

1. Go to Settings → Crew → Certifications
2. Add certification types
3. Assign to crew members with expiry dates

### Job Crew Requirements

1. Open a job
2. Click "Crew Requirements"
3. Add required roles and skills
4. Set quantity needed

### Crew Assignments

1. Open a job
2. Click "Assign Crew"
3. View suggested crew members
4. Assign to job with role

---

## API Endpoints

### Crew Roles

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/crew/roles` | List roles |
| `POST` | `/crew/roles` | Create role |
| `PUT` | `/crew/roles/{id}` | Update role |
| `DELETE` | `/crew/roles/{id}` | Delete role |

### Skills

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/crew/skills` | List skills |
| `POST` | `/crew/skills` | Create skill |
| `DELETE` | `/crew/skills/{id}` | Delete skill |

### Certifications

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/crew/certifications` | List certifications |
| `POST` | `/crew/certifications` | Create certification |
| `DELETE` | `/crew/certifications/{id}` | Delete certification |

### Crew Members

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/crew/members` | List crew members |
| `GET` | `/crew/members/{id}` | Get member details |
| `POST` | `/crew/members` | Create crew member |
| `PUT` | `/crew/members/{id}` | Update crew member |
| `DELETE` | `/crew/members/{id}` | Delete crew member |

### Job Crew Requirements

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/crew/jobs/{id}/crew-requirements` | Get job requirements |
| `POST` | `/crew/jobs/{id}/crew-requirements` | Add requirement |
| `PUT` | `/crew/jobs/{id}/crew-requirements/{id}` | Update requirement |
| `DELETE` | `/crew/jobs/{id}/crew-requirements/{id}` | Delete requirement |
| `PUT` | `/crew/jobs/{id}/crew-requirements/bulk` | Bulk update |

### Crew Assignments

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/crew/jobs/{id}/crew-assignments` | Get job assignments |
| `POST` | `/crew/assignments` | Create assignment |
| `PUT` | `/crew/assignments/{id}` | Update assignment |
| `DELETE` | `/crew/assignments/{id}` | Delete assignment |
| `GET` | `/crew/jobs/{id}/crew-suggestions` | Get suggestions |

---

## Data Model

### Crew Member

```json
{
  "id": "uuid",
  "name": "John Smith",
  "email": "john@example.com",
  "phone": "+1-555-0123",
  "role_id": "uuid",
  "status": "active",
  "hourly_rate": 45.00,
  "skills": [
    {"id": "uuid", "name": "LED Programming"},
    {"id": "uuid", "name": "Forklift Operation"}
  ],
  "certifications": [
    {"id": "uuid", "name": "OSHA 10", "expires_at": "2027-12-31"}
  ],
  "preferred_roles": ["technician", "rigger"],
  "notes": "Senior technician",
  "created_at": "2026-08-06T10:00:00Z"
}
```

### Job Crew Requirement

```json
{
  "id": "uuid",
  "job_id": "uuid",
  "role_id": "uuid",
  "quantity": 2,
  "required_skills": ["LED Programming", "Forklift Operation"],
  "notes": "Need experienced technicians",
  "created_at": "2026-08-06T10:00:00Z"
}
```

### Crew Assignment

```json
{
  "id": "uuid",
  "job_id": "uuid",
  "crew_member_id": "uuid",
  "role": "technician",
  "start_date": "2026-08-07",
  "end_date": "2026-08-09",
  "hourly_rate": 45.00,
  "notes": "Lead technician",
  "created_at": "2026-08-06T10:00:00Z"
}
```

---

## Workflow Example

1. **Setup Skills & Certifications**
   - Add skills: "LED Programming", "Forklift Operation", "Rigging"
   - Add certifications: "OSHA 10", "Forklift License"

2. **Add Crew Members**
   - Create "John Smith" with role "Technician"
   - Assign skills: LED Programming, Forklift Operation
   - Add certification: OSHA 10 (expires 2027)

3. **Define Job Requirements**
   - Job requires 2 technicians
   - Must have LED Programming skill
   - Must have valid OSHA 10

4. **Get Suggestions**
   - System finds crew with matching skills
   - Checks certification validity
   - Suggests best matches

5. **Assign Crew**
   - Select suggested crew member
   - Assign to job
   - Set dates and rates

6. **Track Completion**
   - Crew completes work
   - Job marked as complete
   - Activity logged

---

## Suggestions Algorithm

The crew suggestion system considers:

1. **Role Match** - Crew member has required role
2. **Skill Match** - Crew member has required skills
3. **Certification Validity** - Certifications are current
4. **Availability** - Not assigned to overlapping jobs
5. **Rate** - Within budget constraints

---

## Integration with Jobs

- Job requirements drive crew suggestions
- Assignments link crew to jobs
- Completion updates job status
- Activity log tracks changes
- Calendar feeds show assignments

---

## Limitations

- No shift scheduling
- No time tracking
- No payroll integration
- No availability calendar view
- No crew performance tracking
