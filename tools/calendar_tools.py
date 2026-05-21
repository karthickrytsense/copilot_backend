import os
from datetime import datetime, timedelta
import pytz
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from config import settings


SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _get_calendar_service():
    """Builds and returns an authenticated Google Calendar service using OAuth2."""
    if not settings.GOOGLE_OAUTH_CLIENT_ID or not settings.GOOGLE_OAUTH_CLIENT_SECRET or not settings.GOOGLE_OAUTH_REFRESH_TOKEN:
        raise ValueError(
            "OAuth2 credentials missing. Set GOOGLE_OAUTH_CLIENT_ID, "
            "GOOGLE_OAUTH_CLIENT_SECRET, GOOGLE_OAUTH_REFRESH_TOKEN in .env"
        )

    creds = Credentials(
        token=None,
        refresh_token=settings.GOOGLE_OAUTH_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
        client_secret=settings.GOOGLE_OAUTH_CLIENT_SECRET,
        scopes=SCOPES,
    )

    creds.refresh(Request())
    return build("calendar", "v3", credentials=creds)


def create_calendar_event(
    lead_name: str,
    lead_email: str,
    date: str,
    time: str,
    lead_timezone: str,
) -> dict:
    """
    Creates a Google Calendar event with Google Meet link.
    Invites both the lead and the owner as attendees.
    Google Calendar sends invite emails to both automatically.

    Args:
        lead_name: Full name of the lead
        lead_email: Email of the lead
        date: Selected date in YYYY-MM-DD format
        time: Selected time in HH:MM (24hr) format
        lead_timezone: IANA timezone string from the lead's browser (e.g. "America/New_York")

    Returns:
        dict with keys: success (bool), event_link (str), meet_link (str), message (str)
    """
    try:
        service = _get_calendar_service()

        lead_tz = pytz.timezone(lead_timezone)
        owner_tz = pytz.timezone(settings.OWNER_TIMEZONE or "Asia/Kolkata")
        duration = settings.MEETING_DURATION_MINUTES or 30

        naive_dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        local_dt = lead_tz.localize(naive_dt)
        end_dt = local_dt + timedelta(minutes=duration)

        owner_start = local_dt.astimezone(owner_tz)
        owner_time_str = owner_start.strftime("%d %b %Y, %I:%M %p")
        owner_tz_name = settings.OWNER_TIMEZONE or "Asia/Kolkata"

        attendees = [{"email": lead_email, "displayName": lead_name}]
        if settings.OWNER_EMAIL:
            attendees.append({"email": settings.OWNER_EMAIL, "displayName": "Rytsense Technologies"})

        event = {
            "summary": f"Meeting with {lead_name} - Rytsense Technologies",
            "description": (
                f"Discovery call with {lead_name}.\n\n"
                f"Lead Email: {lead_email}\n"
                f"Meeting time (Rytsense team): {owner_time_str} {owner_tz_name}\n"
                f"Meeting time (Lead): {date} at {time} {lead_timezone}"
            ),
            "start": {
                "dateTime": local_dt.isoformat(),
                "timeZone": lead_timezone,
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": lead_timezone,
            },
            "attendees": attendees,
            "conferenceData": {
                "createRequest": {
                    "requestId": f"rytsense-{lead_email}-{date}-{time}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 60},
                    {"method": "popup", "minutes": 10},
                ],
            },
        }

        calendar_id = settings.OWNER_CALENDAR_ID or "primary"

        created_event = service.events().insert(
            calendarId=calendar_id,
            body=event,
            conferenceDataVersion=1,
            sendUpdates="all",
        ).execute()

        event_link = created_event.get("htmlLink", "")
        meet_link = (
            created_event.get("conferenceData", {})
            .get("entryPoints", [{}])[0]
            .get("uri", "")
        )

        print(f"[Calendar] Event created: {event_link} | Meet: {meet_link}")

        return {
            "success": True,
            "event_link": event_link,
            "meet_link": meet_link,
            "message": (
                f"Meeting scheduled for {date} at {time} ({lead_timezone}). "
                f"A Google Calendar invite with Meet link has been sent to {lead_email}."
            ),
        }

    except Exception as e:
        import traceback
        print(f"[Calendar] Error creating event: {e}")
        print(f"[Calendar] Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "event_link": "",
            "meet_link": "",
            "message": "Failed to schedule the meeting. Please try again or contact us directly.",
        }
