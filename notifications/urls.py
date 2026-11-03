from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notification_list, name='list'),
    path('read-all/', views.mark_all_read, name='read_all'),
    path('<int:pk>/open/', views.notification_open, name='open'),
    path('<int:pk>/delete/', views.notification_delete, name='delete'),
]