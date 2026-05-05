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
        ('id_token', 'id_token'),
    ]

    def authorization_url(self):
        return "https://" + self.setting('DOMAIN') + "/authorize"

    def access_token_url(self):
        return "https://" + self.setting('DOMAIN') + "/oauth/token"

    def get_user_id(self, details, response):
        return details.get('user_id') or response.get('sub')

    def get_user_details(self, response):
        url = 'https://' + self.setting('DOMAIN') + '/userinfo'
        headers = {'authorization': 'Bearer ' + response['access_token']}
        resp = requests.get(url, headers=headers)
        userinfo = resp.json()
 
        DOMAIN = settings.SOCIAL_AUTH_AUTH0_DOMAIN
 
        return {
            'username': userinfo['nickname'],
            'first_name': userinfo['name'],
            'picture': userinfo['picture'],
            'user_id': userinfo['sub'],
            'email': userinfo.get('email', ''),
            'empresa': userinfo.get(f'{DOMAIN}/empresa_id', ''),
            'rol': userinfo.get(f'{DOMAIN}/role', 'usuario'),
        }

def getRole(request):
    """
    Obtiene el rol del usuario leyendo el id_token guardado en extra_data.
    """
    try:
        user = request.user
        auth0user = user.social_auth.filter(provider="auth0")[0]
        DOMAIN = 'https://' + settings.SOCIAL_AUTH_AUTH0_DOMAIN

        # Intentar desde id_token
        id_token = auth0user.extra_data.get('id_token')
        if id_token:
            parts = id_token.split('.')
            payload = parts[1] + '=' * (4 - len(parts[1]) % 4)
            claims = json.loads(base64.urlsafe_b64decode(payload))
            print(f"=== getRole claims: {claims} ===")
            return claims.get(f'{DOMAIN}/rol', 'usuario')

        # Fallback a extra_data
        return auth0user.extra_data.get('rol', 'usuario')

    except Exception as e:
        print(f"=== getRole ERROR: {str(e)} ===")
        return 'usuario'