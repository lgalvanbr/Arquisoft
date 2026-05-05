"""
Auth0 OAuth2 Backend para Django Social Auth
Implementación según laboratorio ISIS2503
"""
from django.contrib.auth.models import User
import requests
import json
import base64
from rest_framework import response
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
        ('email', 'email'),
        ('sub', 'sub'),
        ('https://finops-api/rol', 'rol'),
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
        print("=== USERINFO ===", userinfo)
        print("=== RESPONSE KEYS ===", list(response.keys()))

        return {'username': userinfo['nickname'], 

                'first_name': userinfo['name'], 

                'picture': userinfo['picture'], 

                'user_id': userinfo['sub'],
                'email': userinfo.get('email', ''),
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
    """
    auth0user = User.social_auth.filter(provider="auth0")[0] 

    accessToken = auth0user.extra_data['access_token'] 

    url = 'https://' + settings.SOCIAL_AUTH_AUTH0_DOMAIN + '/userinfo' 

    headers = {'authorization': 'Bearer ' + accessToken} 

    resp = requests.get(url, headers=headers) 

    userinfo = resp.json() 

    role = userinfo.get(f"https://{settings.SOCIAL_AUTH_AUTH0_DOMAIN}/rol") \
        or userinfo.get(f"https://{settings.SOCIAL_AUTH_AUTH0_DOMAIN}/role") \
        or userinfo.get("https://finops-api/rol") \
        or userinfo.get("https://finops-api/role") \
        or 'usuario'
        
    return (role) 
