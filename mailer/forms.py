from django import forms
from django.core.exceptions import ValidationError
from .models import EmailTemplate, AppSettings


class CSVUploadForm(forms.Form):
    csv_file = forms.FileField(
        label="Select CSV File",
        help_text="File must be formatted as CSV with columns 'company_name' and 'email'.",
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv,text/csv,application/vnd.ms-excel'
        })
    )

    def clean_csv_file(self):
        uploaded_file = self.cleaned_data['csv_file']
        if not uploaded_file.name.lower().endswith('.csv'):
            raise ValidationError("Invalid file format. Please upload a valid .csv file.")
        if uploaded_file.size > 10 * 1024 * 1024:  # 10 MB limit
            raise ValidationError("File size exceeds maximum allowed size (10 MB).")
        return uploaded_file


class EmailTemplateForm(forms.ModelForm):
    class Meta:
        model = EmailTemplate
        fields = ['subject', 'body']
        widgets = {
            'subject': forms.TextInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'e.g. Inquiry Regarding Software Engineer Opportunities'
            }),
            'body': forms.Textarea(attrs={
                'class': 'form-control font-monospace',
                'rows': 12,
                'placeholder': 'Write your email body here. Use {{ company_name }} for company name.'
            })
        }
        help_texts = {
            'body': 'Tip: You can use {{ company_name }} anywhere in the subject or body to personalize each email.'
        }


class AppSettingsForm(forms.ModelForm):
    class Meta:
        model = AppSettings
        fields = ['sending_mode', 'daily_limit', 'delay_seconds']
        widgets = {
            'sending_mode': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_sending_mode',
            }),
            'daily_limit': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 500,
                'id': 'id_daily_limit',
            }),
            'delay_seconds': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 60,
                'step': '0.5',
                'id': 'id_delay_seconds',
            })
        }
        help_texts = {
            'sending_mode': None,  # we render help inline in template
        }
