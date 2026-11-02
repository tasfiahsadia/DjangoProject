from django.urls import path
from . import views

app_name = 'opportunities'

urlpatterns = [
    path('', views.opportunity_list, name='list'),
    path('mine/', views.my_opportunities, name='mine'),
    path('saved/', views.saved_list, name='saved'),
    path('create/', views.opportunity_create, name='create'),
    path('<int:pk>/', views.opportunity_detail, name='detail'),
    path('<int:pk>/edit/', views.opportunity_edit, name='edit'),
    path('<int:pk>/delete/', views.opportunity_delete, name='delete'),
    path('<int:pk>/publish/', views.opportunity_publish, name='publish'),
    path('<int:pk>/save/', views.toggle_save, name='toggle_save'),
    path('<int:pk>/resources/add/', views.resource_add, name='resource_add'),
    path('resources/<int:pk>/delete/', views.resource_delete, name='resource_delete'),
]