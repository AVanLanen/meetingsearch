from django.contrib import admin
from .models import ProcessedEmail, Meeting

admin.site.register(ProcessedEmail)
admin.site.register(Meeting)