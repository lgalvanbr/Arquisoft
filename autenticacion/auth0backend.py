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
        }

def getRole(request): 

    user = request.user 

    auth0user = user.social_auth.filter(provider="auth0")[0] 

    accessToken = auth0user.extra_data['access_token'] 

    url = 'https://' + settings.SOCIAL_AUTH_AUTH0_DOMAIN + '/userinfo' 

    headers = {'authorization': 'Bearer ' + accessToken} 

    resp = requests.get(url, headers=headers) 

    userinfo = resp.json() 

    role = userinfo[f"{settings.SOCIAL_AUTH_AUTH0_DOMAIN}/role"] 

    return (role) 