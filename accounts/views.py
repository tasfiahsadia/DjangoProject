from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render

from .models import User


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