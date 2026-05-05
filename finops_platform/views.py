"""
Views para finops_platform - Dashboard principal
"""
from django.shortcuts import render
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET"])
def index(request):
    """Renderiza la página principal (login/dashboard unificado)
    
    Siempre retorna index.html que contiene TANTO el login como el dashboard.
    El JavaScript del cliente decide qué mostrar según si hay token en localStorage.
    """
    return render(request, 'finops_platform/index.html')


@require_http_methods(["GET"])
def overview(request):
    """Renderiza el dashboard (alias para compatibilidad)"""
    return render(request, 'finops_platform/index.html')
