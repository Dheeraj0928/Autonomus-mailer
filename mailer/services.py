import csv
import io
import re
import time
from typing import Dict, Any, List, Optional
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from .models import Contact, EmailTemplate, AppSettings


def normalize_column_name(name: str) -> str:
    """Normalize column header for flexible CSV matching."""
    return re.sub(r'[\s_\-]+', '', name.strip().lower())


def render_template_text(template_text: str, company_name: str) -> str:
    """
    Replace placeholders in email template with actual company name.
    Supports {{ company_name }}, {{company_name}}, {company_name}, etc.
    """
    if not template_text:
        return ""
    # Case-insensitive replacement for {{ company_name }} and {company_name}
    pattern = re.compile(r'\{\{\s*company_name\s*\}\}|\{\s*company_name\s*\}', re.IGNORECASE)
    return pattern.sub(company_name.strip(), template_text)


def import_contacts_from_csv(file_obj) -> Dict[str, Any]:
    """
    Process an uploaded CSV file, validate rows, skip duplicates,
    and save new contacts to the database.
    """
    result = {
        'success': False,
        'total_rows': 0,
        'imported_count': 0,
        'duplicate_count': 0,
        'invalid_rows': [],
        'error': None
    }

    try:
        # Read content and decode handling potential BOMs
        raw_data = file_obj.read()
        for encoding in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
            try:
                text_data = raw_data.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            result['error'] = "Unable to decode CSV file. Please ensure it is saved as UTF-8."
            return result

        reader = csv.reader(io.StringIO(text_data))
        rows = list(reader)

        if not rows:
            result['error'] = "The uploaded CSV file is empty."
            return result

        # Detect header row
        header = rows[0]
        company_idx = None
        email_idx = None

        for idx, col in enumerate(header):
            normalized = normalize_column_name(col)
            if normalized in ['companyname', 'company', 'organization', 'orgname', 'employer']:
                company_idx = idx
            elif normalized in ['email', 'emailaddress', 'mail', 'contactemail', 'hremail']:
                email_idx = idx

        if company_idx is None or email_idx is None:
            result['error'] = (
                "CSV headers not recognized. Your CSV must contain 'company_name' (or 'company') "
                "and 'email' columns in the first row."
            )
            return result

        # Pre-fetch existing emails from DB to minimize database lookups
        existing_emails = set(Contact.objects.values_list('email', flat=True))
        seen_in_file = set()
        contacts_to_create = []

        data_rows = rows[1:]
        result['total_rows'] = len(data_rows)

        for row_num, row in enumerate(data_rows, start=2):
            if not row or not any(cell.strip() for cell in row):
                # Skip empty rows
                continue

            # Extract fields safely
            company_name = row[company_idx].strip() if company_idx < len(row) else ""
            email = row[email_idx].strip() if email_idx < len(row) else ""

            if not company_name:
                result['invalid_rows'].append({
                    'row': row_num,
                    'company_name': company_name,
                    'email': email,
                    'reason': "Missing company name."
                })
                continue

            if not email:
                result['invalid_rows'].append({
                    'row': row_num,
                    'company_name': company_name,
                    'email': email,
                    'reason': "Missing email address."
                })
                continue

            # Validate email format
            try:
                validate_email(email)
            except ValidationError:
                result['invalid_rows'].append({
                    'row': row_num,
                    'company_name': company_name,
                    'email': email,
                    'reason': f"Invalid email format: '{email}'"
                })
                continue

            normalized_email = email.lower()  # normalize for dedup + consistent storage

            # Duplicate check (case-insensitive)
            if normalized_email in existing_emails or normalized_email in seen_in_file:
                result['duplicate_count'] += 1
                continue

            seen_in_file.add(normalized_email)
            contacts_to_create.append(
                Contact(
                    company_name=company_name,
                    email=normalized_email,  # always store lowercase to avoid case-based duplicates
                    status=Contact.STATUS_PENDING
                )
            )

        if contacts_to_create:
            Contact.objects.bulk_create(contacts_to_create)
            result['imported_count'] = len(contacts_to_create)

        result['success'] = True
        return result

    except Exception as e:
        result['error'] = f"An unexpected error occurred while parsing CSV: {str(e)}"
        return result


def send_single_email(contact: Contact, template: EmailTemplate, from_email: Optional[str] = None) -> tuple[bool, Optional[str]]:
    """
    Send an inquiry email to a single Contact using the active EmailTemplate.
    Updates contact state in database.
    """
    rendered_subject = render_template_text(template.subject, contact.company_name)
    rendered_body = render_template_text(template.body, contact.company_name)
    sender = from_email or settings.DEFAULT_FROM_EMAIL

    try:
        send_mail(
            subject=rendered_subject,
            message=rendered_body,
            from_email=sender,
            recipient_list=[contact.email],
            fail_silently=False,
        )
        contact.status = Contact.STATUS_SENT
        contact.sent_at = timezone.now()
        contact.error_message = None
        contact.save(update_fields=['status', 'sent_at', 'error_message', 'updated_at'])
        return True, None
    except Exception as e:
        error_msg = str(e)
        contact.status = Contact.STATUS_FAILED
        contact.error_message = error_msg
        contact.save(update_fields=['status', 'error_message', 'updated_at'])
        return False, error_msg


def send_batch_emails(
    limit: Optional[int] = None,
    delay_override: Optional[float] = None,
    dry_run: bool = False,
    progress_callback=None
) -> Dict[str, Any]:
    """
    Execute daily batch sending for pending contacts.
    Uses a database transaction with select_for_update to prevent race conditions
    (e.g. two simultaneous batch triggers sending the same email twice).
    Returns summary statistics.
    """
    app_settings = AppSettings.get_settings()
    template = EmailTemplate.get_template()

    batch_limit = limit if limit is not None else app_settings.daily_limit
    delay = delay_override if delay_override is not None else app_settings.delay_seconds

    # Use select_for_update inside a transaction to lock rows and prevent double-send
    # when the batch is triggered concurrently (web UI + cron at the same time).
    with transaction.atomic():
        pending_query = (
            Contact.objects
            .select_for_update(skip_locked=True)  # skip rows locked by another process
            .filter(status=Contact.STATUS_PENDING)
            .order_by('created_at', 'id')
        )
        total_pending_available = pending_query.count()
        contacts_to_process = list(pending_query[:batch_limit])

    summary = {
        'total_pending_available': total_pending_available,
        'limit': batch_limit,
        'processed_count': len(contacts_to_process),
        'sent_count': 0,
        'failed_count': 0,
        'dry_run': dry_run,
        'results': []
    }

    for idx, contact in enumerate(contacts_to_process, start=1):
        if dry_run:
            status = "DryRun-Simulated"
            err = None
            summary['sent_count'] += 1
        else:
            success, err = send_single_email(contact, template)
            if success:
                summary['sent_count'] += 1
                status = "Sent"
            else:
                summary['failed_count'] += 1
                status = "Failed"

        item_result = {
            'index': idx,
            'company_name': contact.company_name,
            'email': contact.email,
            'status': status,
            'error': err
        }
        summary['results'].append(item_result)

        if progress_callback:
            progress_callback(item_result, idx, len(contacts_to_process))

        # Throttle between emails if there are more remaining
        if not dry_run and delay > 0 and idx < len(contacts_to_process):
            time.sleep(delay)

    return summary
