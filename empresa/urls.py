from django.urls import path
from . import views

urlpatterns = [
    # Template view
    path('', views.empresa_view, name='empresa'),
    
    # API endpoints
    path('listar/', views.listar_empresas, name='listar_empresas'),
    path('asociar/', views.asociar_usuario_empresa, name='asociar_usuario_empresa'),
]
