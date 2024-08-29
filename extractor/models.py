from django.db import models
from django.utils import timezone

class ProcessedEmail(models.Model):
    email_id = models.CharField(max_length=120, unique=True)
    processed_at = models.DateTimeField(default=timezone.now)

class Meeting(models.Model):
    title = models.CharField(max_length=120)
    date = models.DateTimeField()
    end_date = models.DateTimeField()
    created_at = models.DateTimeField(default=timezone.now)
    google_calendar_id = models.CharField(max_length=120, blank=True, null=True)