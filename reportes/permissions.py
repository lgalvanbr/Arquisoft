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
    
    Logica basada en rol de Auth0:
    - Admin: puede generar reportes de CUALQUIER empresa (sin verificar empresa)
    - Manager: solo puede generar reportes de SU empresa asignada
    
    La empresa del usuario se obtiene del modelo local Usuario (DB), no del token.
    
    Extrae company_id de:
    1. URL parameter (reportes/costos/empresa/<company_id>)
    2. Request body (JSON)
    3. Query parameter (?company_id=...)
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
                'error': 'Parametro requerido',
                'detail': 'company_id o empresa_id no especificado'
            }, status=400)
        
        # 2. Obtener rol via getRole
        role = getRole(request)
        allowed_roles = ["Admin", "Manager"]
        
        print("=== check_company_access: role:", role)
        print("=== check_company_access: allowed_roles:", allowed_roles)
        print("=== check_company_access: requested_company:", requested_company)
        
        if role in allowed_roles:
            if role == "Admin":
                # Admin puede acceder a cualquier empresa
                print("=== check_company_access: Admin - acceso permitido a cualquier empresa ===")
                return view_func(request, *args, **kwargs)
            
            elif role == "Manager":
                # Manager solo puede acceder a su propia empresa
                from autenticacion.models import Usuario as UsuarioModel
                user_company = None
                try:
                    local_usuario = UsuarioModel.objects.filter(usuario_django=request.user).first()
                    if local_usuario and local_usuario.empresa:
                        user_company = str(local_usuario.empresa.id)
                except:
                    pass
                
                print("=== check_company_access: Manager - user_company:", user_company)
                
                if not user_company:
                    return JsonResponse({
                        'error': 'Acceso Denegado',
                        'detail': 'No se encontro informacion de empresa para este usuario'
                    }, status=403)
                
                if str(user_company).upper() != str(requested_company).upper():
                    # INTENTO DE ACCESO NO AUTORIZADO - REGISTRAR
                    _log_unauthorized_access(request, requested_company, user_company)
                    return JsonResponse({
                        'error': 'Acceso Denegado',
                        'detail': 'No tienes permiso para acceder a esta empresa'
                    }, status=403)
                
                print("=== check_company_access: Manager - acceso permitido a su empresa ===")
                return view_func(request, *args, **kwargs)
        
        # 3. Rol no autorizado o no reconocido - verificar empresa del usuario local
        from autenticacion.models import Usuario as UsuarioModel
        user_company = None
        try:
            local_usuario = UsuarioModel.objects.filter(usuario_django=request.user).first()
            if local_usuario and local_usuario.empresa:
                user_company = str(local_usuario.empresa.id)
        except:
            pass
        
        print("=== check_company_access: rol no reconocido - user_company:", user_company)
        
        if not user_company:
            return JsonResponse({
                'error': 'Acceso Denegado',
                'detail': 'No se encontro informacion de empresa para este usuario'
            }, status=403)
        
        if str(user_company).upper() != str(requested_company).upper():
            _log_unauthorized_access(request, requested_company, user_company)
            return JsonResponse({
                'error': 'Acceso Denegado',
                'detail': 'No tienes permiso para acceder a esta empresa'
            }, status=403)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def _log_unauthorized_access(request, requested_company, user_company):
    """Registra intento de acceso no autorizado en la BD"""
    from autenticacion.models import IntentoAccesoNoAutorizado
    from django.utils import timezone
    
    token_id = 'UNKNOWN'
    try:
        social_user = request.user.social_auth.filter(provider='auth0').first()
        if social_user:
            token_id = social_user.extra_data.get('sub', 'UNKNOWN')
    except:
        pass
    
    IntentoAccesoNoAutorizado.objects.create(
        usuario=request.user if request.user.is_authenticated else None,
        empresa_solicitada_id=requested_company,
        empresa_autorizada_id=user_company,
        endpoint=request.path,
        direccion_ip=get_client_ip(request),
        token_identifier=token_id,
        fecha_intento=timezone.now()
    )


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
            role = getRole(request)
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
