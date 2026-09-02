from django.contrib import admin
from .models import Contact, EmailTemplate, AppSettings


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'email', 'status', 'sent_at', 'created_at')
    list_filter = ('status', 'created_at', 'sent_at')
    search_fields = ('company_name', 'email')
    readonly_fields = ('created_at', 'updated_at')
    actions = ['mark_as_pending']

    @admin.action(description="Reset selected contacts to Pending")
    def mark_as_pending(self, request, queryset):
        count = queryset.update(status=Contact.STATUS_PENDING, error_message=None)
        self.message_user(request, f"{count} contacts were reset to Pending.")


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('subject', 'updated_at')


@admin.register(AppSettings)
class AppSettingsAdmin(admin.ModelAdmin):
    list_display = ('daily_limit', 'delay_seconds', 'updated_at')
