from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('process_emails/', views.process_emails, name='process_emails'),
    path('upcoming_meetings/', views.upcoming_meetings, name='upcoming_meetings'),
    path('sign_out/', views.sign_out, name='sign_out'),
    path('delete_meeting/<int:meeting_id>/', views.delete_meeting, name='delete_meeting'),
    path('get_user_email/', views.get_user_email, name='get_user_email'),
    path('mass_delete_meetings/', views.mass_delete_meetings, name='mass_delete_meetings'),
    path('accept_meeting/<int:meeting_index>/', views.accept_meeting, name='accept_meeting'),
    path('reject_meeting/<int:meeting_index>/', views.reject_meeting, name='reject_meeting'),
    path('save_accepted_meetings/', views.save_accepted_meetings, name='save_accepted_meetings'),
    path('get_meeting_details/<int:meeting_index>/', views.get_meeting_details, name='get_meeting_details'),
]