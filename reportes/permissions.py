"""
Validadores de permisos para segregación de datos por empresa.
Laboratorio ISIS2503 - Seguridad Integridad y Confidencialidad
"""
from django.http import JsonResponse
from functools import wraps
from autenticacion.auth0backend import getRole


def require_authentication(view_func):
    """Decorador para requerir usuario autenticado"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({
                'error': 'No autorizado',
                'detail': 'Usuario no autenticado'
            }, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper


def check_company_access(view_func):
    """
    Decorador para validar acceso a empresa solicitada.
    Evita que usuario de Empresa A acceda a datos de Empresa B.
    
    Extrae company_id de:
    1. URL parameter (reportes/costos/empresa/<company_id>)
    2. Request body (JSON)
    3. Query parameter (?company_id=...)
    
    Compara con empresa del usuario en el token Auth0.
    Si no coinciden → 403 Forbidden + log de intento.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # 1. Obtener company_id solicitado
        requested_company = kwargs.get('empresa_id') or \
                           request.GET.get('company_id') or \
                           request.GET.get('empresa_id')
        
        if not requested_company:
            try:
                data = request.POST or {}
                requested_company = data.get('company_id') or data.get('empresa_id')
            except:
                pass
        
        if not requested_company:
            return JsonResponse({
                'error': 'Parámetro requerido',
                'detail': 'company_id o empresa_id no especificado'
            }, status=400)
        
        # 2. Obtener empresa del usuario autenticado
        user_company = None
        try:
            # Desde Auth0 custom claims mapeados por EXTRA_DATA
            if request.user.is_authenticated:
                # social_user.extra_data contiene claims mapeados:
                # 'dev-vy27mzsmkwosyqhr.us.auth0.com/empresa_id' -> 'empresa'
                try:
                    social_user = request.user.social_auth.filter(provider='auth0').first()
                    if not social_user:
                        user_company = None
                    else:
                        extra_data = social_user.extra_data
                        user_company = extra_data.get('empresa', None)
                except:
                    user_company = None
        except:
            pass
        
        # 3. Validar coincidencia de empresa
        if not user_company:
            # Si no hay empresa en token, rechazar
            return JsonResponse({
                'error': 'Acceso Denegado',
                'detail': 'No se encontró información de empresa en el token'
            }, status=403)
        
        if str(user_company).upper() != str(requested_company).upper():
            # INTENTO DE ACCESO NO AUTORIZADO - REGISTRAR
            from autenticacion.models import IntentoAccesoNoAutorizado
            from django.utils import timezone
            import json
            
            # Extraer token ID si existe
            token_id = None
            try:
                social_user = request.user.social_auth.filter(provider='auth0').first()
                token_id = social_user.extra_data.get('sub', 'UNKNOWN') if social_user else 'UNKNOWN'
            except:
                token_id = 'UNKNOWN'
            
            IntentoAccesoNoAutorizado.objects.create(
                usuario=request.user if request.user.is_authenticated else None,
                empresa_solicitada_id=requested_company,
                empresa_autorizada_id=user_company,
                endpoint=request.path,
                direccion_ip=get_client_ip(request),
                token_identifier=token_id,
                fecha_intento=timezone.now()
            )
            
            return JsonResponse({
                'error': 'Acceso Denegado',
                'detail': 'No tienes permiso para acceder a esta empresa'
            }, status=403)
        
        # 4. Pasar al siguiente middleware/view
        return view_func(request, *args, **kwargs)
    
    return wrapper


def get_client_ip(request):
    """Extrae IP cliente real (considera proxies y load balancers)"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def check_admin_role(view_func):
    """Decorador para requerir rol admin"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({
                'error': 'No autorizado',
                'detail': 'Usuario no autenticado'
            }, status=401)
        
        try:
            role = getRole(request.user)
            if role != 'admin':
                return JsonResponse({
                    'error': 'Acceso Denegado',
                    'detail': f'Se requiere rol admin. Tu rol: {role}'
                }, status=403)
        except:
            return JsonResponse({
                'error': 'Acceso Denegado',
                'detail': 'No se pudo validar el rol'
            }, status=403)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper
