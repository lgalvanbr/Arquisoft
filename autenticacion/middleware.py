"""
Middleware de auditoría para registrar intentos de acceso.
Laboratorio ISIS2503 - Seguridad Integridad y Confidencialidad
"""
import json
from django.utils import timezone
from django.http import JsonResponse


class AuditLoggingMiddleware:
    """
    Middleware que registra:
    - Intentos de acceso no autorizado (403)
    - Intentos de manipulación (401)
    - Accesos exitosos a endpoints críticos (200)
    
    Incluye: fecha, IP origen, método, endpoint, usuario, status_code
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Endpoints críticos a auditar
        self.critical_endpoints = [
            '/api/reportes/',
            '/api/auth/me',
        ]
    
    def __call__(self, request):
        # Procesar request
        response = self.get_response(request)
        
        # Registrar si es un endpoint crítico o si hay error de autorización
        if self._should_audit(request, response):
            self._log_request(request, response)
        
        return response
    
    def _should_audit(self, request, response):
        """Determina si el request debe ser auditado"""
        # Auditar si es endpoint crítico Y (acceso no autorizado o exitoso)
        is_critical = any(ep in request.path for ep in self.critical_endpoints)
        is_auth_error = response.status_code in [401, 403]
        is_success = response.status_code == 200
        
        return is_critical and (is_auth_error or is_success)
    
    def _log_request(self, request, response):
        """Registra el request en AuditLog"""
        try:
            from autenticacion.models import AuditLog
            
            # Obtener IP cliente
            ip = self._get_client_ip(request)
            
            # Extraer token info si existe
            token_id = None
            try:
                if request.user.is_authenticated:
                    social_user = request.user.social_user.get(provider='auth0')
                    token_id = social_user.extra_data.get('sub', None)
            except:
                pass
            
            # Preparar data
            request_data = {
                'method': request.method,
                'endpoint': request.path,
                'query_string': request.GET.dict() if request.GET else {},
            }
            
            # Registrar
            AuditLog.objects.create(
                user=request.user if request.user.is_authenticated else None,
                action=self._get_action(response.status_code),
                resource=request.path,
                method=request.method,
                ip_address=ip,
                status_code=response.status_code,
                request_data=json.dumps(request_data),
                token_id=token_id,
                timestamp=timezone.now()
            )
        except Exception as e:
            # No fallar el request si hay error en auditoría
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error en auditoría: {str(e)}")
    
    def _get_action(self, status_code):
        """Determina la acción según status code"""
        if status_code == 401:
            return 'INTENTO_MANIPULACION'
        elif status_code == 403:
            return 'ACCESO_NO_AUTORIZADO'
        else:
            return 'ACCESO_EXITOSO'
    
    def _get_client_ip(self, request):
        """Extrae IP cliente real (considera proxies)"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'UNKNOWN')
        return ip
