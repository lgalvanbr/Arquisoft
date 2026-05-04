"""
Utilidades para autenticación, JWT y detección de anomalías
"""
# import jwt  # TODO: Fix cryptography DLL issue before re-enabling
import logging
from datetime import datetime, timedelta
from functools import wraps
from django.utils import timezone
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status
from .models import Token, AuditoriaAcceso, IntentoBloqueado

logger = logging.getLogger(__name__)


class JWTManager:
    """Gestor de tokens JWT - Versión simplificada (sin cryptography DLL)"""
    
    @staticmethod
    def generar_token_access(usuario):
        """Genera un token JWT de acceso (STUB - TODO: Implementar con JWT real)"""
        # STUB: Retorna un token dummy
        # En producción: jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
        return f"access_token_{usuario.id}_{int(datetime.utcnow().timestamp())}"
    
    @staticmethod
    def generar_token_refresh(usuario):
        """Genera un token JWT de refresco (STUB - TODO: Implementar con JWT real)"""
        # STUB: Retorna un token dummy
        # En producción: jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
        return f"refresh_token_{usuario.id}_{int(datetime.utcnow().timestamp())}"
    
    @staticmethod
    def guardar_tokens(usuario, token_access, token_refresh=None):
        """Guarda los tokens en la base de datos"""
        fecha_expiracion = timezone.now() + timedelta(hours=1)
        token_obj = Token.objects.create(
            usuario=usuario,
            token_access=token_access,
            token_refresh=token_refresh,
            fecha_expiracion=fecha_expiracion,
            activo=True
        )
        return token_obj
    
    @staticmethod
    def validar_token(token):
        """Valida un token JWT (STUB - TODO: Implementar validación real)"""
        # STUB: Retorna payload dummy
        # En producción: jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        try:
            if token and token.startswith(('access_token_', 'refresh_token_')):
                return {'valid': True}
            return None
        except Exception as e:
            logger.warning(f"Error validando token: {str(e)}")
            return None


class DetectorAnomalias:
    """
    Detector de anomalías para detección de ataques de fuerza bruta
    ASR: Detectar anomalías en menos de 2 segundos
    """
    
    CONFIGURACION = settings.SECURITY_SETTINGS
    
    @staticmethod
    def registrar_intento_fallido(username, direccion_ip, user_agent=None, motivo='Contraseña incorrecta'):
        """Registra un intento de login fallido y verifica si hay comportamiento anómalo"""
        AuditoriaAcceso.objects.create(
            username=username,
            direccion_ip=direccion_ip,
            user_agent=user_agent,
            tipo_evento='login_fallido',
            motivo_rechazo=motivo,
            detalles={'user_agent': user_agent}
        )
        
        if DetectorAnomalias._esta_bloqueado(username, direccion_ip):
            return False, "Acceso denegado temporalmente por múltiples intentos fallidos"
        
        ventana_segundos = DetectorAnomalias.CONFIGURACION['VENTANA_TIEMPO_INTENTOS_SEGUNDOS']
        fecha_desde = timezone.now() - timedelta(seconds=ventana_segundos)
        
        intentos_recientes = AuditoriaAcceso.objects.filter(
            username=username,
            tipo_evento='login_fallido',
            fecha_evento__gte=fecha_desde
        ).count()
        
        max_intentos = DetectorAnomalias.CONFIGURACION['MAX_INTENTOS_LOGIN']
        if intentos_recientes >= max_intentos:
            DetectorAnomalias._crear_bloqueo(username, direccion_ip, intentos_recientes)
            return False, f"Demasiados intentos fallidos. Acceso bloqueado por {DetectorAnomalias.CONFIGURACION['DURACION_BLOQUEO_SEGUNDOS']} segundos"
        
        return True, f"Intento fallido registrado ({intentos_recientes}/{max_intentos})"
    
    @staticmethod
    def registrar_intento_exitoso(usuario, direccion_ip, user_agent=None):
        """Registra un login exitoso y limpia intentos fallidos"""
        AuditoriaAcceso.objects.create(
            usuario=usuario,
            username=usuario.username,
            direccion_ip=direccion_ip,
            user_agent=user_agent,
            tipo_evento='login_exitoso'
        )
        
        DetectorAnomalias._desbloquear_si_existe(usuario.username, direccion_ip)
    
    @staticmethod
    def _esta_bloqueado(username, direccion_ip):
        """Verifica si existe un bloqueo activo por anomalía"""
        bloqueo = IntentoBloqueado.objects.filter(
            direccion_ip=direccion_ip,
            activo=True,
            fecha_bloqueo_hasta__gt=timezone.now()
        ).first()
        
        if bloqueo:
            return True
        
        bloqueo = IntentoBloqueado.objects.filter(
            username=username,
            activo=True,
            fecha_bloqueo_hasta__gt=timezone.now()
        ).first()
        
        return bloqueo is not None
    
    @staticmethod
    def _crear_bloqueo(username, direccion_ip, numero_intentos):
        """Crea un registro de bloqueo por anomalía detectada"""
        duracion_segundos = DetectorAnomalias.CONFIGURACION['DURACION_BLOQUEO_SEGUNDOS']
        fecha_bloqueo_hasta = timezone.now() + timedelta(seconds=duracion_segundos)
        
        IntentoBloqueado.objects.create(
            direccion_ip=direccion_ip,
            username=username,
            tipo_anomalia='multiples_intentos_fallidos',
            numero_intentos=numero_intentos,
            fecha_bloqueo_hasta=fecha_bloqueo_hasta,
            duracion_bloqueo_segundos=duracion_segundos,
            razon_bloqueo=f'Múltiples intentos fallidos de login detectados ({numero_intentos} intentos en {DetectorAnomalias.CONFIGURACION["VENTANA_TIEMPO_INTENTOS_SEGUNDOS"]}s)'
        )
        
        logger.warning(
            f"ANOMALÍA DETECTADA: {numero_intentos} intentos fallidos de {username} desde {direccion_ip}. "
            f"Bloqueado por {duracion_segundos} segundos"
        )
    
    @staticmethod
    def _desbloquear_si_existe(username, direccion_ip):
        """Desbloquea un usuario/IP si existe bloqueo previo"""
        IntentoBloqueado.objects.filter(
            username=username,
            activo=True
        ).update(activo=False)


class AuditoriaManager:
    """Gestor de auditoría de acceso"""
    
    @staticmethod
    def registrar_acceso_denegado(username, direccion_ip, razon, user_agent=None):
        """Registra un acceso denegado"""
        AuditoriaAcceso.objects.create(
            username=username,
            direccion_ip=direccion_ip,
            user_agent=user_agent,
            tipo_evento='acceso_denegado',
            motivo_rechazo=razon
        )
    
    @staticmethod
    def registrar_registro_exitoso(usuario, direccion_ip, user_agent=None):
        """Registra un registro exitoso"""
        AuditoriaAcceso.objects.create(
            usuario=usuario,
            username=usuario.username,
            direccion_ip=direccion_ip,
            user_agent=user_agent,
            tipo_evento='registro_exitoso'
        )
    
    @staticmethod
    def obtener_historial_acceso(usuario, dias=7):
        """Obtiene el historial de acceso de un usuario en los últimos N días"""
        fecha_desde = timezone.now() - timedelta(dias)
        return AuditoriaAcceso.objects.filter(
            usuario=usuario,
            fecha_evento__gte=fecha_desde
        ).order_by('-fecha_evento')


def require_scope(required_scope):
    """
    Decorador para validar que el usuario tiene un scope específico de Auth0.
    
    Uso:
        @require_scope('read:integrity_logs')
        def listar_rechazos_integridad(request):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # Obtener usuario autenticado
            usuario = request.user
            
            # Si no está autenticado, DRF lo rechazará antes de llegar aquí
            if not usuario or not usuario.is_authenticated:
                return Response(
                    {'error': 'Usuario no autenticado'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Verificar si es admin (tiene acceso a todo)
            if usuario.is_staff or usuario.is_superuser:
                return func(request, *args, **kwargs)
            
            # Verificar si tiene el scope requerido en Auth0
            # Los scopes se almacenan en la sesión o token de Auth0
            user_scopes = []
            
            # Intentar obtener scopes de múltiples lugares
            if hasattr(usuario, 'auth0_scopes'):
                user_scopes = usuario.auth0_scopes if isinstance(usuario.auth0_scopes, list) else [usuario.auth0_scopes]
            elif hasattr(request, 'auth') and hasattr(request.auth, 'scopes'):
                user_scopes = request.auth.scopes
            elif hasattr(request.session, 'auth0_scope'):
                user_scopes = request.session.get('auth0_scope', '').split()
            
            # Verificar si tiene el scope requerido
            if required_scope not in user_scopes:
                logger.warning(
                    f"Usuario {usuario.username} intentó acceder a endpoint que requiere '{required_scope}'. "
                    f"Scopes disponibles: {user_scopes}"
                )
                return Response(
                    {
                        'error': f'Permiso insuficiente. Requiere scope: {required_scope}',
                        'required_scope': required_scope,
                        'available_scopes': user_scopes
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Usuario tiene el scope, proceder con la función
            return func(request, *args, **kwargs)
        
        return wrapper
    return decorator
