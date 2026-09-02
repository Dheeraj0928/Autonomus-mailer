from django.db import models


class Contact(models.Model):
    STATUS_PENDING = 'Pending'
    STATUS_SENT = 'Sent'
    STATUS_FAILED = 'Failed'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_SENT, 'Sent'),
        (STATUS_FAILED, 'Failed'),
    ]

    company_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Contact'
        verbose_name_plural = 'Contacts'

    def __str__(self):
        return f"{self.company_name} ({self.email}) - {self.status}"


class EmailTemplate(models.Model):
    DEFAULT_SUBJECT = "Inquiry Regarding Software Engineer Opportunities"
    DEFAULT_BODY = (
        "Hello Hiring Team at {{ company_name }},\n\n"
        "I hope you are doing well.\n\n"
        "I am a recent engineering graduate currently looking for Software Engineer or fresher-level opportunities. "
        "I wanted to ask if there are any relevant openings available at your company.\n\n"
        "I would be grateful if you could consider my profile for any suitable opportunities.\n\n"
        "Thank you for your time.\n\n"
        "Regards,\n"
        "Dheeraj"
    )

    subject = models.CharField(max_length=255, default=DEFAULT_SUBJECT)
    body = models.TextField(
        default=DEFAULT_BODY,
        help_text="Use {{ company_name }} as a placeholder for the company's name."
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Email Template'
        verbose_name_plural = 'Email Templates'

    def __str__(self):
        return self.subject

    @classmethod
    def get_template(cls):
        """Returns the active email template singleton instance."""
        template, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                'subject': cls.DEFAULT_SUBJECT,
                'body': cls.DEFAULT_BODY,
            }
        )
        return template


class AppSettings(models.Model):
    # Sending mode presets
    MODE_SAFE = 'safe'
    MODE_NORMAL = 'normal'
    MODE_CUSTOM = 'custom'

    MODE_CHOICES = [
        (MODE_SAFE, '🛡️ Safe Mode (Gmail-Friendly)'),
        (MODE_NORMAL, '⚡ Normal Mode'),
        (MODE_CUSTOM, '⚙️ Custom'),
    ]

    # Preset values for each mode
    PRESETS = {
        MODE_SAFE:   {'daily_limit': 30,  'delay_seconds': 3.0},
        MODE_NORMAL: {'daily_limit': 50,  'delay_seconds': 1.5},
    }

    sending_mode = models.CharField(
        max_length=10,
        choices=MODE_CHOICES,
        default=MODE_SAFE,
        help_text="Safe Mode uses Gmail-friendly limits to avoid spam filters."
    )
    daily_limit = models.PositiveIntegerField(
        default=30,
        help_text="Maximum number of emails to dispatch per daily batch."
    )
    delay_seconds = models.FloatField(
        default=3.0,
        help_text="Seconds delay between consecutive emails to prevent rate-limiting."
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'App Settings'
        verbose_name_plural = 'App Settings'

    def __str__(self):
        return f"Settings ({self.get_sending_mode_display()} — Limit: {self.daily_limit}, Delay: {self.delay_seconds}s)"

    @classmethod
    def get_settings(cls):
        """Returns the application settings singleton instance."""
        settings_obj, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                'sending_mode': cls.MODE_SAFE,
                'daily_limit': 30,
                'delay_seconds': 3.0,
            }
        )
        return settings_obj
