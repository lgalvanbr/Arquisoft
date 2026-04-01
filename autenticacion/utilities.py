"""
Utilidades para autenticación, JWT y detección de anomalías
"""
import jwt
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from .models import Token, AuditoriaAcceso, IntentoBloqueado

logger = logging.getLogger(__name__)


class JWTManager:
    """Gestor de tokens JWT"""
    
    @staticmethod
    def generar_token_access(usuario):
        """Genera un token JWT de acceso"""
        payload = {
            'user_id': str(usuario.id),
            'username': usuario.username,
            'email': usuario.email,
            'rol': usuario.rol,
            'exp': datetime.utcnow() + timedelta(hours=1),
            'iat': datetime.utcnow(),
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
        return token
    
    @staticmethod
    def generar_token_refresh(usuario):
        """Genera un token JWT de refresco"""
        payload = {
            'user_id': str(usuario.id),
            'exp': datetime.utcnow() + timedelta(days=1),
            'iat': datetime.utcnow(),
            'type': 'refresh',
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
        return token
    
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
        """Valida un token JWT"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning(f"Token expirado: {token[:20]}...")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token inválido: {str(e)}")
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
        fecha_desde = timezone.now() - timedelta(days=dias)
        return AuditoriaAcceso.objects.filter(
            usuario=usuario,
            fecha_evento__gte=fecha_desde
        ).order_by('-fecha_evento')
