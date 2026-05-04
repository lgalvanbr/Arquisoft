"""
Backend de autenticación Auth0 integrado con Django REST Framework
Versión simplificada sin dependencias criptográficas para evitar errores de DLL
"""
import logging
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import Usuario, Empresa

logger = logging.getLogger(__name__)


class Auth0Authentication(BaseAuthentication):
    """
    Backend de autenticación temporalmente simplificado.
    
    En producción, esto decodificaría y validaría JWTs de Auth0.
    Por ahora, extrae Bearer token y lo adjunta al request para testing.
    """
    
    def authenticate(self, request):
        """
        Extrae token Bearer del header.
        En producción, aquí se valida el JWT con Auth0.
        """
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return None
        
        token = auth_header.split(' ', 1)[1].strip()
        if not token:
            return None
        
        try:
            # TODO: Implementar validación JWT con Auth0 cuando se resuelva error de DLL
            # Por ahora, retornamos un usuario dummy para testing
            # Este código será reemplazado con JWT validation completo
            
            # Extraer información del token (en producción sería decode + validate)
            # Para testing, creamos un usuario con información estática
            usuario = self._obtener_usuario_testing()
            
            logger.info(f"Autenticación exitosa (testing): {usuario.usuario_django.email}")
            
            return (usuario, token)
        
        except Exception as e:
            logger.error(f"Error de autenticación: {str(e)}")
            raise AuthenticationFailed(f'Error de autenticación: {str(e)}')
    
    def _obtener_usuario_testing(self):
        """
        Usuario de prueba para development.
        Será reemplazado con JWT validation real en producción.
        """
        try:
            usuario = Usuario.objects.select_related('empresa').first()
            if not usuario:
                # Si no hay usuario, crear uno de prueba
                from django.contrib.auth.models import User as DjangoUser
                empresa, _ = Empresa.objects.get_or_create(
                    id='1',
                    defaults={'nombre': 'Admin Empresa'}
                )
                django_user, _ = DjangoUser.objects.get_or_create(
                    username='admin@finops.local',
                    defaults={'email': 'admin@finops.local'}
                )
                usuario, _ = Usuario.objects.get_or_create(
                    usuario_django=django_user,
                    defaults={
                        'empresa': empresa,
                        'rol': 'admin',
                        'activo': True
                    }
                )
            
            # Adjuntar atributos de Auth0 para testing
            usuario.auth0_sub = 'testing-user'
            usuario.auth0_empresa_id = empresa.id
            usuario.auth0_rol = 'admin'
            
            return usuario
        
        except Exception as e:
            logger.error(f"Error creando usuario de testing: {str(e)}")
            raise AuthenticationFailed("No se pudo obtener usuario")
    
    def authenticate_header(self, request):
        """Retorna el valor para el header de autenticación"""
        return 'Bearer realm="finops-api"'
