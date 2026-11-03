from django.urls import path
from . import views

app_name = 'collaboration'

urlpatterns = [
    path('', views.my_collaborations, name='mine'),
    path('start/<int:opportunity_pk>/', views.collaboration_start, name='start'),
    path('<int:pk>/', views.collaboration_detail, name='detail'),
    path('<int:pk>/edit/', views.collaboration_edit, name='edit'),
    path('<int:pk>/delete/', views.collaboration_delete, name='delete'),
    path('<int:pk>/members/add/', views.member_add, name='member_add'),
    path('members/<int:pk>/remove/', views.member_remove, name='member_remove'),
]