"""
Validadores de integridad de payload.
Detecta manipulación de mensajes de solicitud.
ASR Disponibilidad: Detección de SQL Injection en reportes de costos.
Laboratorio ISIS2503 - Seguridad Integridad y Confidencialidad
"""
import hmac
import hashlib
import json
import re
from django.http import JsonResponse
from functools import wraps
from django.conf import settings
from autenticacion.models import AuditLog
from django.utils import timezone


# Patrones de SQL Injection para detectar ataques
SQL_INJECTION_PATTERNS = [
    r"(?i)\b(UNION|SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|EXEC|EXECUTE)\b",
    r"(--|\/\*|\*\/|;)",
    r"(?i)\b(OR|AND)\b\s+[\d\w]+\s*=\s*[\d\w]+",
    r"(?i)\b(SLEEP|WAITFOR|BENCHMARK|LOAD_FILE|INTO\s+OUTFILE|INTO\s+DUMPFILE)\b",
    r"(?i)(\bDECLARE\b|\bEXEC\b|\bCAST\b|\bCONVERT\b)",
    r"(?i)\b(1\s*=\s*1|1\s*=\s*'1'|'\s*OR\s+')",
]

SQL_INJECTION_REGEX = [re.compile(p) for p in SQL_INJECTION_PATTERNS]


def _detect_sql_injection(value):
    """
    Detecta patrones de SQL Injection en un string.
    Retorna True si se detecta un intento de inyección.
    """
    if not value or not isinstance(value, str):
        return False
    for regex in SQL_INJECTION_REGEX:
        if regex.search(value):
            return True
    return False


def validate_payload_integrity(view_func):
    """
    Decorador para validar integridad de payloads.
    
    Verifica que el request NO ha sido adulterado.
    El cliente debe incluir header: X-Payload-Signature
    
    Signature = HMAC-SHA256(payload_body, SECRET_KEY)
    
    Si la firma no coincide:
    - 100% de mensajes adulterados son rechazados
    - Ningún dato es persistido
    - El rechazo es registrado en log con fecha, IP y motivo
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # 1. Solo validar en métodos que envían data
        if request.method not in ['POST', 'PUT', 'PATCH']:
            return view_func(request, *args, **kwargs)
        
        # 2. Obtener firma del header
        received_signature = request.META.get('HTTP_X_PAYLOAD_SIGNATURE', '')
        
        if not received_signature:
            # Sin firma = rechazo
            _log_integrity_violation(
                request,
                'MISSING_SIGNATURE',
                'Header X-Payload-Signature no presente'
            )
            return JsonResponse({
                'error': 'No autorizado',
                'detail': 'Falta header de integridad: X-Payload-Signature'
            }, status=401)
        
        # 3. Leer body del request
        try:
            if request.content_type == 'application/json':
                request.body.seek(0)  # Reset stream
                payload_body = request.body.read()
                if not payload_body:
                    payload_body = b'{}'
            else:
                payload_body = request.body
        except:
            payload_body = b'{}'
        
        # 4. Calcular firma esperada
        secret = settings.SECRET_KEY.encode()
        expected_signature = hmac.new(
            secret,
            payload_body,
            hashlib.sha256
        ).hexdigest()
        
        # 5. Comparar firmas (timing-safe)
        if not hmac.compare_digest(received_signature, expected_signature):
            # Manipulación detectada → RECHAZO
            _log_integrity_violation(
                request,
                'PAYLOAD_TAMPERED',
                f'Firma inválida. Esperada: {expected_signature[:16]}..., Recibida: {received_signature[:16]}...'
            )
            return JsonResponse({
                'error': 'No autorizado',
                'detail': 'Payload adulterado. Integridad comprometida.'
            }, status=401)
        
        # 6. Payload válido → continuar
        return view_func(request, *args, **kwargs)
    
    return wrapper


def _log_integrity_violation(request, reason, detail):
    """Registra violación de integridad en RechazoIntegridad"""
    try:
        from autenticacion.models import RechazoIntegridad
        
        RechazoIntegridad.objects.create(
            direccion_ip=_get_client_ip(request),
            endpoint=request.path,
            motivo_rechazo=reason,
            payload_recibido={
                'detail': detail,
                'timestamp': timezone.now().isoformat()
            },
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )
    except Exception as e:
        # Log fallback si hay error en base de datos
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error registrando violación de integridad: {str(e)}")


def _get_client_ip(request):
    """Extrae IP cliente (considera proxies)"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', 'UNKNOWN')
    return ip


def validate_report_request(view_func):
    """
    Decorador específico para validar requests de reportes.
    ASR Disponibilidad: Detección de SQL Injection.
    
    Verifica:
    - empresa_id no es None
    - empresa_id es string válido
    - No hay inyección SQL (caracteres especiales y patrones de ataque)
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        empresa_id = kwargs.get('empresa_id')
        
        # Validar formato
        if not empresa_id:
            return JsonResponse({
                'error': 'Parámetro requerido',
                'detail': 'empresa_id es obligatorio'
            }, status=400)
        
        # ASR Disponibilidad: Detección de SQL Injection
        if _detect_sql_injection(empresa_id):
            _log_integrity_violation(
                request,
                'SQL_INJECTION_ATTEMPTED',
                f'Se detectó intento de SQL Injection en empresa_id: {empresa_id}'
            )
            return JsonResponse({
                'error': 'No autorizado',
                'detail': 'SQL Injection detectado. Solicitud rechazada.'
            }, status=401)
        
        # Validar que es string alfanumérico (sin inyecciones básicas)
        if not isinstance(empresa_id, str) or not empresa_id.replace('.', '').replace('-', '').replace('_', '').isalnum():
            _log_integrity_violation(
                request,
                'INVALID_EMPRESA_ID_FORMAT',
                f'empresa_id contiene caracteres inválidos: {empresa_id}'
            )
            return JsonResponse({
                'error': 'Formato inválido',
                'detail': 'empresa_id contiene caracteres no permitidos'
            }, status=400)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper
