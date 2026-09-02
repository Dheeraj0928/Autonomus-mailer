from django.core.management.base import BaseCommand
from mailer.services import send_batch_emails
from mailer.models import Contact, AppSettings, EmailTemplate


class Command(BaseCommand):
    help = "Dispatches a daily batch of job inquiry emails to pending contacts based on configured daily limit."

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Override the configured daily limit (e.g. --limit 5 for a test batch).'
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=None,
            help='Override the delay between emails in seconds (e.g. --delay 2.0).'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate the batch dispatch without actually sending emails or updating the database.'
        )

    def handle(self, *args, **options):
        limit_arg = options['limit']
        delay_arg = options['delay']
        dry_run = options['dry_run']

        app_settings = AppSettings.get_settings()
        template = EmailTemplate.get_template()

        limit = limit_arg if limit_arg is not None else app_settings.daily_limit
        delay = delay_arg if delay_arg is not None else app_settings.delay_seconds

        self.stdout.write("=" * 65)
        self.stdout.write(self.style.MIGRATE_HEADING("  [*] JobMail Automator - Daily Batch Email Dispatcher"))
        self.stdout.write("=" * 65)

        if dry_run:
            self.stdout.write(self.style.WARNING("  [DRY RUN MODE ENABLED - No emails will be sent]"))

        total_pending = Contact.objects.filter(status=Contact.STATUS_PENDING).count()
        self.stdout.write(f"- Active Template Subject : {template.subject}")
        self.stdout.write(f"- Total Pending Contacts  : {total_pending}")
        self.stdout.write(f"- Batch Limit for Run     : {limit}")
        self.stdout.write(f"- Delay Between Emails    : {delay}s")
        self.stdout.write("-" * 65)

        if total_pending == 0:
            self.stdout.write(self.style.SUCCESS("[OK] No pending contacts found. All contacts have already been processed!"))
            self.stdout.write("=" * 65)
            return

        def on_progress(item, current_idx, total):
            status_style = self.style.SUCCESS if item['status'] in ['Sent', 'DryRun-Simulated'] else self.style.ERROR
            status_text = f"[{item['status']}]"
            self.stdout.write(
                f"[{current_idx}/{total}] {item['company_name']} <{item['email']}> ... " +
                status_style(status_text)
            )
            if item.get('error'):
                self.stdout.write(self.style.NOTICE(f"    └── Reason: {item['error']}"))

        summary = send_batch_emails(
            limit=limit,
            delay_override=delay,
            dry_run=dry_run,
            progress_callback=on_progress
        )

        self.stdout.write("-" * 65)
        self.stdout.write(self.style.MIGRATE_HEADING("  [#] Batch Execution Summary:"))
        self.stdout.write(f"  - Processed in batch : {summary['processed_count']}")
        self.stdout.write(f"  - Successfully sent  : {self.style.SUCCESS(str(summary['sent_count']))}")
        self.stdout.write(f"  - Failed             : {self.style.ERROR(str(summary['failed_count'])) if summary['failed_count'] > 0 else '0'}")
        
        remaining_pending = Contact.objects.filter(status=Contact.STATUS_PENDING).count()
        self.stdout.write(f"  - Pending remaining  : {remaining_pending}")
        self.stdout.write("=" * 65)

        if summary['failed_count'] > 0:
            self.stdout.write(
                self.style.WARNING("[!] Some emails failed to send. Check your SMTP credentials in .env or the error messages on the dashboard.")
            )
        else:
            self.stdout.write(self.style.SUCCESS("[OK] Daily batch completed successfully!"))
