import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpRequest
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.core.paginator import Paginator
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db.models import Q
from .models import Contact, EmailTemplate, AppSettings
from .forms import CSVUploadForm, EmailTemplateForm, AppSettingsForm
from .services import import_contacts_from_csv, send_batch_emails, render_template_text


def dashboard(request: HttpRequest):
    total_contacts = Contact.objects.count()
    pending_count = Contact.objects.filter(status=Contact.STATUS_PENDING).count()
    sent_count = Contact.objects.filter(status=Contact.STATUS_SENT).count()
    failed_count = Contact.objects.filter(status=Contact.STATUS_FAILED).count()

    app_settings = AppSettings.get_settings()
    template = EmailTemplate.get_template()
    recent_contacts = Contact.objects.order_by('-updated_at', '-id')[:10]

    # Calculate progress percentages
    sent_pct = round((sent_count / total_contacts * 100), 1) if total_contacts > 0 else 0
    pending_pct = round((pending_count / total_contacts * 100), 1) if total_contacts > 0 else 0
    failed_pct = round((failed_count / total_contacts * 100), 1) if total_contacts > 0 else 0

    context = {
        'total_contacts': total_contacts,
        'pending_count': pending_count,
        'sent_count': sent_count,
        'failed_count': failed_count,
        'sent_pct': sent_pct,
        'pending_pct': pending_pct,
        'failed_pct': failed_pct,
        'daily_limit': app_settings.daily_limit,
        'delay_seconds': app_settings.delay_seconds,
        'app_settings': app_settings,
        'template': template,
        'recent_contacts': recent_contacts,
    }
    return render(request, 'mailer/dashboard.html', context)


def upload_contacts(request: HttpRequest):
    import_result = None

    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            import_result = import_contacts_from_csv(csv_file)
            if import_result['success']:
                messages.success(
                    request,
                    f"Successfully imported {import_result['imported_count']} new contact(s)! "
                    f"({import_result['duplicate_count']} duplicate(s) skipped)."
                )
            else:
                messages.error(request, import_result['error'] or "Failed to import CSV file.")
    else:
        form = CSVUploadForm()

    context = {
        'form': form,
        'import_result': import_result,
    }
    return render(request, 'mailer/upload_contacts.html', context)


def email_template_view(request: HttpRequest):
    template = EmailTemplate.get_template()
    app_settings = AppSettings.get_settings()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'save_template':
            template_form = EmailTemplateForm(request.POST, instance=template)
            settings_form = AppSettingsForm(instance=app_settings)
            if template_form.is_valid():
                template_form.save()
                messages.success(request, "Email template updated successfully.")
                return redirect('mailer:email_template')
        elif action == 'save_settings':
            settings_form = AppSettingsForm(request.POST, instance=app_settings)
            template_form = EmailTemplateForm(instance=template)
            if settings_form.is_valid():
                obj = settings_form.save(commit=False)
                # Auto-apply preset values for Safe / Normal modes
                preset = AppSettings.PRESETS.get(obj.sending_mode)
                if preset:
                    obj.daily_limit = preset['daily_limit']
                    obj.delay_seconds = preset['delay_seconds']
                obj.save()
                mode_label = obj.get_sending_mode_display()
                messages.success(
                    request,
                    f"Sending mode set to {mode_label} — "
                    f"Limit: {obj.daily_limit} emails/day, Delay: {obj.delay_seconds}s between sends."
                )
                return redirect('mailer:email_template')
        else:
            template_form = EmailTemplateForm(instance=template)
            settings_form = AppSettingsForm(instance=app_settings)
    else:
        template_form = EmailTemplateForm(instance=template)
        settings_form = AppSettingsForm(instance=app_settings)

    # Generate sample preview
    sample_company = "Google"
    sample_person = "Hiring Team"
    preview_subject = render_template_text(template.subject, sample_company, sample_person)
    preview_body = render_template_text(template.body, sample_company, sample_person)

    import json
    context = {
        'template_form': template_form,
        'settings_form': settings_form,
        'template': template,
        'app_settings': app_settings,
        'preview_subject': preview_subject,
        'preview_body': preview_body,
        'sample_company': sample_company,
        'mode_presets_json': json.dumps(AppSettings.PRESETS),
        'MODE_SAFE': AppSettings.MODE_SAFE,
        'MODE_NORMAL': AppSettings.MODE_NORMAL,
        'MODE_CUSTOM': AppSettings.MODE_CUSTOM,
    }
    return render(request, 'mailer/email_template.html', context)


def contacts_list(request: HttpRequest):
    status_filter = request.GET.get('status', 'all')
    search_query = request.GET.get('q', '').strip()

    contacts = Contact.objects.all()

    if status_filter in [Contact.STATUS_PENDING, Contact.STATUS_SENT, Contact.STATUS_FAILED]:
        contacts = contacts.filter(status=status_filter)

    if search_query:
        contacts = contacts.filter(
            Q(company_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    contacts = contacts.order_by('-created_at')

    paginator = Paginator(contacts, 25)  # 25 contacts per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'search_query': search_query,
        'total_count': paginator.count,
    }
    return render(request, 'mailer/contacts.html', context)


def reset_failed_contacts(request: HttpRequest):
    if request.method == 'POST':
        from django.utils import timezone as tz
        updated = Contact.objects.filter(status=Contact.STATUS_FAILED).update(
            status=Contact.STATUS_PENDING,
            error_message=None,
            updated_at=tz.now()  # manually set since bulk update() skips auto_now
        )
        messages.success(request, f"Reset {updated} failed contact(s) to Pending status.")
    return redirect('mailer:contacts_list')


def delete_all_contacts(request: HttpRequest):
    """Permanently deletes ALL contacts from the database."""
    if request.method == 'POST':
        confirm = request.POST.get('confirm_delete')
        if confirm == 'DELETE_ALL':
            count, _ = Contact.objects.all().delete()
            messages.success(request, f"All {count} contact(s) have been permanently deleted from the database.")
        else:
            messages.error(request, "Confirmation text did not match. No contacts were deleted.")
    return redirect('mailer:contacts_list')


def add_single_contact(request: HttpRequest):
    """Manually add a single contact to the database."""
    if request.method == 'POST':
        company_name = request.POST.get('company_name', '').strip()
        contact_person = request.POST.get('contact_person', '').strip()
        email = request.POST.get('email', '').strip()

        if not company_name:
            messages.error(request, "Company name is required.")
        elif not email:
            messages.error(request, "Email address is required.")
        else:
            try:
                validate_email(email)
                # Normalize to lowercase for case-insensitive dedup
                email_normalized = email.lower()
                # Use get_or_create with exact field match (email is already unique+indexed)
                contact, created = Contact.objects.get_or_create(
                    email=email_normalized,
                    defaults={
                        'company_name': company_name,
                        'contact_person': contact_person,
                        'status': Contact.STATUS_PENDING,
                    }
                )
                if created:
                    messages.success(request, f"Contact '{company_name} <{email_normalized}>' added successfully!")
                else:
                    messages.warning(request, f"Email '{email_normalized}' already exists in the database (Company: {contact.company_name}).")
            except ValidationError:
                messages.error(request, f"Invalid email address format: '{email}'")
    return redirect('mailer:contacts_list')


def trigger_daily_batch(request: HttpRequest):
    if request.method == 'POST':
        custom_limit = request.POST.get('custom_limit')
        limit = int(custom_limit) if custom_limit and custom_limit.isdigit() else None
        
        summary = send_batch_emails(limit=limit)
        
        if summary['processed_count'] == 0:
            messages.info(request, "No pending contacts found to send emails to.")
        else:
            msg = (
                f"Batch completed! Processed: {summary['processed_count']}, "
                f"Sent: {summary['sent_count']}, Failed: {summary['failed_count']}."
            )
            if summary['failed_count'] > 0:
                messages.warning(request, msg)
            else:
                messages.success(request, msg)
                
    return redirect('mailer:dashboard')


def send_test_email_view(request: HttpRequest):
    if request.method == 'POST':
        test_email = request.POST.get('test_email', '').strip()
        test_company = request.POST.get('test_company', 'Google (Test)').strip() or 'Google (Test)'
        test_person = request.POST.get('test_person', '').strip()

        if not test_email:
            messages.error(request, "Please enter a valid email address to receive the test email.")
            return redirect('mailer:email_template')

        # Validate email format before attempting to send
        try:
            validate_email(test_email)
        except ValidationError:
            messages.error(request, f"Invalid email address format: '{test_email}'")
            return redirect('mailer:email_template')

        template = EmailTemplate.get_template()
        rendered_subject = f"[TEST] " + render_template_text(template.subject, test_company, test_person)
        rendered_body = render_template_text(template.body, test_company, test_person)
        sender = settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER

        try:
            send_mail(
                subject=rendered_subject,
                message=rendered_body,
                from_email=sender,
                recipient_list=[test_email],
                fail_silently=False,
            )
            messages.success(request, f"Test email sent successfully to {test_email}! Please check your Inbox (or Spam folder).")
        except Exception as e:
            messages.error(request, f"Failed to send test email: {str(e)}")

    return redirect('mailer:email_template')


def download_sample_csv(request: HttpRequest):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sample_contacts.csv"'
    writer = csv.writer(response)
    writer.writerow(['company_name', 'contact_person', 'email'])
    writer.writerow(['Google', 'Sundar', 'careers@google.com'])
    writer.writerow(['Microsoft', '', 'hr@microsoft.com'])
    writer.writerow(['Unicommerce eSolutions', 'Gargi', 'gargi.rajan@unicommerce.com'])
    writer.writerow(['Tech Innovators', '', 'talent@techinnovators.io'])
    return response
