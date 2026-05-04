"""
Configuración de Auth0 para Django
"""
import os
from functools import lru_cache


class Auth0Settings:
    """Configuración centralizada de Auth0"""
    
    DOMAIN = os.getenv('AUTH0_DOMAIN', '')
    CLIENT_ID = os.getenv('AUTH0_CLIENT_ID', '')
    CLIENT_SECRET = os.getenv('AUTH0_CLIENT_SECRET', '')
    API_IDENTIFIER = os.getenv('AUTH0_API_IDENTIFIER', 'https://finops-api')
    ALGORITHMS = ["RS256"]
    
    @staticmethod
    def get_jwks_url():
        """Retorna la URL del JWKS (JSON Web Key Set) de Auth0"""
        return f"https://{Auth0Settings.DOMAIN}/.well-known/jwks.json"
    
    @staticmethod
    def get_issuer():
        """Retorna el issuer de Auth0"""
        return f"https://{Auth0Settings.DOMAIN}/"
