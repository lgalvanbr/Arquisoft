"""
finops_platform URL Configuration

Main URL router para autenticacion y reportes apps.
Implementación según laboratorio ISIS2503
"""
from django.contrib import admin
from django.urls import path, include
from . import views
from autenticacion import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # ======================== MAIN ENTRY POINT ========================
    path('', views.index, name='index'),
    path('finops_platform/', views.overview, name='finops_platform'),
    
    # ======================== AUTH0 CALLBACK ========================
    path('auth0/callback/', auth_views.auth0_callback_view, name='auth0_callback'),
    
    # ======================== LOGIN ========================
    path('login/', auth_views.login_view, name='login'),
    
    # ======================== APP URLS ========================
    path('autenticacion/', include('autenticacion.urls')),
    path('reportes/', include('reportes.urls')),
    path('usuario/', include('usuario.urls')),
    path('empresa/', include('empresa.urls')),
    
    # ======================== AUTH0 / SOCIAL AUTH PATHS ========================
    path('', include('django.contrib.auth.urls')),
    path('', include('social_django.urls')),
]
