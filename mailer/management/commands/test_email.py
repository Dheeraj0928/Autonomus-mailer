from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from mailer.models import EmailTemplate
from mailer.services import render_template_text


class Command(BaseCommand):
    help = "Sends a single test email to your personal address using active template without touching the contacts database."

    def add_arguments(self, parser):
        parser.add_argument(
            'email',
            type=str,
            nargs='?',
            default=settings.EMAIL_HOST_USER,
            help='Recipient email address (defaults to EMAIL_HOST_USER from .env)'
        )
        parser.add_argument(
            '--company',
            type=str,
            default='Google (Test Preview)',
            help='Company name to simulate in the email'
        )

    def handle(self, *args, **options):
        recipient = options['email']
        company_name = options['company']

        if not recipient:
            self.stdout.write(self.style.ERROR("[!] No recipient email specified and EMAIL_HOST_USER is empty in .env"))
            return

        template = EmailTemplate.get_template()
        subject = render_template_text(template.subject, company_name)
        body = render_template_text(template.body, company_name)
        sender = settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER

        self.stdout.write("=" * 60)
        self.stdout.write(self.style.MIGRATE_HEADING("  [*] Sending Test Email..."))
        self.stdout.write("=" * 60)
        self.stdout.write(f"- From      : {sender}")
        self.stdout.write(f"- To        : {recipient}")
        self.stdout.write(f"- Company   : {company_name}")
        self.stdout.write(f"- Subject   : {subject}")
        self.stdout.write("-" * 60)

        try:
            send_mail(
                subject=f"[TEST EMAIL] {subject}",
                message=body,
                from_email=sender,
                recipient_list=[recipient],
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS(f"[OK] Test email sent successfully to {recipient}!"))
            self.stdout.write("Check your Gmail Inbox (or Spam folder).")
            self.stdout.write("=" * 60)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[!] Failed to send test email: {str(e)}"))
            self.stdout.write("=" * 60)
