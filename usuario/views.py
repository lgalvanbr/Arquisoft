from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.models import User
from django.middleware.csrf import get_token
import json

@require_http_methods(["GET"])
def listar_usuarios(request):
    """
    GET /api/usuarios/
    Retorna lista de todos los usuarios del sistema
    """
    try:
        usuarios = User.objects.all().values('id', 'username', 'email', 'first_name', 'last_name')
        return JsonResponse({
            'total': usuarios.count(),
            'usuarios': list(usuarios)
        }, status=200)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


def usuario_view(request):
    """
    GET /usuario/
    Renderiza template de listado de usuarios
    """
    return render(request, 'usuario/usuario.html')
