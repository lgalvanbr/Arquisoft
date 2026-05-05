"""
Views para finops_platform - Dashboard principal
"""
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required


@require_http_methods(["GET"])
def index(request):
    """Renderiza la página de inicio/overview"""
    if not request.user.is_authenticated:
        return render(request, 'autenticacion/login.html')
    return render(request, 'finops_platform/overview.html')


@require_http_methods(["GET"])
@login_required
def overview(request):
    """Renderiza el dashboard de overview"""
    return render(request, 'finops_platform/overview.html')
