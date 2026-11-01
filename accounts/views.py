from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import (PasswordChangeView, PasswordResetConfirmView, PasswordResetView)
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from .forms import (
    FacultyProfileForm,
    ResetPasswordForm,
    ResetRequestForm,
    StudentProfileForm,
    StudentRegistrationForm,
    StyledPasswordChangeForm,
    UserNameForm,
)
from .models import User

def register(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Registration successful. You can now log in.')
            return redirect('accounts:login')
    else:
        form = StudentRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})

@login_required
def dashboard(request):
    user = request.user
    if user.is_superuser:
        return redirect('admin:index')
    if user.role == User.Role.FACULTY:
        return redirect('accounts:faculty_dashboard')
    return redirect('accounts:student_dashboard')


@login_required
def student_dashboard(request):
    if request.user.role != User.Role.STUDENT:
        raise PermissionDenied
    profile = getattr(request.user, 'student_profile', None)
    return render(request, 'accounts/student_dashboard.html', {'profile': profile})


@login_required
def faculty_dashboard(request):
    if request.user.role != User.Role.FACULTY:
        raise PermissionDenied
    profile = getattr(request.user, 'faculty_profile', None)
    return render(request, 'accounts/faculty_dashboard.html', {'profile': profile})


class PasswordResetRequestView(SuccessMessageMixin, PasswordResetView):
    template_name = 'accounts/password_reset_form.html'
    email_template_name = 'accounts/password_reset_email.txt'
    subject_template_name = 'accounts/password_reset_subject.txt'
    form_class = ResetRequestForm
    success_url = reverse_lazy('accounts:login')
    success_message = (
        'If an account with that email exists, '
        'we have sent password reset instructions.'
    )


class PasswordResetSetView(SuccessMessageMixin, PasswordResetConfirmView):
    template_name = 'accounts/password_reset_confirm.html'
    form_class = ResetPasswordForm
    success_url = reverse_lazy('accounts:login')
    success_message = 'Your password has been changed. You can now log in.'


@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html', {'profile': request.user.profile})


@login_required
def profile_edit(request):
    profile = request.user.profile
    if profile is None:
        messages.error(request, 'Your profile has not been set up yet.')
        return redirect('accounts:dashboard')

    if request.user.role == User.Role.FACULTY:
        profile_form_class = FacultyProfileForm
    else:
        profile_form_class = StudentProfileForm
    old_picture = profile.profile_picture.name

    if request.method == 'POST':
        user_form = UserNameForm(request.POST, instance=request.user)
        profile_form = profile_form_class(request.POST, request.FILES, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            # Delete the old picture file if it was replaced or removed.
            if old_picture and old_picture != profile.profile_picture.name:
                profile.profile_picture.storage.delete(old_picture)
            messages.success(request, 'Your profile was updated.')
            return redirect('accounts:profile')
    else:
        user_form = UserNameForm(instance=request.user)
        profile_form = profile_form_class(instance=profile)

    return render(request, 'accounts/profile_edit.html', {
        'user_form': user_form,
        'profile_form': profile_form,
    })


class PasswordChangeProfileView(SuccessMessageMixin, PasswordChangeView):
    template_name = 'accounts/password_change.html'
    form_class = StyledPasswordChangeForm
    success_url = reverse_lazy('accounts:profile')
    success_message = 'Your password was changed.'