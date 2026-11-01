import re
from django import forms
from django.contrib.auth.forms import (AuthenticationForm, PasswordResetForm, SetPasswordForm, UserCreationForm,)
from django.db import transaction

from .models import Department, StudentProfile, User


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