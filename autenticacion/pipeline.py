"""
Pipeline personalizado de social_django para crear perfil de usuario despues de Auth0 login.

Flujo:
1. social_django autentica con Auth0 y crea/obtiene el usuario Django
2. Este pipeline crea/actualiza el perfil Usuario con el rol de Auth0
3. Django mantiene la sesion activa automaticamente
4. El usuario es redirigido a LOGIN_REDIRECT_URL (/finops_platform/)
"""
import logging
import requests
import base64
import json

logger = logging.getLogger(__name__)

from django.conf import settings
from autenticacion.models import Usuario


def _get_role_from_userinfo(backend, response):
    """
    Obtiene el rol desde /userinfo usando el access_token de la response.
    Se usa en el pipeline donde request.user no esta disponible aun.
    """
    namespace = f"https://{settings.SOCIAL_AUTH_AUTH0_DOMAIN}/role"
    
    # Intento 1: desde el id_token JWT
    if 'id_token' in response:
        from autenticacion.auth0backend import Auth0
        claims = Auth0._extract_from_jwt(None, response['id_token'])
        role = claims.get(f"{settings.SOCIAL_AUTH_AUTH0_DOMAIN}/role")
        print("=== pipeline: rol from id_token:", role)
        if role:
            return role
    
    # Intento 2: desde el access_token JWT
    if 'access_token' in response:
        from autenticacion.auth0backend import Auth0
        claims = Auth0._extract_from_jwt(None, response['access_token'])
        role = claims.get(f"{settings.SOCIAL_AUTH_AUTH0_DOMAIN}/role")
        print("=== pipeline: rol from access_token JWT:", role)
        if role:
            return role
    
    # Intento 3: llamar a /userinfo directamente
    if 'access_token' in response:
        url = f'https://{settings.SOCIAL_AUTH_AUTH0_DOMAIN}/userinfo'
        headers = {'authorization': 'Bearer ' + response['access_token']}
        print("=== pipeline: GET userinfo for role fallback:", url)
        resp = requests.get(url, headers=headers)
        print("=== pipeline: userinfo status:", resp.status_code)
        userinfo = resp.json()
        print("=== pipeline: userinfo:", userinfo)
        role = userinfo.get(namespace)
        print("=== pipeline: rol from /userinfo:", role)
        return role
    
    return None


def create_usuario_profile(backend, user, response, *args, **kwargs):
    print("=== pipeline: RESPONSE KEYS:", list(response.keys()))
    
    role = _get_role_from_userinfo(backend, response)
    rol = role if role else 'usuario'
    print("=== pipeline: rol final a guardar:", rol)

    try:
        usuario = Usuario.objects.get(usuario_django=user)
        if usuario.rol != rol:
            usuario.rol = rol
            usuario.save()
            print(f"=== pipeline: Rol actualizado: {user.username} -> {rol} ===")
    except Usuario.DoesNotExist:
        usuario = Usuario.objects.create(
            usuario_django=user,
            rol=rol,
            activo=True,
        )
        print(f"=== pipeline: Usuario creado: {user.username} con rol: {rol} ===")

    return {'usuario_profile': usuario}
