"""
Auth0 OAuth2 Backend para Django Social Auth
Implementación según laboratorio ISIS2503
"""
import requests
import json
import base64
from social_core.backends.oauth import BaseOAuth2
from django.conf import settings


class Auth0(BaseOAuth2):
    """Auth0 OAuth authentication backend"""

    name = 'auth0'
    SCOPE_SEPARATOR = ' '
    ACCESS_TOKEN_METHOD = 'POST'
    # Mapear los custom claims de Auth0 a nombres simples para EXTRA_DATA
    # Auth0 retorna claims con namespace: dev-vy27mzsmkwosyqhr.us.auth0.com/empresa_id
    # Los mapeamos a nombres simples en extra_data: 'empresa', 'rol'
    EXTRA_DATA = [
        ('picture', 'picture'),
        ('email', 'email'),
        ('sub', 'sub'),
        ('dev-vy27mzsmkwosyqhr.us.auth0.com/empresa_id', 'empresa'),
        ('dev-vy27mzsmkwosyqhr.us.auth0.com/rol', 'rol'),
    ]

    def authorization_url(self):
        """Return the authorization endpoint."""
        return "https://" + self.setting('DOMAIN') + "/authorize"

    def access_token_url(self):
        """Return the token endpoint."""
        return "https://" + self.setting('DOMAIN') + "/oauth/token"

    def get_user_id(self, details, response):
        """Return current user id."""
        return details.get('user_id') or response.get('sub')

    def get_user_details(self, response):
        """Obtener detalles del usuario desde Auth0 usando el id_token JWT
        
        El id_token es un JWT que contiene claims del usuario.
        El access_token es opaco y no se puede decodificar.
        Usamos el id_token para extraer los custom claims de Auth0.
        """
        try:
            NAMESPACE = 'https://dev-vy27mzsmkwosyqhr.us.auth0.com'
            
            # id_token es JWT decodificable, contiene los custom claims
            id_token = response.get('id_token')
            claims = self._extract_from_jwt(id_token) if id_token else {}
            
            # Si no hay id_token o falla la extracción, llamar a /userinfo endpoint
            if not claims or 'sub' not in claims:
                access_token = response.get('access_token')
                url = 'https://' + self.setting('DOMAIN') + '/userinfo'
                headers = {'authorization': 'Bearer ' + access_token}
                resp = requests.get(url, headers=headers, timeout=5)
                resp.raise_for_status()
                claims = resp.json()
            
            # Extraer detalles del usuario
            username = claims.get('nickname') or claims.get('email', '').split('@')[0]
            first_name = claims.get('name', '')
            
            return {
                'username': username,
                'first_name': first_name,
                'picture': claims.get('picture', ''),
                'user_id': claims.get('sub'),
                'email': claims.get('email', ''),
                'empresa': claims.get(f'{NAMESPACE}/empresa_id', 'BITE.CO'),
                'rol': claims.get(f'{NAMESPACE}/rol', 'usuario'),
            }
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error en get_user_details: {str(e)}", exc_info=True)
            # Retornar valores por defecto si algo falla
            return {
                'username': response.get('sub', 'unknown'),
                'first_name': '',
                'picture': '',
                'user_id': response.get('sub'),
                'email': '',
                'empresa': 'BITE.CO',
                'rol': 'usuario',
            }

    def _extract_from_jwt(self, token):
        """Extrae claims del JWT sin validar firma (confiamos en HTTPS)"""
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return {}
            
            # Decodificar payload (segunda parte del JWT)
            payload = parts[1]
            # Agregar padding si es necesario
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += '=' * padding
            
            decoded = base64.urlsafe_b64decode(payload)
            return json.loads(decoded)
        except Exception:
            return {}


def getRole(user):
    """
    Obtiene el rol del usuario desde el token de Auth0.
    Se utiliza para validar permisos en vistas protegidas.
    
    Args:
        user: Usuario autenticado (Django User)
    
    Returns:
        str: Rol del usuario ('admin', 'gerente', 'usuario', etc.)
    """
    try:
        # Obtener el social auth asociado al usuario
        social_user = user.social_user.get(provider='auth0')
        
        # El rol está en extra_data del social auth
        # EXTRA_DATA mapea 'dev-vy27mzsmkwosyqhr.us.auth0.com/rol' -> 'rol'
        extra_data = social_user.extra_data
        
        # El rol ya está mapeado a 'rol' por EXTRA_DATA
        rol = extra_data.get('rol', 'usuario')
        
        return rol
    except Exception as e:
        # Si no se encuentra el rol, retornar rol por defecto
        return 'usuario'
