from django.urls import path
from . import views

app_name = 'mailer'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('upload/', views.upload_contacts, name='upload_contacts'),
    path('template/', views.email_template_view, name='email_template'),
    path('contacts/', views.contacts_list, name='contacts_list'),
    path('contacts/reset-failed/', views.reset_failed_contacts, name='reset_failed_contacts'),
    path('contacts/delete-all/', views.delete_all_contacts, name='delete_all_contacts'),
    path('contacts/add/', views.add_single_contact, name='add_single_contact'),
    path('trigger-batch/', views.trigger_daily_batch, name='trigger_daily_batch'),
    path('send-test-email/', views.send_test_email_view, name='send_test_email'),
    path('sample-csv/', views.download_sample_csv, name='download_sample_csv'),
]
