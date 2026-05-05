"""
Views para finops_platform - Dashboard principal
"""
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import logout


@require_http_methods(["GET"])
def index(request):
    if request.user.is_authenticated:
        refresh = RefreshToken.for_user(request.user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        logout(request)  # ← cerrar sesión Django para romper el ciclo
        return render(request, 'autenticacion/auth0_redirect.html', {
            'access_token': access_token,
            'refresh_token': refresh_token,
        })
    return render(request, 'finops_platform/overview.html')


@require_http_methods(["GET"])
def overview(request):
    """Renderiza el dashboard de overview
    
    Esta ruta es un alias para /finops_platform/ que muestra el dashboard.
    El cliente verifica si hay token JWT antes de mostrar.
    """
    return render(request, 'finops_platform/overview.html')

