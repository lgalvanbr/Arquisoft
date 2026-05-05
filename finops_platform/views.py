"""
Views para finops_platform - Dashboard principal
"""
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required


@require_http_methods(["GET"])
def index(request):
    """Renderiza la página de inicio/login"""
    if request.user.is_authenticated:
        return render(request, 'finops_platform/overview.html')
    return render(request, 'autenticacion/login.html')


@require_http_methods(["GET"])
def overview(request):
    """Renderiza el dashboard de overview - requiere autenticación"""
    if not request.user.is_authenticated:
        return render(request, 'autenticacion/login.html')
    return render(request, 'finops_platform/overview.html')

