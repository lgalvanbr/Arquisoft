"""
finops_platform URL Configuration

Main URL router para autenticacion y reportes apps.
Implementación según laboratorio ISIS2503
"""
from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # ======================== AUTH0 / SOCIAL AUTH PATHS ========================
    path('', include('django.contrib.auth.urls')),
    path('', include('social_django.urls')),
    
    # ======================== APP URLS ========================
    path('autenticacion/', include('autenticacion.urls')),
    path('reportes/', include('reportes.urls')),
    path('usuario/', include('usuario.urls')),
    path('empresa/', include('empresa.urls')),
    
    # ======================== MAIN INDEX ========================
    path('', views.index, name='index'),
]
