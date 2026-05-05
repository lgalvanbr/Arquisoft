"""
URL configuration for autenticacion app.

Rutas de autenticacion, autorizacion y auditoria.
Implementacion segun laboratorio ISIS2503
"""
from django.urls import path
from . import views

urlpatterns = [
    # ======================== TEMPLATE VIEWS ========================
    path('', views.login_view, name='login_page'),
    path('seguridad/', views.seguridad_view, name='seguridad_page'),
    
    # ======================== AUTH0 / SOCIAL AUTH PATHS ========================
    # Se incluyen en finops_platform/urls.py (social_django.urls)
    
    # ======================== ENDPOINTS DE AUTENTICACION ========================
    path('register', views.register, name='register'),
    path('login', views.login, name='login'),
    path('me', views.obtener_usuario_actual, name='obtener_usuario_actual'),
    path('refresh', views.refresh_token, name='refresh_token'),
    path('logout', views.logout, name='logout'),
    
    # ======================== ENDPOINTS DE AUDITORIA ========================
    path('audit/historial', views.historial_acceso, name='historial_acceso'),
    path('rechazos/integridad', views.listar_rechazos_integridad, name='listar_rechazos_integridad'),
    
    # ======================== HEALTH CHECK ========================
    path('health', views.health_check, name='health_check'),

    # ======================== AUTH0 LOGIN (custom entry point) ========================
    path('login/auth0', views.auth0_login, name='auth0_login'),
]
