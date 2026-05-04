"""
Auth0 OAuth2 Backend para Django Social Auth
Implementación según laboratorio ISIS2503
"""
import requests
from social_core.backends.oauth import BaseOAuth2
from django.conf import settings


class Auth0(BaseOAuth2):
    """Auth0 OAuth authentication backend"""

    name = 'auth0'
    SCOPE_SEPARATOR = ' '
    ACCESS_TOKEN_METHOD = 'POST'
    EXTRA_DATA = [
        ('picture', 'picture')
    ]

    def authorization_url(self):
        """Return the authorization endpoint."""
        return "https://" + self.setting('DOMAIN') + "/authorize"

    def access_token_url(self):
        """Return the token endpoint."""
        return "https://" + self.setting('DOMAIN') + "/oauth/token"

    def get_user_id(self, details, response):
        """Return current user id."""
        return details['user_id']

    def get_user_details(self, response):
        """Obtener detalles del usuario desde Auth0"""
        url = 'https://' + self.setting('DOMAIN') + '/userinfo'
        headers = {'authorization': 'Bearer ' + response['access_token']}
        resp = requests.get(url, headers=headers)
        userinfo = resp.json()

        return {
            'username': userinfo['nickname'],
            'first_name': userinfo['name'],
            'picture': userinfo['picture'],
            'user_id': userinfo['sub']
        }


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
