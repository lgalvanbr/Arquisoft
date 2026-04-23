"""
Backend de autenticación JWT para Django REST Framework.
Valida el token Bearer del header Authorization y retorna el Usuario del perfil.
"""
import jwt
import logging
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

logger = logging.getLogger(__name__)


class JWTAuthentication(BaseAuthentication):
    """Autenticación JWT custom para DRF."""

    def authenticate(self, request):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return None

        token = auth_header.split(' ', 1)[1].strip()
        if not token:
            return None

        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token expirado')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('Token inválido')

        user_id = payload.get('user_id')
        if not user_id:
            raise AuthenticationFailed('Token sin user_id')

        try:
            from .models import Usuario
            usuario = Usuario.objects.select_related('usuario_django').get(id=user_id)
        except Usuario.DoesNotExist:
            raise AuthenticationFailed('Usuario no encontrado')

        if not usuario.activo:
            raise AuthenticationFailed('Usuario inactivo')

        return (usuario, token)

    def authenticate_header(self, request):
        return 'Bearer realm="api"'
