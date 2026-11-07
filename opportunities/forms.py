import os
from django import forms
from django.utils import timezone
from accounts.models import Department
from .models import Opportunity, OpportunityResource

ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.ppt', '.pptx', '.txt', '.zip'}
MAX_FILE_SIZE = 5 * 1024 * 1024

def validate_resource_file(uploaded):
    """Shared check for resource files: allowed type and size."""
    extension = os.path.splitext(uploaded.name)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise forms.ValidationError(
            'Allowed file types: PDF, DOC, DOCX, PPT, PPTX, TXT, ZIP.'
        )
    if uploaded.size > MAX_FILE_SIZE:
        raise forms.ValidationError('File must be 5 MB or smaller.')


class OpportunityForm(forms.ModelForm):
    resource_title = forms.CharField(
        max_length=150,
        required=False,
        label='Resource title (optional)',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    resource_file = forms.FileField(
        required=False,
        label='Resource file (optional)',
        widget=forms.FileInput(attrs={'class': 'form-control'}),
    )
    class Meta:
        model = Opportunity
        fields = (
            'title', 'opportunity_type', 'category', 'description',
            'required_skills', 'positions', 'duration', 'deadline',
            'target_departments', 'status',
        )
        labels = {
            'opportunity_type': 'Type',
            'target_departments': 'Open to departments',
            'positions': 'Number of positions',
        }
        help_texts = {
            'required_skills': 'Separate skills with commas, e.g. Python, Machine Learning.',
            'target_departments': 'Students of the selected departments can apply.',
            'status': 'Draft is hidden from students. Choose Open to publish.',
        }
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'opportunity_type': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. Artificial Intelligence',
            }),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 6}),
            'required_skills': forms.TextInput(attrs={'class': 'form-control'}),
            'positions': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'duration': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. 3 months',
            }),
            'deadline': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'
            ),
            'target_departments': forms.CheckboxSelectMultiple,
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_deadline(self):
        deadline = self.cleaned_data['deadline']
        if 'deadline' in self.changed_data and deadline < timezone.localdate():
            raise forms.ValidationError('Deadline cannot be in the past.')
        return deadline

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            del self.fields['resource_title']
            del self.fields['resource_file']

    def clean_resource_file(self):
        uploaded = self.cleaned_data.get('resource_file')
        if uploaded:
            validate_resource_file(uploaded)
        return uploaded

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('resource_title') and not cleaned_data.get('resource_file'):
            self.add_error('resource_file', 'Please choose a file or clear the title.')
        return cleaned_data


class OpportunityResourceForm(forms.ModelForm):
    class Meta:
        model = OpportunityResource
        fields = ('title', 'file')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean_file(self):
        uploaded = self.cleaned_data['file']
        validate_resource_file(uploaded)
        return uploaded


class OpportunityFilterForm(forms.Form):
    """Search / filter bar on the browse page (sent with GET)."""
    q = forms.CharField(
        required=False,
        label='Search',
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'Title, category or skill',
        }),
    )
    opportunity_type = forms.ChoiceField(
        required=False,
        label='Type',
        choices=[('', 'All types')] + Opportunity.OpportunityType.choices,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    department = forms.ModelChoiceField(
        required=False,
        label='Open to department',
        queryset=Department.objects.all(),
        empty_label='All departments',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )