from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def role_required(role):
    """Allow only logged-in users with the given role (STUDENT or FACULTY)."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.role != role or request.user.profile is None:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return login_required(wrapper)
    return decorator