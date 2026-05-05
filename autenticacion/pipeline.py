"""
Pipeline personalizado de social_django para crear perfil de usuario despues de Auth0 login.

Flujo:
1. social_django autentica con Auth0 y crea/obtiene el usuario Django
2. Este pipeline crea/actualiza el perfil Usuario con el rol de Auth0
3. Django mantiene la sesion activa automaticamente
4. El usuario es redirigido a LOGIN_REDIRECT_URL (/finops_platform/)
"""
import logging

logger = logging.getLogger(__name__)

from autenticacion.models import Usuario

def create_usuario_profile(backend, user, response, *args, **kwargs):
    print("=== RESPONSE KEYS:", list(response.keys()))
    print("=== RESPONSE COMPLETO:", response)
    
    namespace = 'https://dev-vy27mzsmkwosyqhr.us.auth0.com'
    rol_claim = None

    # Leer rol desde el id_token
    if 'id_token' in response:
        from autenticacion.auth0backend import Auth0
        claims = Auth0._extract_from_jwt(None, response['id_token'])
        rol_claim = claims.get(f'{namespace}/rol')

    # Fallback desde access_token
    if not rol_claim and 'access_token' in response:
        from autenticacion.auth0backend import Auth0
        claims = Auth0._extract_from_jwt(None, response['access_token'])
        rol_claim = claims.get(f'{namespace}/rol')

    rol_map = {
        'admin': 'admin',
        'manager': 'gerente',
        'gerente': 'gerente',
        'usuario': 'usuario',
    }
    rol = rol_map.get(rol_claim, 'usuario')

    try:
        usuario = Usuario.objects.get(usuario_django=user)
        # Actualizar rol si cambio
        if rol_claim and usuario.rol != rol:
            usuario.rol = rol
            usuario.save()
            print(f"=== Rol actualizado: {user.username} -> {rol} ===")
    except Usuario.DoesNotExist:
        usuario = Usuario.objects.create(
            usuario_django=user,
            rol=rol,
            activo=True,
        )
        print(f"=== Usuario creado: {user.username} con rol: {rol} ===")

    return {'usuario_profile': usuario}
