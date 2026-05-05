from django.urls import path
from . import views

urlpatterns = [
    # Template view
    path('', views.usuario_view, name='usuario'),

    # API endpoints
    path('listar/', views.listar_usuarios, name='listar_usuarios'),
    path('asignar-rol/', views.asignar_rol, name='asignar_rol'),
]
