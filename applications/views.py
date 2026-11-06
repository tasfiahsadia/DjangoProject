from django.urls import reverse

from notifications.models import Notification
from notifications.utils import notify
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User
from opportunities.models import Opportunity
from collaboration.models import CollaborationMember

from .forms import (
    ApplicationAttachmentForm,
    ApplicationEvaluationForm,
    ApplicationForm,
)
from .models import Application, ApplicationAttachment, ApplicationEvaluation


class PositionsFull(Exception):
    """Raised when all positions of an opportunity are already filled."""


class ApplicationWithdrawn(Exception):
    """Raised when the student withdrew while the faculty was evaluating."""


def get_own_application(request, pk):
    """Return the application only if it belongs to the logged-in student."""
    return get_object_or_404(Application, pk=pk, student=request.user.profile)


def save_evaluation(form, application, faculty):
    """Save the evaluation and update the application status all-or-nothing."""
    with transaction.atomic():
        opportunity = Opportunity.objects.select_for_update().get(
            pk=application.opportunity_id
        )
        locked = Application.objects.select_for_update().get(pk=application.pk)
        if locked.status == Application.Status.WITHDRAWN:
            raise ApplicationWithdrawn

        evaluation = form.save(commit=False)
        if evaluation.decision == ApplicationEvaluation.Decision.ACCEPTED:
            accepted = (
                Application.objects
                .filter(opportunity=opportunity, status=Application.Status.ACCEPTED)
                .exclude(pk=locked.pk)
                .count()
            )
            if accepted >= opportunity.positions:
                raise PositionsFull(
                    f'All {opportunity.positions} position(s) for this opportunity '
                    f'are already filled.'
                )

        evaluation.application = locked
        evaluation.evaluator = faculty
        evaluation.save()
        locked.status = evaluation.decision
        locked.save(update_fields=['status', 'updated_at'])

        accepted_total = Application.objects.filter(
            opportunity=opportunity, status=Application.Status.ACCEPTED
        ).count()
        if (accepted_total >= opportunity.positions
                and opportunity.status == Opportunity.Status.OPEN):
            opportunity.status = Opportunity.Status.CLOSED
            opportunity.save(update_fields=['status', 'updated_at'])

@role_required(User.Role.STUDENT)
def apply(request, opportunity_pk):
    opportunity = get_object_or_404(
        Opportunity.objects.exclude(status=Opportunity.Status.DRAFT),
        pk=opportunity_pk,
    )
    student = request.user.profile

    existing = Application.objects.filter(student=student, opportunity=opportunity).first()
    if existing:
        messages.info(request, 'You have already applied to this opportunity.')
        return redirect('applications:detail', pk=existing.pk)

    if not opportunity.is_open:
        messages.error(request, 'This opportunity is not open for applications.')
        return redirect(opportunity)
    if not opportunity.target_departments.filter(pk=student.department_id).exists():
        messages.error(request, 'This opportunity is not open to your department.')
        return redirect(opportunity)

    if request.method == 'POST':
        form = ApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            application = form.save(commit=False)
            application.opportunity = opportunity
            application.student = student
            try:
                application.save()
            except IntegrityError:
                messages.info(request, 'You have already applied to this opportunity.')
                return redirect(opportunity)

            notify(
                recipient=opportunity.faculty.user,
                title='New application received',
                message=(
                    f'{request.user.get_full_name() or request.user.username} '
                    f'applied for "{opportunity.title}".'
                ),
                notification_type=Notification.Type.APPLICATION,
                link=reverse('applications:review', args=[application.pk]),
            )
            messages.success(request, 'Your application was submitted.')
            return redirect('applications:detail', pk=application.pk)
    else:
        form = ApplicationForm()

    return render(request, 'applications/apply.html', {
        'form': form,
        'opportunity': opportunity,
    })


@role_required(User.Role.STUDENT)
def my_applications(request):
    applications = request.user.profile.applications.select_related(
        'opportunity__faculty__user'
    )
    return render(request, 'applications/my_list.html', {'applications': applications})


@role_required(User.Role.STUDENT)
def application_detail(request, pk):
    application = get_own_application(request, pk)
    return render(request, 'applications/detail.html', {
        'application': application,
        'evaluation': getattr(application, 'evaluation', None),
        'attachments': application.attachments.all(),
        'can_change': application.is_pending,
    })


@role_required(User.Role.STUDENT)
def application_edit(request, pk):
    application = get_own_application(request, pk)
    if not application.is_pending:
        messages.error(request, 'Only a pending application can be edited.')
        return redirect('applications:detail', pk=application.pk)

    old_cv = application.cv.name

    if request.method == 'POST':
        form = ApplicationForm(request.POST, request.FILES, instance=application)
        if form.is_valid():
            form.save()
            if old_cv and old_cv != application.cv.name:
                application.cv.storage.delete(old_cv)
            messages.success(request, 'Your application was updated.')
            return redirect('applications:detail', pk=application.pk)
    else:
        form = ApplicationForm(instance=application)
    return render(request, 'applications/edit.html', {
        'form': form,
        'application': application,
    })


@role_required(User.Role.STUDENT)
@require_POST
def application_withdraw(request, pk):
    application = get_own_application(request, pk)
    if not application.is_pending:
        messages.error(request, 'Only a pending application can be withdrawn.')
    else:
        application.status = Application.Status.WITHDRAWN
        application.save(update_fields=['status', 'updated_at'])
        notify(
            recipient=application.opportunity.faculty.user,
            title='Application withdrawn',
            message=(
                f'{request.user.get_full_name() or request.user.username} '
                f'withdrew the application for "{application.opportunity.title}".'
            ),
            notification_type=Notification.Type.APPLICATION,
            link=reverse('applications:review', args=[application.pk]),
        )
        messages.success(request, 'Your application was withdrawn.')
    return redirect('applications:detail', pk=application.pk)


@role_required(User.Role.STUDENT)
def attachment_add(request, pk):
    application = get_own_application(request, pk)
    if not application.is_pending:
        messages.error(request, 'Files can be added only to a pending application.')
        return redirect('applications:detail', pk=application.pk)

    if request.method == 'POST':
        form = ApplicationAttachmentForm(
            request.POST, request.FILES, application=application
        )
        if form.is_valid():
            attachment = form.save(commit=False)
            attachment.application = application
            attachment.save()
            messages.success(request, 'File uploaded.')
            return redirect('applications:detail', pk=application.pk)
    else:
        form = ApplicationAttachmentForm(application=application)
    return render(request, 'applications/attachment_form.html', {
        'form': form,
        'application': application,
    })


@role_required(User.Role.STUDENT)
@require_POST
def attachment_delete(request, pk):
    attachment = get_object_or_404(
        ApplicationAttachment, pk=pk, application__student=request.user.profile
    )
    application = attachment.application
    if not application.is_pending:
        messages.error(request, 'Files can be removed only from a pending application.')
    else:
        attachment.file.delete(save=False)
        attachment.delete()
        messages.success(request, 'File deleted.')
    return redirect('applications:detail', pk=application.pk)


@role_required(User.Role.FACULTY)
def opportunity_applications(request, pk):
    opportunity = get_object_or_404(
        Opportunity, pk=pk, faculty=request.user.profile
    )
    applications = opportunity.applications.select_related(
        'student__user', 'student__department'
    )

    counts = {
        row['status']: row['total']
        for row in (
            opportunity.applications.order_by()
            .values('status')
            .annotate(total=Count('id'))
        )
    }
    status_rows = [
        {'value': value, 'label': label, 'count': counts.get(value, 0)}
        for value, label in Application.Status.choices
    ]

    selected = request.GET.get('status', '')
    if selected in Application.Status.values:
        applications = applications.filter(status=selected)
    else:
        selected = ''

    return render(request, 'applications/opportunity_applications.html', {
        'opportunity': opportunity,
        'applications': applications,
        'status_rows': status_rows,
        'selected_status': selected,
        'total_count': sum(counts.values()),
    })


@role_required(User.Role.FACULTY)
def application_review(request, pk):
    application = get_object_or_404(
        Application.objects.select_related(
            'student__user', 'student__department', 'opportunity'
        ),
        pk=pk,
        opportunity__faculty=request.user.profile,
    )
    evaluation = getattr(application, 'evaluation', None)
    can_evaluate = application.status != Application.Status.WITHDRAWN

    if request.method == 'POST':
        if not can_evaluate:
            messages.error(request, 'A withdrawn application cannot be evaluated.')
            return redirect('applications:review', pk=application.pk)
        form = ApplicationEvaluationForm(
            request.POST, instance=evaluation, application=application
        )
        if form.is_valid():
            try:
                save_evaluation(form, application, request.user.profile)
            except ApplicationWithdrawn:
                messages.error(request, 'The student withdrew this application.')
                return redirect('applications:review', pk=application.pk)
            except PositionsFull as error:
                form.add_error(None, str(error))
            else:
                messages.success(request, 'Evaluation saved.')
                notify(
                    recipient=application.student.user,
                    title='Your application was evaluated',
                    message=(
                        f'Your application for "{application.opportunity.title}" '
                        f'was {form.instance.get_decision_display().lower()}.'
                    ),
                    notification_type=Notification.Type.EVALUATION,
                    link=reverse('applications:detail', args=[application.pk]),
                )
                already_member = CollaborationMember.objects.filter(
                    collaboration__opportunity=application.opportunity,
                    student=application.student,
                ).exists()
                if already_member and form.instance.decision != ApplicationEvaluation.Decision.ACCEPTED:
                    messages.warning(
                        request,
                        'This student is already a member of the collaboration. '
                        'Remove them from the collaboration page if needed.',
                    )
                return redirect('applications:review', pk=application.pk)
    else:
        form = ApplicationEvaluationForm(instance=evaluation, application=application)

    return render(request, 'applications/review.html', {
        'application': application,
        'evaluation': evaluation,
        'attachments': application.attachments.all(),
        'form': form,
        'can_evaluate': can_evaluate,
    })