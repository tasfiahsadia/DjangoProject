from django.urls import path
from . import views

app_name = 'applications'

urlpatterns = [
    path('mine/', views.my_applications, name='mine'),
    path('apply/<int:opportunity_pk>/', views.apply, name='apply'),
    path('<int:pk>/', views.application_detail, name='detail'),
    path('<int:pk>/edit/', views.application_edit, name='edit'),
    path('<int:pk>/withdraw/', views.application_withdraw, name='withdraw'),
    path('<int:pk>/attachments/add/', views.attachment_add, name='attachment_add'),
    path('attachments/<int:pk>/delete/', views.attachment_delete, name='attachment_delete'),
    path('opportunity/<int:pk>/', views.opportunity_applications, name='opportunity_applications'),
    path('<int:pk>/review/', views.application_review, name='review'),
]