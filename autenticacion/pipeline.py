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

logger = logging.getLogger(__name__)

from django.conf import settings
from autenticacion.models import Usuario

def create_usuario_profile(backend, user, response, *args, **kwargs):
    print("=== pipeline: RESPONSE KEYS:", list(response.keys()))
    print("=== pipeline: RESPONSE COMPLETO:", response)
    
    namespace = 'https://dev-vy27mzsmkwosyqhr.us.auth0.com'
    rol_claim = None

    # Intentar leer rol desde el id_token
    if 'id_token' in response:
        from autenticacion.auth0backend import Auth0
        claims = Auth0._extract_from_jwt(None, response['id_token'])
        print("=== pipeline: id_token claims:", list(claims.keys()))
        rol_claim = claims.get(f'{namespace}/role')
        print("=== pipeline: rol from id_token:", rol_claim)

    # Fallback desde access_token JWT
    if not rol_claim and 'access_token' in response:
        from autenticacion.auth0backend import Auth0
        claims = Auth0._extract_from_jwt(None, response['access_token'])
        print("=== pipeline: access_token claims:", list(claims.keys()))
        rol_claim = claims.get(f'{namespace}/role')
        print("=== pipeline: rol from access_token JWT:", rol_claim)

    # Fallback final: llamar a /userinfo directamente
    if not rol_claim and 'access_token' in response:
        url = f'https://{settings.SOCIAL_AUTH_AUTH0_DOMAIN}/userinfo'
        headers = {'authorization': 'Bearer ' + response['access_token']}
        print("=== pipeline: GET userinfo for role fallback:", url)
        resp = requests.get(url, headers=headers)
        print("=== pipeline: userinfo status:", resp.status_code)
        userinfo = resp.json()
        print("=== pipeline: userinfo:", userinfo)
        rol_claim = userinfo.get(f'{namespace}/role')
        print("=== pipeline: rol from /userinfo:", rol_claim)

    # Usar el valor directo de Auth0 (sin normalizar)
    rol = rol_claim if rol_claim else 'usuario'
    print("=== pipeline: rol final a guardar:", rol)

    try:
        usuario = Usuario.objects.get(usuario_django=user)
        # Actualizar rol si cambio
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
