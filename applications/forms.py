from django import forms
from django.core.files.uploadedfile import UploadedFile

from .models import Application, ApplicationAttachment, ApplicationEvaluation

SOP_MIN_LENGTH = 100
MAX_ATTACHMENTS = 5
MAX_FILE_SIZE_MB = 5


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ('sop', 'remarks')
        labels = {
            'sop': 'Statement of purpose (SOP)',
            'remarks': 'Additional remarks (optional)',
        }
        help_texts = {
            'sop': f'Minimum {SOP_MIN_LENGTH} characters.',
        }
        widgets = {
            'sop': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 8,
                'placeholder': (
                    'Example: I am a 5th semester CSE student with experience in '
                    'Python and Django. I want to join this project because I enjoy '
                    'working with data. I have completed the Data Structures course '
                    'and built a small web application. I hope to learn research '
                    'methods and contribute to the team.'
                ),
            }),
            'remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Example: I am free on Sunday and Tuesday afternoons for meetings.',
            }),
        }

    def clean_sop(self):
        sop = self.cleaned_data['sop'].strip()
        if len(sop) < SOP_MIN_LENGTH:
            raise forms.ValidationError(
                f'Please write at least {SOP_MIN_LENGTH} characters (you wrote {len(sop)}).'
            )
        return sop


class ApplicationAttachmentForm(forms.ModelForm):
    class Meta:
        model = ApplicationAttachment
        fields = ('title', 'file')
        labels = {
            'title': 'File title',
            'file': 'File',
        }
        help_texts = {
            'file': f'PDF, DOC, DOCX, ZIP, JPG or PNG. Maximum {MAX_FILE_SIZE_MB} MB.',
        }
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Transcript, Project report, Certificate',
            }),
            'file': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.zip,.jpg,.jpeg,.png',
            }),
        }

    def __init__(self, *args, application, **kwargs):
        super().__init__(*args, **kwargs)
        self.application = application

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if isinstance(file, UploadedFile) and file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
            raise forms.ValidationError(f'File must be {MAX_FILE_SIZE_MB} MB or smaller.')
        return file

    def clean(self):
        cleaned_data = super().clean()
        if self.application.attachments.count() >= MAX_ATTACHMENTS:
            raise forms.ValidationError(
                f'You can attach at most {MAX_ATTACHMENTS} files to one application.'
            )
        return cleaned_data


class ApplicationEvaluationForm(forms.ModelForm):
    class Meta:
        model = ApplicationEvaluation
        fields = ('score', 'feedback', 'decision')
        labels = {
            'score': 'Score (0 to 10)',
        }
        widgets = {
            'score': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 10,
                'step': 0.5,
                'placeholder': 'e.g. 8.5',
            }),
            'feedback': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': (
                    'Example: Strong Python background and a clear motivation. '
                    'Please bring your transcript to the first meeting.'
                ),
            }),
            'decision': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, application, **kwargs):
        super().__init__(*args, **kwargs)
        self.application = application
        self.fields['decision'].choices = (
            [('', 'Select a decision')] + ApplicationEvaluation.Decision.choices
        )

    def clean(self):
        cleaned_data = super().clean()
        application = self.application

        if application.status == Application.Status.WITHDRAWN:
            raise forms.ValidationError('A withdrawn application cannot be evaluated.')

        if cleaned_data.get('decision') == ApplicationEvaluation.Decision.ACCEPTED:
            # Count the other accepted applications (not this one, so re-evaluation works).
            accepted_count = (
                Application.objects
                .filter(
                    opportunity=application.opportunity,
                    status=Application.Status.ACCEPTED,
                )
                .exclude(pk=application.pk)
                .count()
            )
            positions = application.opportunity.positions
            if accepted_count >= positions:
                raise forms.ValidationError(
                    f'All {positions} position(s) for this opportunity are already filled.'
                )
        return cleaned_data