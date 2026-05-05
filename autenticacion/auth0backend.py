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
    ]

    def authorization_url(self):
        return "https://" + self.setting('DOMAIN') + "/authorize"

    def access_token_url(self):
        return "https://" + self.setting('DOMAIN') + "/oauth/token"

    def get_user_id(self, details, response):
        return details['user_id']

    def get_user_details(self, response):

        url = 'https://' + self.setting('DOMAIN') + '/userinfo' 

        headers = {'authorization': 'Bearer ' + response['access_token']} 

        resp = requests.get(url, headers=headers) 

        userinfo = resp.json() 

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
    user = request.user 

    try:
        auth0user = user.social_auth.filter(provider="auth0")[0]
        if not auth0user:
            print("=== getRole: NO social_auth para provider auth0 ===")
            return None
    
        accessToken = auth0user.extra_data['access_token']
        if not accessToken:
            print("=== getRole: NO access_token en extra_data ===")
            print("=== getRole: extra_data keys:", list(auth0user.extra_data.keys()))
            return None

        print("=== getRole: access_token len:", len(accessToken))

        url = 'https://' + settings.SOCIAL_AUTH_AUTH0_DOMAIN + '/userinfo' 
        headers = {'authorization': 'Bearer ' + accessToken} 

        print("=== getRole: GET", url)

        resp = requests.get(url, headers=headers) 
        print("=== getRole: status", resp.status_code)

        userinfo = resp.json() 
        print("=== getRole: userinfo:", json.dumps(userinfo, indent=2))

        role = userinfo[f"{settings.SOCIAL_AUTH_AUTH0_DOMAIN}/role"] 
        print("=== getRole: role encontrado:", role)
        
        return role
    except Exception as e:
        return None 
