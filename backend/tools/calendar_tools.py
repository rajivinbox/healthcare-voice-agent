"""
Calendar tools for appointment management.

Supports two backends:
  1. Google Calendar (when GOOGLE_SERVICE_ACCOUNT_FILE + GOOGLE_CALENDAR_ID are set)
  2. In-memory demo calendar (fallback — data is lost on server restart)
"""
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional
from config import settings

logger = logging.getLogger(__name__)

# ─── In-memory store (demo fallback) ────────────────────────────────────────
_demo_appointments: dict[str, dict] = {}


def _seed_demo_data() -> None:
    """Pre-populate demo calendar with a few sample appointments."""
    if _demo_appointments:
        return
    now = datetime.now()
    samples = [
        {
            "appointment_id": "APT001",
            "patient_id": "P1A2B3",
            "patient_name": "Alice Johnson",
            "provider": "Dr. Smith",
            "datetime": (now + timedelta(days=1, hours=2)).strftime("%Y-%m-%dT%H:%M"),
            "duration_minutes": 30,
            "reason": "Annual checkup",
            "status": "scheduled",
        },
        {
            "appointment_id": "APT002",
            "patient_id": "P4C5D6",
            "patient_name": "Bob Williams",
            "provider": "Dr. Patel",
            "datetime": (now + timedelta(days=1, hours=4)).strftime("%Y-%m-%dT%H:%M"),
            "duration_minutes": 45,
            "reason": "Follow-up consultation",
            "status": "scheduled",
        },
        {
            "appointment_id": "APT003",
            "patient_id": "P7E8F9",
            "patient_name": "Carol Davis",
            "provider": "Dr. Smith",
            "datetime": (now + timedelta(days=2, hours=1)).strftime("%Y-%m-%dT%H:%M"),
            "duration_minutes": 30,
            "reason": "Blood pressure review",
            "status": "scheduled",
        },
    ]
    for s in samples:
        _demo_appointments[s["appointment_id"]] = s


_seed_demo_data()

# ─── Google Calendar helpers ─────────────────────────────────────────────────

def _get_google_service():
    """Build and return an authenticated Google Calendar service."""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds = service_account.Credentials.from_service_account_file(
        settings.google_service_account_file,
        scopes=["https://www.googleapis.com/auth/calendar"],
    )
    return build("calendar", "v3", credentials=creds)


def _parse_dt(dt_str: str) -> datetime:
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse datetime: {dt_str}")


# ─── Public API ──────────────────────────────────────────────────────────────

def list_appointments(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    patient_name: Optional[str] = None,
    provider: Optional[str] = None,
) -> list[dict]:
    """
    List appointments filtered by date range, patient name, or provider.

    Args:
        date_from: ISO date string (YYYY-MM-DD or YYYY-MM-DDTHH:MM), default = today
        date_to:   ISO date string, default = 7 days from now
        patient_name: Optional partial name filter
        provider:     Optional provider name filter

    Returns:
        List of appointment dicts, sorted by datetime
    """
    now = datetime.now()
    from_dt = _parse_dt(date_from) if date_from else now.replace(hour=0, minute=0, second=0)
    to_dt = _parse_dt(date_to) if date_to else from_dt + timedelta(days=7)

    if settings.use_google_calendar:
        return _gcal_list(from_dt, to_dt, patient_name, provider)

    # Demo mode
    results = []
    for appt in _demo_appointments.values():
        if appt["status"] == "cancelled":
            continue
        appt_dt = _parse_dt(appt["datetime"])
        if not (from_dt <= appt_dt <= to_dt):
            continue
        if patient_name and patient_name.lower() not in appt["patient_name"].lower():
            continue
        if provider and provider.lower() not in appt["provider"].lower():
            continue
        results.append(appt)

    results.sort(key=lambda x: x["datetime"])
    logger.info("list_appointments → %d result(s)", len(results))
    return results


def check_availability(date: str, provider: str, duration_minutes: int = 30) -> list[str]:
    """
    Return available time slots for a provider on a given date.

    Args:
        date: Date string YYYY-MM-DD
        provider: Provider name (e.g. "Dr. Smith")
        duration_minutes: Duration of the requested slot

    Returns:
        List of available ISO datetime strings (YYYY-MM-DDTHH:MM)
    """
    from_dt = _parse_dt(f"{date}T08:00")
    to_dt = _parse_dt(f"{date}T17:00")

    booked_start_times: list[datetime] = []
    for appt in list_appointments(
        date_from=f"{date}T00:00",
        date_to=f"{date}T23:59",
        provider=provider,
    ):
        booked_start_times.append(_parse_dt(appt["datetime"]))

    slots: list[str] = []
    current = from_dt
    while current + timedelta(minutes=duration_minutes) <= to_dt:
        conflict = any(
            abs((current - b).total_seconds()) < duration_minutes * 60
            for b in booked_start_times
        )
        if not conflict:
            slots.append(current.strftime("%Y-%m-%dT%H:%M"))
        current += timedelta(minutes=30)

    logger.info("check_availability %s %s → %d slot(s)", date, provider, len(slots))
    return slots


def book_appointment(
    patient_id: str,
    patient_name: str,
    provider: str,
    appointment_datetime: str,
    reason: str,
    duration_minutes: int = 30,
) -> dict:
    """
    Book a new appointment.

    Returns:
        Created appointment dict including appointment_id
    """
    appt_id = f"APT{str(uuid.uuid4())[:6].upper()}"
    appt = {
        "appointment_id": appt_id,
        "patient_id": patient_id,
        "patient_name": patient_name,
        "provider": provider,
        "datetime": appointment_datetime,
        "duration_minutes": duration_minutes,
        "reason": reason,
        "status": "scheduled",
    }

    if settings.use_google_calendar:
        _gcal_create(appt)
    else:
        _demo_appointments[appt_id] = appt

    logger.info("Appointment booked: %s for %s with %s at %s", appt_id, patient_name, provider, appointment_datetime)
    return appt


def cancel_appointment(appointment_id: str) -> dict:
    """
    Cancel an existing appointment.

    Returns:
        Updated appointment dict with status='cancelled'
    """
    if settings.use_google_calendar:
        return _gcal_cancel(appointment_id)

    appt = _demo_appointments.get(appointment_id.upper())
    if not appt:
        raise ValueError(f"Appointment {appointment_id} not found")
    appt["status"] = "cancelled"
    logger.info("Appointment cancelled: %s", appointment_id)
    return appt


def reschedule_appointment(appointment_id: str, new_datetime: str) -> dict:
    """
    Reschedule an appointment to a new date/time.

    Returns:
        Updated appointment dict
    """
    if settings.use_google_calendar:
        return _gcal_reschedule(appointment_id, new_datetime)

    appt = _demo_appointments.get(appointment_id.upper())
    if not appt:
        raise ValueError(f"Appointment {appointment_id} not found")
    old_dt = appt["datetime"]
    appt["datetime"] = new_datetime
    logger.info("Appointment rescheduled: %s from %s to %s", appointment_id, old_dt, new_datetime)
    return appt


def get_appointment(appointment_id: str) -> Optional[dict]:
    """Fetch a single appointment by ID."""
    if settings.use_google_calendar:
        return _gcal_get(appointment_id)
    return _demo_appointments.get(appointment_id.upper())


# ─── Google Calendar implementation ─────────────────────────────────────────

def _gcal_list(from_dt, to_dt, patient_name, provider) -> list[dict]:
    service = _get_google_service()
    events_result = service.events().list(
        calendarId=settings.google_calendar_id,
        timeMin=from_dt.isoformat() + "Z",
        timeMax=to_dt.isoformat() + "Z",
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    appointments = []
    for event in events_result.get("items", []):
        appt = _gcal_event_to_appt(event)
        if patient_name and patient_name.lower() not in appt["patient_name"].lower():
            continue
        if provider and provider.lower() not in appt["provider"].lower():
            continue
        appointments.append(appt)
    return appointments


def _gcal_create(appt: dict) -> dict:
    service = _get_google_service()
    start = _parse_dt(appt["datetime"])
    end = start + timedelta(minutes=appt["duration_minutes"])
    body = {
        "summary": f"{appt['patient_name']} - {appt['reason']}",
        "description": f"Patient ID: {appt['patient_id']}\nProvider: {appt['provider']}\nReason: {appt['reason']}",
        "start": {"dateTime": start.isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": end.isoformat(), "timeZone": "UTC"},
        "extendedProperties": {
            "private": {
                "appointment_id": appt["appointment_id"],
                "patient_id": appt["patient_id"],
                "patient_name": appt["patient_name"],
                "provider": appt["provider"],
            }
        },
    }
    event = service.events().insert(calendarId=settings.google_calendar_id, body=body).execute()
    appt["gcal_event_id"] = event["id"]
    return appt


def _gcal_cancel(appointment_id: str) -> dict:
    service = _get_google_service()
    event = _gcal_find_event(appointment_id)
    service.events().delete(calendarId=settings.google_calendar_id, eventId=event["id"]).execute()
    return _gcal_event_to_appt(event) | {"status": "cancelled"}


def _gcal_reschedule(appointment_id: str, new_datetime: str) -> dict:
    service = _get_google_service()
    event = _gcal_find_event(appointment_id)
    start = _parse_dt(new_datetime)
    dur = 30
    end = start + timedelta(minutes=dur)
    event["start"] = {"dateTime": start.isoformat(), "timeZone": "UTC"}
    event["end"] = {"dateTime": end.isoformat(), "timeZone": "UTC"}
    updated = service.events().update(
        calendarId=settings.google_calendar_id, eventId=event["id"], body=event
    ).execute()
    return _gcal_event_to_appt(updated)


def _gcal_get(appointment_id: str) -> Optional[dict]:
    try:
        event = _gcal_find_event(appointment_id)
        return _gcal_event_to_appt(event)
    except Exception:
        return None


def _gcal_find_event(appointment_id: str) -> dict:
    service = _get_google_service()
    events = service.events().list(
        calendarId=settings.google_calendar_id,
        privateExtendedProperty=f"appointment_id={appointment_id}",
    ).execute()
    items = events.get("items", [])
    if not items:
        raise ValueError(f"Google Calendar event not found for appointment {appointment_id}")
    return items[0]


def _gcal_event_to_appt(event: dict) -> dict:
    props = event.get("extendedProperties", {}).get("private", {})
    start_str = event.get("start", {}).get("dateTime", "")
    dt = datetime.fromisoformat(start_str.replace("Z", "")) if start_str else datetime.now()
    end_str = event.get("end", {}).get("dateTime", start_str)
    end_dt = datetime.fromisoformat(end_str.replace("Z", "")) if end_str else dt + timedelta(minutes=30)
    duration = int((end_dt - dt).total_seconds() / 60)
    return {
        "appointment_id": props.get("appointment_id", event.get("id", "")),
        "patient_id": props.get("patient_id", ""),
        "patient_name": props.get("patient_name", event.get("summary", "")),
        "provider": props.get("provider", ""),
        "datetime": dt.strftime("%Y-%m-%dT%H:%M"),
        "duration_minutes": duration,
        "reason": event.get("description", ""),
        "status": "cancelled" if event.get("status") == "cancelled" else "scheduled",
    }
