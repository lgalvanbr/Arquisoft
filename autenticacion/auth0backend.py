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
        ('access_token', 'access_token'),
        ('id_token', 'id_token'),  # guardar id_token para leer claims
    ]

    def authorization_url(self):
        return "https://" + self.setting('DOMAIN') + "/authorize"

    def access_token_url(self):
        return "https://" + self.setting('DOMAIN') + "/oauth/token"

    def get_user_id(self, details, response):
        return details.get('user_id') or response.get('sub')

    def get_user_details(self, response):
        """Obtener detalles del usuario desde el id_token (JWT decodificable)"""
        try:
            DOMAIN = settings.SOCIAL_AUTH_AUTH0_DOMAIN

            # Leer claims desde el id_token (es JWT, se puede decodificar)
            id_token = response.get('id_token')
            claims = self._extract_from_jwt(id_token) if id_token else {}

            # Fallback a /userinfo si no hay id_token
            if not claims or 'sub' not in claims:
                access_token = response.get('access_token')
                url = 'https://' + self.setting('DOMAIN') + '/userinfo'
                headers = {'authorization': 'Bearer ' + access_token}
                resp = requests.get(url, headers=headers, timeout=5)
                resp.raise_for_status()
                claims = resp.json()

            username = claims.get('nickname') or claims.get('email', '').split('@')[0]

            return {
                'username': username,
                'first_name': claims.get('name', ''),
                'picture': claims.get('picture', ''),
                'user_id': claims.get('sub'),
                'email': claims.get('email', ''),
                'empresa': claims.get(f'{DOMAIN}/empresa_id', ''),
                'rol': claims.get(f'{DOMAIN}/rol', 'usuario'),
            }
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error en get_user_details: {str(e)}", exc_info=True)
            return {
                'username': response.get('sub', 'unknown'),
                'first_name': '',
                'picture': '',
                'user_id': response.get('sub'),
                'email': '',
                'empresa': '',
                'rol': 'usuario',
            }

    def _extract_from_jwt(self, token):
        """Extrae claims del id_token JWT sin validar firma"""
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return {}
            payload = parts[1]
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += '=' * padding
            decoded = base64.urlsafe_b64decode(payload)
            return json.loads(decoded)
        except Exception:
            return {}


def getRole(request):
    """
    Obtiene el rol del usuario leyendo el id_token guardado en extra_data.
    El id_token es un JWT decodificable que contiene los custom claims de Auth0.
    """
    try:
        user = request.user
        auth0user = user.social_auth.filter(provider="auth0")[0]
        DOMAIN = settings.SOCIAL_AUTH_AUTH0_DOMAIN

        # Leer el id_token guardado en extra_data
        id_token = auth0user.extra_data.get('id_token')
        if id_token:
            parts = id_token.split('.')
            payload = parts[1] + '=' * (4 - len(parts[1]) % 4)
            claims = json.loads(base64.urlsafe_b64decode(payload))
            return claims.get(f'{DOMAIN}/rol', 'usuario')

        # Fallback: leer del extra_data mapeado
        return auth0user.extra_data.get('rol', 'usuario')

    except Exception:
        return 'usuario'