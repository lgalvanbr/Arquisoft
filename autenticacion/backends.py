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

        ip = self._obtener_ip(request)
        token_id = token[:20]

        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            self._registrar_rechazo(ip, 'Token expirado', token_id)
            raise AuthenticationFailed('Token expirado')
        except jwt.InvalidTokenError:
            self._registrar_rechazo(ip, 'Token inválido o adulterado', token_id)
            raise AuthenticationFailed('Token inválido')

        user_id = payload.get('user_id')
        if not user_id:
            self._registrar_rechazo(ip, 'Token sin user_id', token_id)
            raise AuthenticationFailed('Token sin user_id')

        try:
            from .models import Usuario
            usuario = Usuario.objects.select_related('usuario_django').get(id=user_id)
        except Usuario.DoesNotExist:
            self._registrar_rechazo(ip, 'Usuario no encontrado', token_id)
            raise AuthenticationFailed('Usuario no encontrado')

        if not usuario.activo:
            self._registrar_rechazo(ip, 'Usuario inactivo', token_id)
            raise AuthenticationFailed('Usuario inactivo')

        return (usuario, token)

    def authenticate_header(self, request):
        return 'Bearer realm="api"'

    def _obtener_ip(self, request):
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '0.0.0.0')

    def _registrar_rechazo(self, ip, motivo, token_id):
        try:
            from .models import AuditoriaAcceso
            AuditoriaAcceso.objects.create(
                username='desconocido',
                direccion_ip=ip or '0.0.0.0',
                tipo_evento='acceso_denegado',
                motivo_rechazo=motivo,
                detalles={'token_id': token_id, 'motivo': motivo}
            )
            logger.warning(
                f"Token rechazado desde {ip}: {motivo} (token_id: {token_id}...)"
            )
        except Exception as e:
            logger.error(f"Error registrando rechazo de token: {e}")
