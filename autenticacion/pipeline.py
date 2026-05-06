"""
Pipeline personalizado de social_django para crear perfil de usuario despues de Auth0 login.

Flujo:
1. social_django autentica con Auth0 y crea/obtiene el usuario Django
2. Este pipeline crea/actualiza el perfil Usuario con el rol de Auth0 via getRole
3. Django mantiene la sesion activa automaticamente
4. El usuario es redirigido a LOGIN_REDIRECT_URL (/finops_platform/)
"""
import logging

logger = logging.getLogger(__name__)

from autenticacion.models import Usuario
from autenticacion.auth0backend import getRole

def create_usuario_profile(backend, user, response, *args, **kwargs):
    print("=== pipeline: RESPONSE KEYS:", list(response.keys()))
    print("=== pipeline: RESPONSE COMPLETO:", response)
    
    # Obtener request del strategy de social_django
    request = backend.strategy.request
    
    # Usar getRole para obtener el rol desde /userinfo
    role = getRole(request)
    print("=== pipeline: getRole returned:", role)
    
    rol = role if role else 'usuario'
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
