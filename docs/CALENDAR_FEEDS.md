# Calendar Feeds

> Last reviewed: 2026-08-06

## Overview

Calendar Feeds provide ICS (iCalendar) subscriptions for jobs and maintenance schedules, allowing crew members to view assignments in their preferred calendar app.

**Frontend:** Settings → Calendar Feeds  
**Backend:** `/api/v1/calendar/*`

---

## Features

- **Personal Feeds** - Each user gets a unique feed URL
- **Crew Member Feeds** - Individual feeds per crew member
- **Configurable Content** - Include jobs, maintenance, or both
- **Token-Based Access** - Secure URLs with regeneration support
- **Calendar App Compatible** - Works with Google Calendar, Outlook, Apple Calendar

---

## Concepts

### Calendar Feeds

ICS feeds that can be subscribed to:

- Generated per user or crew member
- Unique token for access
- Can include jobs and/or maintenance
- Auto-updates when data changes

### Feed Tokens

Unique identifiers for feed access:

- Used in URL: `/api/v1/calendar/{token}/feed.ics`
- Can be regenerated for security
- No authentication required (token is the credential)

---

## UI Overview

### User Feed

1. Navigate to Settings → Calendar Feeds
2. Click "Get My Feed URL"
3. Copy the generated URL
4. Add to calendar app

### Crew Member Feed

1. Navigate to Crew → Member Details
2. Click "Calendar Feed"
3. Copy the generated URL
4. Share with crew member

### Feed Configuration

1. Open Calendar Feeds settings
2. Toggle options:
   - Include jobs
   - Include maintenance
3. Save changes

### Regenerate Token

1. Open Calendar Feeds settings
2. Click "Regenerate Token"
3. Confirm action
4. Update all calendar subscriptions

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/calendar/{token}/feed.ics` | Get ICS feed (public) |
| `GET` | `/calendar/my-feed` | Get current user's feed URL |
| `GET` | `/calendar/feeds` | List feeds |
| `POST` | `/calendar/feeds` | Create feed |
| `PUT` | `/calendar/feeds/{id}` | Update feed |
| `DELETE` | `/calendar/feeds/{id}` | Delete feed |
| `POST` | `/calendar/feeds/{id}/regenerate-token` | Regenerate token |
| `GET` | `/calendar/crew-member/{id}/feed` | Get crew member's feed |

---

## ICS Feed Format

```ics
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Stockwire Rental//Calendar Feed//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:Stockwire - John Smith

BEGIN:VEVENT
DTSTART:20260807T090000Z
DTEND:20260807T170000Z
SUMMARY:Job - Corporate Event Setup
DESCRIPTION:Setup LED wall and sound system\nVenue: Convention Center\nContact: John Doe
LOCATION:Convention Center, 123 Main St
STATUS:CONFIRMED
UID:job-uuid@stockwire
END:VEVENT

BEGIN:VEVENT
DTSTART:20260808T080000Z
DTEND:20260808T100000Z
SUMMARY:Maintenance - LED Wall Inspection
DESCRIPTION:Quarterly inspection of LED wall components\nDevice: Main LED Wall
STATUS:CONFIRMED
UID:maintenance-uuid@stockwire
END:VEVENT

END:VCALENDAR
```

---

## Data Model

### Calendar Feed

```json
{
  "id": "uuid",
  "name": "John Smith's Feed",
  "token": "a1b2c3d4e5f6",
  "user_id": "uuid",
  "crew_member_id": "uuid",
  "includes_jobs": true,
  "includes_maintenance": true,
  "created_at": "2026-08-06T10:00:00Z"
}
```

---

## Feed Content

### Jobs

Each job becomes a calendar event:

- **Title:** Job code and name
- **Start/End:** Job dates
- **Description:** Job details, requirements
- **Location:** Venue address
- **Status:** Job status

### Maintenance

Each maintenance record becomes an event:

- **Title:** Device name and maintenance type
- **Start:** Scheduled date
- **Duration:** Estimated duration
- **Description:** Maintenance details

---

## Workflow Example

1. **Setup**
   - User navigates to Settings → Calendar Feeds
   - Clicks "Get My Feed URL"
   - Copies URL

2. **Subscribe**
   - Opens Google Calendar
   - Clicks "+" next to "Other calendars"
   - Selects "From URL"
   - Pastes feed URL
   - Calendar events appear

3. **View Assignments**
   - Jobs appear as all-day or timed events
   - Maintenance appears as events
   - Details included in event description

4. **Updates**
   - When job dates change, calendar updates
   - When maintenance is scheduled, event appears
   - Changes reflect within feed refresh interval

---

## Integration with Crew

- Crew members get individual feeds
- Feeds show only their assignments
- Useful for on-site crew without app access
- Can share with subcontractors

---

## Security

- Token-based access (no login required)
- Tokens can be regenerated
- Feeds are read-only
- No sensitive data in feed URLs

---

## Calendar App Compatibility

| App | Support | Notes |
|-----|---------|-------|
| Google Calendar | Full | Auto-refresh every few hours |
| Outlook | Full | May need manual refresh |
| Apple Calendar | Full | Auto-refresh daily |
| Thunderbird | Full | Auto-refresh configurable |
| Samsung Calendar | Partial | May not update automatically |

---

## Limitations

- No real-time updates (depends on calendar app refresh)
- No write-back from calendar to Stockwire
- No attachment support in events
- No color coding by job type
- No recurring event support for maintenance
