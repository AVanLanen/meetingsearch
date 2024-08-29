from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from .models import Meeting, ProcessedEmail
from .services.gmail_service import get_gmail_service, get_emails, remove_credentials
from .services.calendar_service import get_calendar_service, create_calendar_event, delete_calendar_event
from .services.openai_service import analyze_email
from django.utils import timezone
import json
from django.core.paginator import Paginator
import html
from django.core.serializers.json import DjangoJSONEncoder
from django.template.loader import render_to_string  # Add this line
from django.middleware.csrf import get_token

def index(request):
    return render(request, 'extractor/index.html')

def upcoming_meetings(request):
    meetings_list = Meeting.objects.order_by('date')
    paginator = Paginator(meetings_list, 8)  # Show 8 meetings per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
        'csrf_token': get_token(request),  # Add this line
    }
    return render(request, 'extractor/partials/meetings_grid.html', context)

@require_http_methods(["POST"])
def process_emails(request):
    gmail_service, user_email = get_gmail_service()
    emails = get_emails(gmail_service)
    potential_meetings = []
    processed_count = 0
    new_meetings_count = 0

    for email in emails:
        if not ProcessedEmail.objects.filter(email_id=email['id']).exists():
            event_details = analyze_email(email['subject'], email['snippet'])
            if event_details:
                potential_meetings.append({
                    'email': {
                        'subject': email['subject'],
                        'snippet': html.escape(email['snippet'])
                    },
                    'event_details': event_details,
                    'accepted': False
                })
                new_meetings_count += 1
            
            ProcessedEmail.objects.create(email_id=email['id'])
            processed_count += 1

    request.session['potential_meetings'] = potential_meetings
    request.session['total_emails'] = len(emails)
    request.session['processed_count'] = processed_count
    request.session['new_meetings_count'] = new_meetings_count

    context = {
        'potential_meetings': potential_meetings,
        'total_meetings': len(potential_meetings),
        'processed_meetings': 0,
        'last_run': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
        'processed_count': processed_count,
        'new_meetings_count': new_meetings_count,
        'total_emails': len(emails),
    }
    
    return render(request, 'extractor/partials/review_modal.html', context)

@require_POST
def accept_meeting(request, meeting_index):
    potential_meetings = request.session.get('potential_meetings', [])
    if 0 <= meeting_index < len(potential_meetings):
        meeting = potential_meetings[meeting_index]
        meeting['accepted'] = True
        request.session['potential_meetings'] = potential_meetings
        
        # Create the meeting in the calendar
        calendar_service = get_calendar_service()
        event = create_calendar_event(calendar_service, meeting['event_details'])
        Meeting.objects.create(
            title=event['summary'],
            date=event['start']['dateTime'],
            end_date=event['end']['dateTime'],
            google_calendar_id=event['id']
        )
    
    return HttpResponse('')  # Return an empty response to remove the card

@require_POST
def reject_meeting(request, meeting_index):
    potential_meetings = request.session.get('potential_meetings', [])
    if 0 <= meeting_index < len(potential_meetings):
        potential_meetings[meeting_index]['accepted'] = False
        request.session['potential_meetings'] = potential_meetings
    
    return HttpResponse('')  # Return an empty response to remove the card

@require_POST
def save_accepted_meetings(request):
    potential_meetings = request.session.get('potential_meetings', [])
    calendar_service = get_calendar_service()
    
    for meeting in potential_meetings:
        if meeting.get('accepted', False):
            event = create_calendar_event(calendar_service, meeting['event_details'])
            Meeting.objects.create(
                title=event['summary'],
                date=event['start']['dateTime'],
                end_date=event['end']['dateTime'],
                google_calendar_id=event['id']
            )
    
    request.session['potential_meetings'] = []
    
    return render(request, 'extractor/partials/meetings_grid.html', 
                  {'page_obj': Meeting.objects.order_by('date')[:8]})

def get_user_email(request):
    _, user_email = get_gmail_service()
    return JsonResponse({'email': user_email})

def sign_out(request):
    remove_credentials()
    return JsonResponse({'status': 'success', 'message': 'Signed out successfully'})

@require_POST
def delete_meeting(request, meeting_id):
    meeting = get_object_or_404(Meeting, id=meeting_id)
    calendar_service = get_calendar_service()
    
    if meeting.google_calendar_id:
        delete_calendar_event(calendar_service, meeting.google_calendar_id)
    meeting.delete()
    
    return upcoming_meetings(request)

@require_POST
@csrf_exempt
def mass_delete_meetings(request):
    try:
        data = json.loads(request.body)
        meeting_ids = data.get('meeting_ids', [])
    except json.JSONDecodeError:
        meeting_ids = request.POST.getlist('meeting_ids[]')

    calendar_service = get_calendar_service()
    
    for meeting_id in meeting_ids:
        try:
            meeting = Meeting.objects.get(id=meeting_id)
            if meeting.google_calendar_id:
                delete_calendar_event(calendar_service, meeting.google_calendar_id)
            meeting.delete()
        except Meeting.DoesNotExist:
            continue
    
    return upcoming_meetings(request)

def get_meeting_details(request, meeting_index):
    potential_meetings = request.session.get('potential_meetings', [])
    if 0 <= meeting_index < len(potential_meetings):
        meeting = potential_meetings[meeting_index]
        return render(request, 'extractor/partials/meeting_details.html', {'meeting': meeting})
    else:
        return HttpResponse("No more meetings")