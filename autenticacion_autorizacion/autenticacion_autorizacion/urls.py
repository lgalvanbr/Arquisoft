"""autenticacion_autorizacion URL Configuration

Rutas de la API de Autenticación y Autorización
"""
from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # ======================== ENDPOINTS DE AUTENTICACIÓN ========================
    path('api/auth/register', views.register, name='register'),
    path('api/auth/login', views.login, name='login'),
    path('api/auth/me', views.obtener_usuario_actual, name='obtener_usuario_actual'),
    path('api/auth/refresh', views.refresh_token, name='refresh_token'),
    path('api/auth/logout', views.logout, name='logout'),
    
    # ======================== ENDPOINTS DE AUDITORÍA ========================
    path('api/auth/audit/historial', views.historial_acceso, name='historial_acceso'),
    
    # ======================== HEALTH CHECK ========================
    path('api/health', views.health_check, name='health_check'),
]
