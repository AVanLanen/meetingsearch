from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import os.path
from django.conf import settings
from datetime import datetime, timedelta

SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    creds = None
    if os.path.exists('calendar_token.pickle'):
        with open('calendar_token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                settings.GMAIL_CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open('calendar_token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)
    return service

def create_calendar_event(service, event_details):
    # Use the end time provided by OpenAI if it exists
    if 'end' not in event_details or not event_details['end'].get('dateTime'):
        start_datetime = datetime.fromisoformat(event_details['start']['dateTime'].replace('Z', '+00:00'))
        end_datetime = start_datetime + timedelta(hours=1)
        event_details['end'] = {
            'dateTime': end_datetime.isoformat(),
            'timeZone': event_details['start'].get('timeZone', 'UTC')
        }
    else:
        # Ensure the end time is in the correct format
        end_datetime = datetime.fromisoformat(event_details['end']['dateTime'].replace('Z', '+00:00'))
        event_details['end']['dateTime'] = end_datetime.isoformat()

    # Ensure timeZone is set for both start and end
    event_details['start']['timeZone'] = event_details['start'].get('timeZone', 'UTC')
    event_details['end']['timeZone'] = event_details['end'].get('timeZone', 'UTC')

    # Remove any fields that are not part of the Google Calendar API event resource
    allowed_fields = {'summary', 'location', 'description', 'start', 'end', 'attendees', 'reminders'}
    filtered_event_details = {k: v for k, v in event_details.items() if k in allowed_fields}

    event = service.events().insert(calendarId='primary', body=filtered_event_details).execute()
    return event

def delete_calendar_event(service, event_id):
    try:
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        return True
    except Exception as e:
        print(f"Error deleting event from Google Calendar: {str(e)}")
        return False