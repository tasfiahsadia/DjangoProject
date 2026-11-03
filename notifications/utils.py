from .models import Notification

def notify(recipient, title, message,
           notification_type=Notification.Type.APPLICATION, link=''):
    """Create one notification for one user."""
    return Notification.objects.create(
        recipient=recipient,
        title=title,
        message=message,
        notification_type=notification_type,
        link=link,
    )