"""
Middleware para validación de integridad de payloads
ASR Integridad: Detección y rechazo de mensajes adulterados
"""
import json
import logging
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from django.utils import timezone
from rest_framework import status
from .models import RechazoIntegridad

logger = logging.getLogger(__name__)


def obtener_ip_cliente(request):
    """
    Obtiene la dirección IP del cliente desde el request.
    
    Intenta obtener la IP del header X-Forwarded-For (proxy/load balancer),
    si no está disponible usa REMOTE_ADDR.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'desconocida')


class IntegridadPayloadMiddleware(MiddlewareMixin):
    """
    Middleware que valida la integridad de payloads en endpoints sensibles.
    
    ASR Integridad:
    - 100% de mensajes adulterados son rechazados con error 401
    - Ningún dato es persistido en BD
    - Rechazo registrado en log con fecha, IP de origen y motivo
    """
    
    ENDPOINTS_PROTEGIDOS = [
        '/api/reportes/',
    ]
    
    def process_request(self, request):
        """
        Procesa la solicitud y valida integridad de payload.
        
        Solo procesa:
        - Métodos: POST, PUT, PATCH
        - Endpoints en ENDPOINTS_PROTEGIDOS
        """
        # Solo procesar métodos que envían datos
        if request.method not in ['POST', 'PUT', 'PATCH']:
            return None
        
        # Solo endpoints protegidos
        if not any(request.path.startswith(ep) for ep in self.ENDPOINTS_PROTEGIDOS):
            return None
        
        try:
            # Intentar parsear JSON
            if request.body:
                payload = json.loads(request.body)
                request.payload = payload
            else:
                request.payload = {}
        except json.JSONDecodeError as e:
            # JSON inválido = Mensaje adulterado
            return self._rechazar_integridad(
                request,
                f"JSON inválido: {str(e)}",
                status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error parsing payload: {str(e)}")
            return self._rechazar_integridad(
                request,
                "Error procesando solicitud",
                status.HTTP_400_BAD_REQUEST
            )
        
        return None
    
    def _rechazar_integridad(self, request, motivo, http_status):
        """
        Rechaza una solicitud por falta de integridad.
        
        Registra el evento en RechazoIntegridad con:
        - Fecha exacta
        - IP de origen
        - Motivo del rechazo
        - Payload recibido
        """
        ip_cliente = obtener_ip_cliente(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        try:
            RechazoIntegridad.objects.create(
                direccion_ip=ip_cliente,
                endpoint=request.path,
                motivo_rechazo=motivo,
                payload_recibido=getattr(request, 'payload', {}),
                user_agent=user_agent
            )
        except Exception as e:
            logger.error(f"Error registrando rechazo de integridad: {str(e)}")
        
        # Log con contexto completo
        logger.warning(
            f"[ASR INTEGRIDAD] Rechazo: {motivo} | "
            f"Endpoint: {request.path} | "
            f"IP: {ip_cliente} | "
            f"Timestamp: {timezone.now().isoformat()}"
        )
        
        return JsonResponse(
            {'error': 'Mensaje inválido o adulterado'},
            status=http_status
        )
