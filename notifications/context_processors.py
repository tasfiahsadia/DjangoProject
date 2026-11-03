def unread_count(request):
    """Make the number of unread notifications available in every template."""
    user = getattr(request, 'user', None)
    if user is not None and user.is_authenticated:
        return {
            'unread_notification_count': user.notifications.filter(is_read=False).count()
        }
    return {}