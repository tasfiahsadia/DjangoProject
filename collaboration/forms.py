from django import forms
from django.utils import timezone

from accounts.models import StudentProfile
from applications.models import Application

from .models import Collaboration


class CollaborationForm(forms.ModelForm):
    class Meta:
        model = Collaboration
        fields = ('title', 'description', 'end_date', 'status')
        labels = {'end_date': 'End date (optional)'}
        help_texts = {
            'status': 'Choose Completed when the work is finished.',
        }
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'end_date': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'
            ),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        end_date = cleaned_data.get('end_date')
        if end_date and end_date < self.instance.start_date:
            raise forms.ValidationError('End date cannot be before the start date.')

        if cleaned_data.get('status') == Collaboration.Status.COMPLETED and not end_date:
            cleaned_data['end_date'] = timezone.localdate()
        return cleaned_data


class AddMemberForm(forms.Form):
    """Dropdown of accepted students who are not yet in this collaboration."""
    student = forms.ModelChoiceField(
        queryset=StudentProfile.objects.none(),
        empty_label='Select an accepted student',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    def __init__(self, *args, collaboration, **kwargs):
        super().__init__(*args, **kwargs)
        field = self.fields['student']
        field.queryset = (
            StudentProfile.objects
            .filter(
                applications__opportunity=collaboration.opportunity,
                applications__status=Application.Status.ACCEPTED,
            )
            .exclude(collaboration_memberships__collaboration=collaboration)
            .select_related('user')
            .distinct()
        )
        field.label_from_instance = (
            lambda s: f'{s.user.get_full_name() or s.user.username} ({s.student_id})'
        )