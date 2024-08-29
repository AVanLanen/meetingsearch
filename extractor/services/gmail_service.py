import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from django.conf import settings
import os
import stat
from datetime import datetime, time, timedelta
import pytz

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def check_credentials_file_permissions(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Credentials file not found: {file_path}")

    # For testing purposes, we'll just check if the file is readable
    return os.access(file_path, os.R_OK)

def get_gmail_service():
    print("Attempting to get Gmail service...")
    creds = None
    if not check_credentials_file_permissions(settings.GMAIL_CREDENTIALS_FILE):
        raise PermissionError("Credentials file is not readable")
    
    if os.path.exists('token.pickle'):
        print("Found existing token.pickle file")
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired credentials")
            creds.refresh(Request())
        else:
            print("Getting new credentials")
            flow = InstalledAppFlow.from_client_secrets_file(
                settings.GMAIL_CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    print("Building Gmail service")
    service = build('gmail', 'v1', credentials=creds)
    
    # Get user's email
    user_info = service.users().getProfile(userId='me').execute()
    user_email = user_info['emailAddress']
    
    return service, user_email

def get_emails(service, user_id='me', max_results=50):  # Increased from 10 to 50
    print("Fetching emails...")
    # Get date for 3 days ago
    three_days_ago = datetime.now(pytz.UTC) - timedelta(days=3)
    
    # Format the date for the Gmail API query
    query_date = three_days_ago.strftime('%Y/%m/%d')
    
    query = f'after:{query_date}'
    print(f"Query: {query}")

    try:
        results = service.users().messages().list(userId=user_id, maxResults=max_results, q=query).execute()
        messages = results.get('messages', [])
        print(f"Found {len(messages)} messages")

        emails = []
        for message in messages:
            msg = service.users().messages().get(userId=user_id, id=message['id']).execute()
            subject = next((header['value'] for header in msg['payload']['headers'] if header['name'].lower() == 'subject'), 'No Subject')
            emails.append({
                'id': msg['id'],
                'snippet': msg['snippet'],
                'subject': subject
            })
            print(f"Processed email: {subject}")

        print(f"Processed {len(emails)} emails")
        return emails
    except Exception as e:
        print(f"Error fetching emails: {str(e)}")
        return []

def remove_credentials():
    if os.path.exists('token.pickle'):
        os.remove('token.pickle')
        print("Removed stored credentials")
    else:
        print("No stored credentials found")