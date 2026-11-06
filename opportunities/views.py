import os
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from accounts.decorators import role_required
from accounts.models import User

from .forms import OpportunityFilterForm, OpportunityForm, OpportunityResourceForm
from .models import Opportunity, OpportunityResource, SavedOpportunity


def get_own_opportunity(request, pk):
    """Return the opportunity only if it belongs to the logged-in faculty."""
    return get_object_or_404(Opportunity, pk=pk, faculty=request.user.profile)


def get_saved_ids(user):
    """IDs of the opportunities this student has saved (empty set for others)."""
    if user.role == User.Role.STUDENT and user.profile is not None:
        return set(
            user.profile.saved_opportunities.values_list('opportunity_id', flat=True)
        )
    return set()


@role_required(User.Role.FACULTY)
def my_opportunities(request):
    opportunities = (
        request.user.profile.opportunities
        .prefetch_related('target_departments')
        .annotate(application_count=Count('applications'))
    )
    return render(request, 'opportunities/mine.html', {'opportunities': opportunities})


@role_required(User.Role.FACULTY)
def opportunity_create(request):
    if request.method == 'POST':
        form = OpportunityForm(request.POST, request.FILES)
        if form.is_valid():
            opportunity = form.save(commit=False)
            opportunity.faculty = request.user.profile
            opportunity.save()
            form.save_m2m()

            uploaded = form.cleaned_data.get('resource_file')
            if uploaded:
                OpportunityResource.objects.create(
                    opportunity=opportunity,
                    title=form.cleaned_data.get('resource_title')
                    or os.path.splitext(uploaded.name)[0],
                    file=uploaded,
                )
            messages.success(request, 'Opportunity created.')
            return redirect(opportunity)
    else:
        form = OpportunityForm(
            initial={'target_departments': [request.user.profile.department_id]}
        )
    return render(request, 'opportunities/form.html', {'form': form})


@role_required(User.Role.FACULTY)
def opportunity_edit(request, pk):
    opportunity = get_own_opportunity(request, pk)
    if request.method == 'POST':
        form = OpportunityForm(request.POST, instance=opportunity)
        if form.is_valid():
            form.save()
            messages.success(request, 'Opportunity updated.')
            return redirect(opportunity)
    else:
        form = OpportunityForm(instance=opportunity)
    return render(
        request, 'opportunities/form.html', {'form': form, 'opportunity': opportunity}
    )


@role_required(User.Role.FACULTY)
def opportunity_delete(request, pk):
    opportunity = get_own_opportunity(request, pk)
    if request.method == 'POST':
        for resource in opportunity.resources.all():
            resource.file.delete(save=False)
        for application in opportunity.applications.prefetch_related('attachments'):
            if application.cv:
                application.cv.delete(save=False)
            for attachment in application.attachments.all():
                attachment.file.delete(save=False)
        opportunity.delete()
        messages.success(request, 'Opportunity deleted.')
        return redirect('opportunities:mine')
    return render(
        request, 'opportunities/confirm_delete.html', {'opportunity': opportunity}
    )


@role_required(User.Role.FACULTY)
@require_POST
def opportunity_publish(request, pk):
    opportunity = get_own_opportunity(request, pk)
    if opportunity.deadline < timezone.localdate():
        messages.error(
            request, 'The deadline has already passed. Edit the deadline before publishing.'
        )
    else:
        opportunity.status = Opportunity.Status.OPEN
        opportunity.save(update_fields=['status', 'updated_at'])
        messages.success(request, 'Opportunity published. Students can now see it.')
    return redirect(opportunity)


@role_required(User.Role.FACULTY)
def resource_add(request, pk):
    opportunity = get_own_opportunity(request, pk)
    if request.method == 'POST':
        form = OpportunityResourceForm(request.POST, request.FILES)
        if form.is_valid():
            resource = form.save(commit=False)
            resource.opportunity = opportunity
            resource.save()
            messages.success(request, 'File uploaded.')
            return redirect(opportunity)
    else:
        form = OpportunityResourceForm()
    return render(
        request,
        'opportunities/resource_form.html',
        {'form': form, 'opportunity': opportunity},
    )


@role_required(User.Role.FACULTY)
@require_POST
def resource_delete(request, pk):
    resource = get_object_or_404(
        OpportunityResource, pk=pk, opportunity__faculty=request.user.profile
    )
    opportunity = resource.opportunity
    resource.file.delete(save=False)
    resource.delete()
    messages.success(request, 'File deleted.')
    return redirect(opportunity)


@login_required
def opportunity_list(request):
    opportunities = (
        Opportunity.objects
        .filter(status=Opportunity.Status.OPEN, deadline__gte=timezone.localdate())
        .select_related('faculty__user', 'faculty__department')
        .prefetch_related('target_departments')
    )

    form = OpportunityFilterForm(request.GET or None)
    if form.is_valid():
        search = form.cleaned_data['q']
        opportunity_type = form.cleaned_data['opportunity_type']
        department = form.cleaned_data['department']
        if search:
            opportunities = opportunities.filter(
                Q(title__icontains=search)
                | Q(category__icontains=search)
                | Q(required_skills__icontains=search)
            )
        if opportunity_type:
            opportunities = opportunities.filter(opportunity_type=opportunity_type)
        if department:
            opportunities = opportunities.filter(target_departments=department)

    return render(request, 'opportunities/list.html', {
        'opportunities': opportunities,
        'form': form,
        'saved_ids': get_saved_ids(request.user),
    })


@login_required
def opportunity_detail(request, pk):
    opportunity = get_object_or_404(
        Opportunity.objects
        .select_related('faculty__user', 'faculty__department')
        .prefetch_related('target_departments', 'resources'),
        pk=pk,
    )
    profile = request.user.profile
    is_owner = (
        request.user.role == User.Role.FACULTY
        and profile is not None
        and opportunity.faculty_id == profile.pk
    )

    if opportunity.status == Opportunity.Status.DRAFT and not is_owner:
        raise Http404

    my_application = None
    if request.user.role == User.Role.STUDENT and profile is not None:
        my_application = profile.applications.filter(opportunity=opportunity).first()

    collaboration = getattr(opportunity, 'collaboration', None)
    can_view_collab = False
    if collaboration is not None:
        can_view_collab = is_owner or (
            request.user.role == User.Role.STUDENT
            and profile is not None
            and collaboration.members.filter(student=profile).exists()
        )
    accepted_count = (
        opportunity.applications.filter(status='ACCEPTED').count() if is_owner else 0
    )

    return render(request, 'opportunities/detail.html', {
        'opportunity': opportunity,
        'is_owner': is_owner,
        'is_saved': pk in get_saved_ids(request.user),
        'my_application': my_application,
        'collaboration': collaboration,
        'can_view_collab': can_view_collab,
        'accepted_count': accepted_count,
    })


@role_required(User.Role.STUDENT)
@require_POST
def toggle_save(request, pk):
    opportunity = get_object_or_404(
        Opportunity.objects.exclude(status=Opportunity.Status.DRAFT), pk=pk
    )
    saved, created = SavedOpportunity.objects.get_or_create(
        student=request.user.profile, opportunity=opportunity
    )
    if created:
        messages.success(request, 'Saved to your list.')
    else:
        saved.delete()
        messages.info(request, 'Removed from your saved list.')

    next_url = request.POST.get('next', '')
    if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect(opportunity)


@role_required(User.Role.STUDENT)
def saved_list(request):
    saved_items = (
        request.user.profile.saved_opportunities
        .exclude(opportunity__status=Opportunity.Status.DRAFT)
        .select_related('opportunity__faculty__user', 'opportunity__faculty__department')
        .prefetch_related('opportunity__target_departments')
    )
    return render(request, 'opportunities/saved.html', {
        'saved_items': saved_items,
        'saved_ids': get_saved_ids(request.user),
    })