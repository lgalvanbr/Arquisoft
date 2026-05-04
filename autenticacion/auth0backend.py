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
    EXTRA_DATA = [
        ('picture', 'picture'),
        ('email', 'email'),
        ('sub', 'sub'),
        ('https://finops-api/empresa', 'empresa'),
        ('https://finops-api/rol', 'rol'),
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
        """Obtener detalles del usuario desde Auth0 usando el token JWT"""
        try:
            # Intentar extraer info del JWT primero (offline, sin HTTP call)
            access_token = response.get('access_token')
            userinfo = self._extract_from_jwt(access_token) if access_token else {}
            
            # Si JWT extraction falla, llamar a /userinfo endpoint
            if not userinfo or 'sub' not in userinfo:
                url = 'https://' + self.setting('DOMAIN') + '/userinfo'
                headers = {'authorization': 'Bearer ' + access_token}
                resp = requests.get(url, headers=headers, timeout=5)
                resp.raise_for_status()
                userinfo = resp.json()
            
            # Extraer detalles del usuario
            username = userinfo.get('nickname') or userinfo.get('email', '').split('@')[0]
            first_name = userinfo.get('name', '')
            
            return {
                'username': username,
                'first_name': first_name,
                'picture': userinfo.get('picture', ''),
                'user_id': userinfo.get('sub'),
                'email': userinfo.get('email', ''),
                'empresa': userinfo.get('https://finops-api/empresa', 'BITE.CO'),
                'rol': userinfo.get('https://finops-api/rol', 'usuario'),
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
        extra_data = social_user.extra_data
        
        # Auth0 puede enviar el rol en diferentes formatos
        # 1. En custom claims del token (namespace/role)
        rol = extra_data.get('https://finops-api/rol', None)
        
        # 2. O en el campo 'role' directo
        if not rol:
            rol = extra_data.get('role', 'usuario')
        
        return rol
    except Exception as e:
        # Si no se encuentra el rol, retornar rol por defecto
        return 'usuario'
