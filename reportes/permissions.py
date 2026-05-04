"""
Decoradores y validadores para confidencialidad
ASR Confidencialidad: Detección de acceso no autorizado a empresas ajenas
"""
import logging
from functools import wraps
from django.http import JsonResponse
from django.utils import timezone
from rest_framework import status
from autenticacion.models import IntentoAccesoNoAutorizado

logger = logging.getLogger(__name__)


def obtener_ip_cliente(request):
    """
    Obtiene la dirección IP del cliente desde el request.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'desconocida')


def validar_acceso_empresa(view_func):
    """
    Decorador que valida que el usuario solo acceda a su empresa.
    
    ASR Confidencialidad:
    - Extrae empresa_id de la URL (parámetro de ruta)
    - Compara con empresa del usuario en JWT
    - Si no coinciden: rechaza con 403, registra en IntentoAccesoNoAutorizado
    - Registra: IP, token_identifier, empresa_solicitada, empresa_autorizada, fecha
    
    Uso:
        @validar_acceso_empresa
        def my_view(request, empresa_id):
            pass
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Obtener empresa_id de la URL
        empresa_solicitada_id = kwargs.get('empresa_id')
        
        if not empresa_solicitada_id:
            logger.warning(f"[ASR CONFIDENCIALIDAD] Endpoint sin empresa_id en ruta")
            return JsonResponse(
                {'error': 'empresa_id requerido en la ruta'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Obtener empresa del usuario (desde Auth0 en el JWT)
        usuario = request.user
        empresa_autorizada_id = getattr(usuario, 'auth0_empresa_id', None)
        
        # Si el usuario no tiene empresa asignada en el token
        if not empresa_autorizada_id:
            logger.warning(
                f"[ASR CONFIDENCIALIDAD] Usuario sin empresa_id en token: {usuario.usuario_django.email}"
            )
            return JsonResponse(
                {'error': 'Usuario sin empresa asignada'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Comparar: ¿Intenta acceder a una empresa distinta a la suya?
        if str(empresa_solicitada_id) != str(empresa_autorizada_id):
            ip_cliente = obtener_ip_cliente(request)
            token_identifier = request.auth[:50] if request.auth else 'unknown'  # Primeros 50 chars del token
            
            # Registrar intento de acceso no autorizado
            try:
                IntentoAccesoNoAutorizado.objects.create(
                    usuario=usuario,
                    empresa_solicitada_id=empresa_solicitada_id,
                    empresa_autorizada_id=empresa_autorizada_id,
                    endpoint=request.path,
                    direccion_ip=ip_cliente,
                    token_identifier=token_identifier
                )
            except Exception as e:
                logger.error(f"Error registrando acceso no autorizado: {str(e)}")
            
            # Log detallado
            logger.warning(
                f"[ASR CONFIDENCIALIDAD] Intento de acceso no autorizado | "
                f"Usuario: {usuario.usuario_django.email} | "
                f"Empresa solicitada: {empresa_solicitada_id} | "
                f"Empresa autorizada: {empresa_autorizada_id} | "
                f"Endpoint: {request.path} | "
                f"IP: {ip_cliente} | "
                f"Timestamp: {timezone.now().isoformat()}"
            )
            
            # Rechazar acceso
            return JsonResponse(
                {'error': 'No autorizado para acceder a esta empresa'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Acceso permitido - continuar con la vista
        return view_func(request, *args, **kwargs)
    
    return wrapper
