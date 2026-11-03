from notifications.models import Notification
from notifications.utils import notify
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User
from applications.models import Application
from opportunities.models import Opportunity

from .forms import AddMemberForm, CollaborationForm
from .models import Collaboration, CollaborationMember


def get_own_collaboration(request, pk):
    """Return the collaboration only if its opportunity belongs to this faculty."""
    return get_object_or_404(
        Collaboration.objects.select_related('opportunity__faculty__user'),
        pk=pk,
        opportunity__faculty=request.user.profile,
    )


@login_required
def my_collaborations(request):
    profile = request.user.profile
    if profile is None:
        raise PermissionDenied
    if request.user.role == User.Role.FACULTY:
        collaborations = Collaboration.objects.filter(opportunity__faculty=profile)
    else:
        collaborations = Collaboration.objects.filter(
            pk__in=profile.collaboration_memberships.values('collaboration_id')
        )
    collaborations = (
        collaborations
        .select_related('opportunity__faculty__user')
        .annotate(member_count=Count('members'))
    )
    return render(request, 'collaboration/list.html', {'collaborations': collaborations})


@role_required(User.Role.FACULTY)
@require_POST
def collaboration_start(request, opportunity_pk):
    opportunity = get_object_or_404(
        Opportunity, pk=opportunity_pk, faculty=request.user.profile
    )
    existing = Collaboration.objects.filter(opportunity=opportunity).first()
    if existing:
        messages.info(request, 'A collaboration already exists for this opportunity.')
        return redirect(existing)

    accepted = Application.objects.filter(
        opportunity=opportunity, status=Application.Status.ACCEPTED
    )
    if not accepted.exists():
        messages.error(
            request, 'Accept at least one application before starting a collaboration.'
        )
        return redirect(opportunity)

    try:
        with transaction.atomic():
            collaboration = Collaboration.objects.create(
                opportunity=opportunity,
                title=opportunity.title,
                description=opportunity.description,
            )
            CollaborationMember.objects.bulk_create([
                CollaborationMember(collaboration=collaboration, student_id=application.student_id)
                for application in accepted
            ])
    except IntegrityError:
        messages.info(request, 'A collaboration already exists for this opportunity.')
        return redirect(opportunity)

    for application in accepted.select_related('student__user'):
        notify(
            recipient=application.student.user,
            title='Collaboration started',
            message=f'You are now a member of "{collaboration.title}".',
            notification_type=Notification.Type.COLLABORATION,
            link=collaboration.get_absolute_url(),
        )
    messages.success(request, 'Collaboration started with the accepted students.')
    return redirect(collaboration)


@login_required
def collaboration_detail(request, pk):
    collaboration = get_object_or_404(
        Collaboration.objects.select_related(
            'opportunity__faculty__user', 'opportunity__faculty__department'
        ),
        pk=pk,
    )
    profile = request.user.profile
    is_owner = (
        request.user.role == User.Role.FACULTY
        and profile is not None
        and collaboration.opportunity.faculty_id == profile.pk
    )
    is_member = (
        request.user.role == User.Role.STUDENT
        and profile is not None
        and collaboration.members.filter(student=profile).exists()
    )
    if not (is_owner or is_member):
        raise PermissionDenied

    members = collaboration.members.select_related('student__user', 'student__department')
    return render(request, 'collaboration/detail.html', {
        'collaboration': collaboration,
        'members': members,
        'is_owner': is_owner,
    })


@role_required(User.Role.FACULTY)
def collaboration_edit(request, pk):
    collaboration = get_own_collaboration(request, pk)
    if request.method == 'POST':
        form = CollaborationForm(request.POST, instance=collaboration)
        if form.is_valid():
            form.save()
            messages.success(request, 'Collaboration updated.')
            return redirect(collaboration)
    else:
        form = CollaborationForm(instance=collaboration)
    return render(request, 'collaboration/form.html', {
        'form': form,
        'collaboration': collaboration,
    })


@role_required(User.Role.FACULTY)
def collaboration_delete(request, pk):
    collaboration = get_own_collaboration(request, pk)
    if request.method == 'POST':
        opportunity = collaboration.opportunity
        collaboration.delete()
        messages.success(request, 'Collaboration deleted.')
        return redirect(opportunity)
    return render(request, 'collaboration/confirm_delete.html', {
        'collaboration': collaboration,
    })


@role_required(User.Role.FACULTY)
def member_add(request, pk):
    collaboration = get_own_collaboration(request, pk)
    if request.method == 'POST':
        form = AddMemberForm(request.POST, collaboration=collaboration)
        if form.is_valid():
            student = form.cleaned_data['student']
            CollaborationMember.objects.create(collaboration=collaboration, student=student)
            notify(
                recipient=student.user,
                title='Added to a collaboration',
                message=f'You were added to "{collaboration.title}".',
                notification_type=Notification.Type.COLLABORATION,
                link=collaboration.get_absolute_url(),
            )
            messages.success(request, 'Member added.')
            return redirect(collaboration)
    else:
        form = AddMemberForm(collaboration=collaboration)
    return render(request, 'collaboration/member_form.html', {
        'form': form,
        'collaboration': collaboration,
    })


@role_required(User.Role.FACULTY)
@require_POST
def member_remove(request, pk):
    member = get_object_or_404(
        CollaborationMember,
        pk=pk,
        collaboration__opportunity__faculty=request.user.profile,
    )
    collaboration = member.collaboration
    member.delete()
    messages.success(request, 'Member removed.')
    return redirect(collaboration)