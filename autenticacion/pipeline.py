"""
Pipeline personalizado de social_django para generar JWTs después de Auth0 login.

Flujo:
1. social_django autentica con Auth0 y crea/obtiene el usuario Django
2. Este pipeline genera JWT tokens (access + refresh)
3. Guarda los tokens en la sesión Django
4. El usuario es redirigido a /auth0/callback/ que captura los tokens
5. El callback redirige a /finops_platform/?auth_token=xxx
6. JavaScript captura el token de la URL y lo guarda en localStorage
"""
import logging

logger = logging.getLogger(__name__)

from autenticacion.models import Usuario

def create_usuario_profile(backend, user, response, *args, **kwargs):
    """
    Crea el perfil Usuario propio si no existe después del login con Auth0.
    """
    try:
        usuario = Usuario.objects.get(usuario_django=user)
    except Usuario.DoesNotExist:
        # Obtener rol desde los claims del token
        namespace = 'https://dev-vy27mzsmkwosyqhr.us.auth0.com'
        rol = 'usuario'  # default
        
        # Intentar leer el rol desde extra_data
        if kwargs.get('social') and kwargs['social'].extra_data:
            rol = kwargs['social'].extra_data.get('rol', 'usuario') or 'usuario'
        
        # Intentar desde response directo
        if rol == 'usuario':
            rol_claim = response.get(f'{namespace}/rol')
            if rol_claim:
                rol = rol_claim

        # Mapear rol de Auth0 a los choices del modelo
        rol_map = {
            'admin': 'admin',
            'manager': 'gerente', 
            'gerente': 'gerente',
            'usuario': 'usuario',
        }
        rol = rol_map.get(rol, 'usuario')

        usuario = Usuario.objects.create(
            usuario_django=user,
            rol=rol,
            activo=True,
        )
        print(f"=== Usuario creado: {user.username} con rol: {rol} ===")
    
    return {'usuario_profile': usuario}


def save_jwt_to_session(backend, user, response, *args, **kwargs):
    """
    Pipeline step que genera JWTs y los guarda en la sesión después de Auth0 login.
    Se ejecuta automáticamente después de que social_django crea/obtiene el usuario.
    """
    try:
        from autenticacion.utilities import JWTManager
        from autenticacion.models import Usuario

        # Obtener el perfil Usuario asociado al Django User
        usuario = None
        try:
            usuario = user.perfil_autenticacion
        except Exception:
            try:
                usuario = Usuario.objects.get(usuario_django=user)
            except Exception:
                logger.warning(f"No se encontró perfil Usuario para {user.username}")

        # Generar JWT tokens
        if usuario:
            token_access = JWTManager.generar_token_access(usuario)
            token_refresh = JWTManager.generar_token_refresh(usuario)
            JWTManager.guardar_tokens(usuario, token_access, token_refresh)
        else:
            # Fallback: generar tokens con el Django user directamente
            token_access = JWTManager.generar_token_access(user)
            token_refresh = JWTManager.generar_token_refresh(user)

        # Guardar tokens en sesión para que el frontend los capture
        request = backend.strategy.request
        request.session['auth0_access_token'] = token_access
        request.session['auth0_refresh_token'] = token_refresh
        request.session['auth0_user_id'] = str(user.id)
        request.session['auth0_username'] = user.username

        logger.info(f"JWT tokens generados para usuario {user.username} via Auth0")

    except Exception as e:
        logger.error(f"Error generando JWT en pipeline Auth0: {str(e)}", exc_info=True)
