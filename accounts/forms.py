import re
from django import forms
from django.contrib.auth.forms import (AuthenticationForm,PasswordChangeForm,PasswordResetForm,SetPasswordForm,UserCreationForm,)
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction

from .models import Department, FacultyProfile, StudentProfile, User


class StudentRegistrationForm(UserCreationForm):
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        empty_label='Select your department',
    )
    student_id = forms.CharField(max_length=8, label='Student ID')
    batch = forms.IntegerField(min_value=1, max_value=999)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')

        field_order = [
            'username',
            'email',
            'department',
            'student_id',
            'batch',
            'password1',
            'password2',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            'username': 'Username',
            'email': 'University email (@uap-bd.edu)',
            'student_id': 'Student ID (8 digits)',
            'batch': 'Batch (e.g. 57)',
            'password1': 'Password',
            'password2': 'Confirm password',
        }
        for name, text in placeholders.items():
            self.fields[name].widget.attrs['placeholder'] = text

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if not email.endswith('@uap-bd.edu'):
            raise forms.ValidationError(
                'Only university email addresses (@uap-bd.edu) are allowed.'
            )
        return email

    def clean_student_id(self):
        student_id = self.cleaned_data['student_id'].strip()
        if not re.fullmatch(r'[0-9]{8}', student_id):
            raise forms.ValidationError(
                'Student ID must be exactly 8 digits.'
            )
        if StudentProfile.objects.filter(student_id=student_id).exists():
            raise forms.ValidationError(
                'A student with this ID is already registered.'
            )
        return student_id

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.STUDENT
        user.is_active = False
        user.save()
        StudentProfile.objects.create(
            user=user,
            department=self.cleaned_data['department'],
            student_id=self.cleaned_data['student_id'],
            batch=self.cleaned_data['batch'],
        )
        return user

class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'placeholder': 'Username',
            'autocomplete': 'username',
        })
        self.fields['password'].widget.attrs.update({
            'placeholder': 'Password',
            'autocomplete': 'current-password',
        })

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        if username and password:
            user = User.objects.filter(username=username).first()
            if user and not user.is_active and user.check_password(password):
                raise forms.ValidationError(
                    'Your email is not verified yet. Open the verification link '
                    'sent to your email, or request a new link below.',
                    code='unverified',
                )
        return super().clean()

class ResetRequestForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({
            'placeholder': 'University email',
            'autocomplete': 'email',
        })


class ResetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].widget.attrs['placeholder'] = 'New password'
        self.fields['new_password2'].widget.attrs['placeholder'] = 'Confirm new password'


class UserNameForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }


class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ('profile_picture', 'bio', 'semester', 'interests', 'cv')
        labels = {
            'semester': 'Current semester',
            'cv': 'CV (PDF, max 5 MB, optional)',
        }
        help_texts = {
            'interests': 'Separate with commas.',
        }
        widgets = {
            'profile_picture': forms.ClearableFileInput(
                attrs={'class': 'form-control', 'accept': 'image/*'}
            ),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'semester': forms.NumberInput(
                attrs={'class': 'form-control', 'min': 1, 'max': 8, 'placeholder': 'e.g. 5'}
            ),
            'interests': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'e.g. Machine Learning, Web Development, Python'}
            ),
            'cv': forms.ClearableFileInput(
                attrs={'class': 'form-control', 'accept': 'application/pdf,.pdf'}
            ),
        }

    def clean_profile_picture(self):
        picture = self.cleaned_data.get('profile_picture')
        if isinstance(picture, UploadedFile) and picture.size > 2 * 1024 * 1024:
            raise forms.ValidationError('Image must be 2 MB or smaller.')
        return picture

    def clean_cv(self):
        cv = self.cleaned_data.get('cv')
        if isinstance(cv, UploadedFile) and cv.size > 5 * 1024 * 1024:
            raise forms.ValidationError('CV must be 5 MB or smaller.')
        return cv


class FacultyProfileForm(StudentProfileForm):
    class Meta(StudentProfileForm.Meta):
        model = FacultyProfile
        fields = ('profile_picture', 'bio')


class StyledPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

class ResendVerificationForm(forms.Form):
    email = forms.EmailField(
        label='University email',
        widget=forms.EmailInput(attrs={
            'placeholder': 'University email',
            'autocomplete': 'email',
        }),
    )