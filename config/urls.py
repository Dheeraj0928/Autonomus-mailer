"""
URL configuration for JobMail Automator project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('mailer.urls', namespace='mailer')),
]
