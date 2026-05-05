"""
Pipeline personalizado de social_django para generar JWTs después de Auth0 login.

Este pipeline:
1. Se ejecuta después de la autenticación normal de social_django
2. Genera tokens JWT (access + refresh)
3. Los guarda en la sesión Django para que el frontend los capture
"""
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


def save_jwt_to_session(backend, user, response, *args, **kwargs):
    """
    Pipeline step que genera JWTs y los guarda en la sesión después de Auth0 login.
    
    Se ejecuta automáticamente después de que social_django crea/obtiene el usuario.
    """
    try:
        from autenticacion.utilities import JWTManager
        from autenticacion.models import Usuario
        
        # Obtener o crear el perfil Usuario asociado al Django User
        try:
            usuario = user.perfil_autenticacion
        except Exception:
            # Si no existe el perfil, intentar crearlo
            try:
                usuario = Usuario.objects.get(usuario_django=user)
            except Exception:
                logger.warning(f"No se encontró perfil Usuario para {user.username}")
                usuario = None
        
        # Extraer rol y empresa del response de Auth0
        extra_data = response.get('extra_data', {})
        if not extra_data:
            # social_django guarda los datos en user.social_auth
            social = user.social_auth.filter(provider='auth0').first()
            if social:
                extra_data = social.extra_data
        
        rol = extra_data.get('https://finops-api/rol', 'usuario')
        empresa = extra_data.get('https://finops-api/empresa', '')
        
        if usuario:
            # Actualizar rol y empresa si cambiaron
            if rol and usuario.rol != rol:
                usuario.rol = rol
                usuario.save()
            if empresa and str(usuario.empresa) != empresa:
                usuario.empresa = empresa
                usuario.save()
        
        # Generar JWT tokens
        # Usamos el Django user como base, pero el JWT Manager puede necesitar el perfil Usuario
        # Si no hay perfil, usamos el user directamente
        token_access = JWTManager.generar_token_access(usuario if usuario else user)
        token_refresh = JWTManager.generar_token_refresh(usuario if usuario else user)
        
        # Guardar tokens en sesión para que el frontend los capture
        request = backend.strategy.request
        request.session['auth0_access_token'] = token_access
        request.session['auth0_refresh_token'] = token_refresh
        request.session['auth0_user_id'] = str(user.id)
        request.session['auth0_username'] = user.username
        
        logger.info(f"JWT tokens generados para usuario {user.username} via Auth0")
        
    except Exception as e:
        logger.error(f"Error generando JWT en pipeline Auth0: {str(e)}", exc_info=True)
