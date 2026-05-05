from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.contrib.auth import logout
from autenticacion.utilities import JWTManager

@require_http_methods(["GET"])
def index(request):
    if request.user.is_authenticated:
        usuario = request.user
        access_token = JWTManager.generar_token_access(usuario)
        refresh_token = JWTManager.generar_token_refresh(usuario)
        JWTManager.guardar_tokens(usuario, access_token, refresh_token)
        logout(request)
        return render(request, 'autenticacion/auth0_redirect.html', {
            'access_token': access_token,
            'refresh_token': refresh_token,
        })
    return render(request, 'finops_platform/overview.html')

@require_http_methods(["GET"])
def overview(request):
    return render(request, 'finops_platform/overview.html')
