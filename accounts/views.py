from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from .tokens import email_verification_token
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
    ResendVerificationForm,
)
from .models import User


def send_verification_email(request, user):
    """Build the verification link and send it (the terminal prints it in development)."""
    context = {
        'user': user,
        'protocol': 'https' if request.is_secure() else 'http',
        'domain': get_current_site(request).domain,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': email_verification_token.make_token(user),
    }
    subject = render_to_string('accounts/verify_email_subject.txt', context).strip()
    body = render_to_string('accounts/verify_email_body.txt', context)
    send_mail(subject, body, None, [user.email])

def register(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            send_verification_email(request, user)
            messages.success(
                request,
                'Registration successful. Please verify your email with the link '
                'we sent, then log in.',
            )
            return redirect('accounts:login')
    else:
        form = StudentRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})

def activate(request, uidb64, token):
    try:
        user = User.objects.get(pk=urlsafe_base64_decode(uidb64).decode())
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and user.is_active:
        messages.info(request, 'Your email is already verified. Please log in.')
        return redirect('accounts:login')

    if user is not None and email_verification_token.check_token(user, token):
        user.is_active = True
        user.save(update_fields=['is_active'])
        messages.success(request, 'Email verified, you can now log in.')
        return redirect('accounts:login')

    messages.error(
        request, 'This verification link is invalid or has expired. Request a new one.'
    )
    return redirect('accounts:resend_verification')


def resend_verification(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        form = ResendVerificationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].strip().lower()
            user = User.objects.filter(email__iexact=email, is_active=False).first()
            if user:
                send_verification_email(request, user)
            messages.success(
                request,
                'If this email belongs to an account that is not verified yet, '
                'we have sent a new verification link.',
            )
            return redirect('accounts:login')
    else:
        form = ResendVerificationForm()
    return render(request, 'accounts/resend_verification.html', {'form': form})

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
    old_cv = profile.cv.name if hasattr(profile, 'cv') else ''

    if request.method == 'POST':
        user_form = UserNameForm(request.POST, instance=request.user)
        profile_form = profile_form_class(request.POST, request.FILES, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()

            if old_picture and old_picture != profile.profile_picture.name:
                profile.profile_picture.storage.delete(old_picture)
            if old_cv and old_cv != profile.cv.name:
                profile.cv.storage.delete(old_cv)
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