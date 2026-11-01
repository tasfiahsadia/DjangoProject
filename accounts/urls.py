from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import LoginForm

app_name = 'accounts'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='accounts/login.html',
            authentication_form=LoginForm,
            redirect_authenticated_user=True,
        ),
        name='login',
    ),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', views.register, name='register'),
    path('password/reset/', views.PasswordResetRequestView.as_view(), name='password_reset'),
    path(
        'password/reset/<uidb64>/<token>/', views.PasswordResetSetView.as_view(), name='password_reset_confirm'),
    path('student/', views.student_dashboard, name='student_dashboard'),
    path('faculty/', views.faculty_dashboard, name='faculty_dashboard'),
]