from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Notification


@login_required
def notification_list(request):
    # Only this user's own notifications are ever queried
    notifications = request.user.notifications.all()
    return render(request, 'notifications/list.html', {'notifications': notifications})


@login_required
@require_POST
def notification_open(request, pk):
    """Mark one notification as read, then go to the page it points to."""
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=['is_read'])
    if notification.link:
        return redirect(notification.link)
    return redirect('notifications:list')


@login_required
@require_POST
def mark_all_read(request):
    updated = request.user.notifications.filter(is_read=False).update(is_read=True)
    if updated:
        messages.success(request, 'All notifications marked as read.')
    return redirect('notifications:list')


@login_required
@require_POST
def notification_delete(request, pk):
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.delete()
    messages.success(request, 'Notification deleted.')
    return redirect('notifications:list')