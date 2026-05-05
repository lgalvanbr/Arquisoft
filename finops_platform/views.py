"""
Views para finops_platform - Dashboard principal
"""
from django.shortcuts import render
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET"])
def index(request):
    """Renderiza la página principal (login o dashboard según token JWT del cliente)
    
    El servidor siempre retorna un HTML que contiene TANTO login como dashboard.
    El cliente JavaScript verifica si hay token en localStorage y muestra lo apropiado.
    """
    return render(request, 'finops_platform/overview.html')


@require_http_methods(["GET"])
def overview(request):
    """Renderiza el dashboard de overview
    
    Esta ruta es un alias para /finops_platform/ que muestra el dashboard.
    El cliente verifica si hay token JWT antes de mostrar.
    """
    return render(request, 'finops_platform/overview.html')

