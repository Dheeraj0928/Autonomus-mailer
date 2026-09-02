import io
from django.test import TestCase, Client
from django.urls import reverse
from django.core import mail
from mailer.models import Contact, EmailTemplate, AppSettings
from mailer.services import import_contacts_from_csv, render_template_text, send_batch_emails


class CSVImportTests(TestCase):
    def test_import_valid_csv(self):
        csv_content = (
            "company_name,email\n"
            "Google,careers@google.com\n"
            "Microsoft,hr@microsoft.com\n"
            "ABC Corp,hr@abccorp.com\n"
        ).encode('utf-8')

        file_obj = io.BytesIO(csv_content)
        result = import_contacts_from_csv(file_obj)

        self.assertTrue(result['success'])
        self.assertEqual(result['imported_count'], 3)
        self.assertEqual(result['duplicate_count'], 0)
        self.assertEqual(Contact.objects.count(), 3)

    def test_duplicate_and_invalid_rows_handling(self):
        # Insert initial contact
        Contact.objects.create(company_name="Google", email="careers@google.com")

        csv_content = (
            "company_name,email\n"
            "Google,careers@google.com\n"  # duplicate of existing in DB
            "Duplicate In File,duplicate@example.com\n"
            "Duplicate In File,duplicate@example.com\n"  # duplicate in same file
            "Invalid Email Company,not-an-email\n"  # invalid email format
            "Valid Company,talent@valid.com\n"
        ).encode('utf-8')

        file_obj = io.BytesIO(csv_content)
        result = import_contacts_from_csv(file_obj)

        self.assertTrue(result['success'])
        self.assertEqual(result['imported_count'], 2)  # 'duplicate@example.com' (first occurrence) and 'talent@valid.com'
        self.assertEqual(result['duplicate_count'], 2)
        self.assertEqual(len(result['invalid_rows']), 1)
        self.assertEqual(result['invalid_rows'][0]['company_name'], "Invalid Email Company")


class TemplateRenderTests(TestCase):
    def test_render_company_name_placeholder(self):
        template_text = "Hello Hiring Team at {{ company_name }},\nWelcome to {{company_name}}!"
        rendered = render_template_text(template_text, "Acme Corp")
        self.assertEqual(rendered, "Hello Hiring Team at Acme Corp,\nWelcome to Acme Corp!")

    def test_render_with_contact_person_name(self):
        template_text = "Hello {{ Name }},\nI want to work at {{ company_name }}."
        rendered = render_template_text(template_text, "Google", "Gargi")
        self.assertEqual(rendered, "Hello Gargi,\nI want to work at Google.")

    def test_render_without_contact_person_name_fallback(self):
        template_text = "Hello {{ Name }},\nI want to work at {{ company_name }}."
        rendered = render_template_text(template_text, "Google", "")
        self.assertEqual(rendered, "Hello,\nI want to work at Google.")



class BatchEmailSendingTests(TestCase):
    def setUp(self):
        self.c1 = Contact.objects.create(company_name="Company A", email="a@example.com", status=Contact.STATUS_PENDING)
        self.c2 = Contact.objects.create(company_name="Company B", email="b@example.com", status=Contact.STATUS_PENDING)
        self.c3 = Contact.objects.create(company_name="Company C", email="c@example.com", status=Contact.STATUS_SENT)

    def test_send_batch_emails(self):
        summary = send_batch_emails(limit=1, delay_override=0)
        self.assertEqual(summary['processed_count'], 1)
        self.assertEqual(summary['sent_count'], 1)

        # First contact should be updated to Sent
        self.c1.refresh_from_db()
        self.assertEqual(self.c1.status, Contact.STATUS_SENT)
        self.assertIsNotNone(self.c1.sent_at)

        # Second contact should still be Pending
        self.c2.refresh_from_db()
        self.assertEqual(self.c2.status, Contact.STATUS_PENDING)

        # Check that email was sent through django test outbox
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['a@example.com'])
        self.assertIn("Company A", mail.outbox[0].body)


class ViewIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_dashboard_view(self):
        response = self.client.get(reverse('mailer:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Campaign Dashboard")

    def test_contacts_view(self):
        Contact.objects.create(company_name="Test Co", email="test@example.com")
        response = self.client.get(reverse('mailer:contacts_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Co")

    def test_template_view(self):
        response = self.client.get(reverse('mailer:email_template'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Email Template & Settings")
