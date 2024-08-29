import openai
import json
from django.conf import settings
from datetime import datetime
from zoneinfo import ZoneInfo

openai.api_key = settings.OPENAI_API_KEY

def analyze_email(subject, email_body):
    print("Analyzing email with OpenAI...")
    print(f"Email subject: {subject}")
    print("Email snippet:", email_body[:100] + "..." if len(email_body) > 100 else email_body)
    
    eastern_tz = ZoneInfo("America/New_York")
    current_time = datetime.now(eastern_tz).isoformat()
    full_content = f" Your task is to Extract event/meeting details from the email and format them according to the Google Calendar API event resource schema. Use the provided current system date and time for context when interpreting relative dates and times in the email. Current system date and time (Eastern Time): {current_time}\n\nSubject: {subject}\n\nBody: {email_body}, if an end time is not given, use a default of 1 hour past the start time. Always use Eastern Time (America/New_York) as the timezone for events."
    
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": """You are an event extractor. Your task is to read emails and determine if they are inviting/notifying the user of an event/meeting. If an email doesn't seem like they are inviting or announcing an event, ignore it and do not make details up. 
             Extract event/meeting details from the email and format them according to the Google Calendar API event resource schema. Determine the start and end time based on the email content. If an end time is not explicitly mentioned, make a reasonable estimate based on the type of event."""},
            {"role": "user", "content": full_content}
        ],
        functions=[
            {
                "name": "extract_event_details",
                "description": "Extract event details from an email and format them according to the Google Calendar API event resource schema",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string", "description": "The title of the event"},
                        "location": {"type": "string", "description": "The location of the event"},
                        "description": {"type": "string", "description": "A description of the event"},
                        "start": {
                            "type": "object",
                            "properties": {
                                "dateTime": {"type": "string", "format": "date-time", "description": "The start date and time of the event in ISO 8601 format"},
                                "timeZone": {"type": "string", "description": "The time zone of the start time (always use America/New_York)"}
                            },
                            "required": ["dateTime", "timeZone"]
                        },
                        "end": {
                            "type": "object",
                            "properties": {
                                "dateTime": {"type": "string", "format": "date-time", "description": "The end date and time of the event in ISO 8601 format"},
                                "timeZone": {"type": "string", "description": "The time zone of the end time (always use America/New_York)"}
                            },
                            "required": ["dateTime", "timeZone"]
                        },
                        "attendees": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "email": {"type": "string", "description": "The attendee's email address"}
                                }
                            },
                            "description": "The attendees of the event"
                        },
                        "reminders": {
                            "type": "object",
                            "properties": {
                                "useDefault": {"type": "boolean", "description": "Whether to use the default reminders"},
                                "overrides": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "method": {"type": "string", "description": "The reminder method (email or popup)"},
                                            "minutes": {"type": "integer", "description": "The number of minutes before the event to trigger the reminder"}
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "required": ["summary", "start", "end"]
                }
            }
        ],
        function_call={"name": "extract_event_details"}
    )
    
    function_call = response.choices[0].message.get("function_call")
    
    if function_call:
        print("OpenAI raw response:", function_call.arguments)
        try:
            event_details = json.loads(function_call.arguments)
            print("Parsed event details:", event_details)
            return event_details
        except json.JSONDecodeError:
            print("Failed to parse OpenAI response as JSON. Raw response:", function_call.arguments)
            return None
    else:
        print("OpenAI did not find an event/meeting in this email")
        return None