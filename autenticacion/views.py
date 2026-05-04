"""
Views para el servicio de autenticación
"""
import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.contrib.auth import authenticate
from django.utils import timezone
from django.db import transaction

from .models import Usuario, Permiso, RolPermiso, RechazoIntegridad, IntentoAccesoNoAutorizado
from .utilities import JWTManager, DetectorAnomalias, AuditoriaManager, require_scope

logger = logging.getLogger(__name__)


def obtener_ip_cliente(request):
    """Obtiene la dirección IP del cliente"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def obtener_user_agent(request):
    """Obtiene el User-Agent del cliente"""
    return request.META.get('HTTP_USER_AGENT', '')


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """Endpoint para registrar un nuevo usuario"""
    try:
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        empresa = request.data.get('empresa', '')
        
        if not all([username, email, password]):
            return Response(
                {'error': 'username, email y password son requeridos'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if Usuario.objects.filter(usuario_django__username=username).exists():
            return Response(
                {'error': 'El usuario ya existe'},
                status=status.HTTP_409_CONFLICT
            )
        
        if Usuario.objects.filter(usuario_django__email=email).exists():
            return Response(
                {'error': 'El email ya está registrado'},
                status=status.HTTP_409_CONFLICT
            )
        
        with transaction.atomic():
            usuario = Usuario.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                empresa=empresa,
                rol='usuario',
            )

            ip_cliente = obtener_ip_cliente(request)
            user_agent = obtener_user_agent(request)
            AuditoriaManager.registrar_registro_exitoso(usuario, ip_cliente, user_agent)

        return Response(
            {
                'mensaje': 'Usuario registrado exitosamente',
                'usuario': {
                    'id': str(usuario.id),
                    'username': usuario.username,
                    'email': usuario.email,
                    'empresa': usuario.empresa,
                }
            },
            status=status.HTTP_201_CREATED
        )
    
    except Exception as e:
        logger.error(f"Error en registro: {str(e)}")
        return Response(
            {'error': 'Error al registrar usuario'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """Endpoint para login de usuario"""
    try:
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response(
                {'error': 'username y password son requeridos'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ip_cliente = obtener_ip_cliente(request)
        user_agent = obtener_user_agent(request)
        
        if DetectorAnomalias._esta_bloqueado(username, ip_cliente):
            AuditoriaManager.registrar_acceso_denegado(
                username, ip_cliente,
                'Cuenta bloqueada por múltiples intentos fallidos',
                user_agent
            )
            return Response(
                {'error': 'Acceso denegado temporalmente. Intente más tarde'},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        # authenticate() devuelve Django User, no Usuario
        django_user = authenticate(request, username=username, password=password)

        if django_user is None:
            DetectorAnomalias.registrar_intento_fallido(
                username, ip_cliente, user_agent, 'Credenciales inválidas'
            )
            logger.warning(f"Intento fallido de login: {username} desde {ip_cliente}")
            return Response(
                {'error': 'Credenciales inválidas'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Obtener el perfil extendido Usuario
        try:
            usuario = django_user.perfil_autenticacion
        except Exception:
            return Response(
                {'error': 'Perfil de usuario no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )

        if not usuario.activo:
            AuditoriaManager.registrar_acceso_denegado(
                username, ip_cliente, 'Usuario inactivo', user_agent
            )
            return Response(
                {'error': 'Usuario inactivo'},
                status=status.HTTP_403_FORBIDDEN
            )

        with transaction.atomic():
            token_access = JWTManager.generar_token_access(usuario)
            token_refresh = JWTManager.generar_token_refresh(usuario)
            JWTManager.guardar_tokens(usuario, token_access, token_refresh)
            DetectorAnomalias.registrar_intento_exitoso(usuario, ip_cliente, user_agent)

        logger.info(f"Login exitoso: {username}")

        return Response(
            {
                'mensaje': 'Login exitoso',
                'access_token': token_access,
                'refresh_token': token_refresh,
                'tokens': {
                    'access': token_access,
                    'refresh': token_refresh,
                },
                'user': {
                    'id': str(usuario.id),
                    'username': usuario.username,
                    'email': usuario.email,
                    'rol': usuario.rol,
                    'empresa': usuario.empresa,
                }
            },
            status=status.HTTP_200_OK
        )
    
    except Exception as e:
        logger.error(f"Error en login: {str(e)}")
        return Response(
            {'error': 'Error en autenticación'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_usuario_actual(request):
    """Endpoint para obtener información del usuario autenticado"""
    try:
        usuario = request.user

        permisos = RolPermiso.objects.filter(rol=usuario.rol).select_related('permiso')
        permisos_list = [p.permiso.codigo for p in permisos]

        return Response(
            {
                'usuario': {
                    'id': str(usuario.id),
                    'username': usuario.username,
                    'email': usuario.email,
                    'first_name': usuario.first_name,
                    'last_name': usuario.last_name,
                    'empresa': usuario.empresa,
                    'rol': usuario.rol,
                    'activo': usuario.activo,
                    'bloqueado': usuario.bloqueado,
                },
                'permisos': permisos_list,
            },
            status=status.HTTP_200_OK
        )
    
    except Exception as e:
        logger.error(f"Error obteniendo usuario actual: {str(e)}")
        return Response(
            {'error': 'Error al obtener usuario'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def refresh_token(request):
    """Endpoint para refrescar el token de acceso"""
    try:
        token_refresh = request.data.get('refresh')
        
        if not token_refresh:
            return Response(
                {'error': 'refresh token es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payload = JWTManager.validar_token(token_refresh)
        if not payload:
            return Response(
                {'error': 'Token inválido o expirado'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        usuario = request.user
        token_access = JWTManager.generar_token_access(usuario)
        
        ip_cliente = obtener_ip_cliente(request)
        user_agent = obtener_user_agent(request)
        
        from .models import AuditoriaAcceso
        AuditoriaAcceso.objects.create(
            usuario=usuario,
            username=usuario.username,
            direccion_ip=ip_cliente,
            user_agent=user_agent,
            tipo_evento='token_refresh'
        )
        
        return Response(
            {
                'access': token_access,
            },
            status=status.HTTP_200_OK
        )
    
    except Exception as e:
        logger.error(f"Error refrescando token: {str(e)}")
        return Response(
            {'error': 'Error al refrescar token'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



@api_view(['POST', 'GET'])
@permission_classes([AllowAny])
def logout(request):
    """Endpoint para logout del usuario (maneja tanto JWT como Auth0)
    
    - Para usuarios con JWT: revoca el token
    - Para usuarios con Auth0: redirige a logout de Auth0
    - Limpia la sesión Django en ambos casos
    """
    try:
        usuario = request.user
        
        # Revocar tokens JWT si existen
        if usuario.is_authenticated:
            try:
                from .models import Token
                Token.objects.filter(usuario=usuario, activo=True).update(
                    activo=False,
                    fecha_revocacion=timezone.now(),
                    motivo_revocacion='Logout del usuario'
                )
            except Exception as e:
                logger.warning(f"Error revocando tokens: {str(e)}")
            
            # Eliminar social auth associations para forzar re-login
            try:
                usuario.social_user.all().delete()
            except Exception as e:
                logger.warning(f"Error eliminando social_user: {str(e)}")
        
        # Limpiar sesión Django completamente
        from django.contrib.auth import logout as django_logout
        django_logout(request)
        
        # Construir URL de logout de Auth0
        domain = settings.SOCIAL_AUTH_AUTH0_DOMAIN
        client_id = settings.SOCIAL_AUTH_AUTH0_KEY
        
        # Obtener la URL de retorno (puede ser pasada como parámetro o usar el host actual)
        # Agregar un parámetro 'just_logged_out=true' para que el frontend sepa que no debe restaurar sesión
        return_to = request.GET.get('return_to') or request.build_absolute_uri('/?just_logged_out=true')
        
        # Construir URL de logout de Auth0
        # Formato: https://YOUR_DOMAIN/v2/logout?client_id=YOUR_CLIENT_ID&returnTo=RETURN_URL
        # El parámetro 'federated' hace logout de todos los proveedores conectados
        auth0_logout_url = f"https://{domain}/v2/logout?client_id={client_id}&returnTo={return_to}"
        
        logger.info(f"Logout: {usuario.username if usuario.is_authenticated else 'anonymous'}")
        
        # Si es una petición AJAX/fetch, retornar JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return Response(
                {'mensaje': 'Logout exitoso', 'auth0_logout_url': auth0_logout_url},
                status=status.HTTP_200_OK
            )
        
        # Si es una petición normal, redirigir a Auth0 logout
        return redirect(auth0_logout_url)
        
    except Exception as e:
        logger.error(f"Error en logout: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Error en logout'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def historial_acceso(request):
    """Endpoint para obtener el historial de acceso del usuario"""
    try:
        usuario = request.user
        dias = int(request.query_params.get('dias', 7))
        
        historial = AuditoriaManager.obtener_historial_acceso(usuario, dias)
        
        datos_historial = [
            {
                'id': str(h.id),
                'tipo_evento': h.tipo_evento,
                'direccion_ip': h.direccion_ip,
                'fecha_evento': h.fecha_evento.isoformat(),
                'user_agent': h.user_agent,
            }
            for h in historial
        ]
        
        return Response(
            {
                'usuario': usuario.username,
                'historial': datos_historial,
                'total': len(datos_historial),
            },
            status=status.HTTP_200_OK
        )
    
    except Exception as e:
        logger.error(f"Error obteniendo historial: {str(e)}")
        return Response(
            {'error': 'Error al obtener historial'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Endpoint para verificar el estado del servicio"""
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        return Response(
            {
                'status': 'healthy',
                'service': 'auth_service',
                'timestamp': timezone.now().isoformat(),
            },
            status=status.HTTP_200_OK
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return Response(
            {'status': 'unhealthy'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ========== ASR LOG ENDPOINTS ==========

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@require_scope('read:integrity_logs')
def listar_rechazos_integridad(request):
    """
    ASR Integridad: Listar todos los rechazos por integridad.
    
    Parámetros query:
    - dias: Número de días atrás a consultar (default: 7)
    - empresa_id: Filtrar por empresa (admin solo)
    - endpoint: Filtrar por endpoint
    
    Solo admin puede ver rechazos de otras empresas.
    """
    try:
        from .models import RechazoIntegridad
        
        usuario = request.user
        dias = int(request.query_params.get('dias', 7))
        
        # Calcular fecha desde hace N días
        desde = timezone.now() - timezone.timedelta(days=dias)
        
        # Base query
        query = RechazoIntegridad.objects.filter(
            fecha_rechazo__gte=desde
        ).order_by('-fecha_rechazo')
        
        # Filtros opcionales
        endpoint = request.query_params.get('endpoint')
        if endpoint:
            query = query.filter(endpoint__icontains=endpoint)
        
        ip_cliente = request.query_params.get('direccion_ip')
        if ip_cliente:
            query = query.filter(direccion_ip=ip_cliente)
        
        # Paginación
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 50))
        
        total = query.count()
        start = (page - 1) * page_size
        end = start + page_size
        
        rechazos = query[start:end]
        
        datos = [
            {
                'id': str(r.id),
                'direccion_ip': r.direccion_ip,
                'endpoint': r.endpoint,
                'motivo_rechazo': r.motivo_rechazo,
                'fecha_rechazo': r.fecha_rechazo.isoformat(),
                'user_agent': r.user_agent,
            }
            for r in rechazos
        ]
        
        return Response(
            {
                'total': total,
                'page': page,
                'page_size': page_size,
                'rechazos': datos,
            },
            status=status.HTTP_200_OK
        )
    
    except Exception as e:
        logger.error(f"Error listando rechazos de integridad: {str(e)}")
        return Response(
            {'error': 'Error al listar rechazos'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_intentos_acceso_no_autorizado(request):
    """
    ASR Confidencialidad: Listar intentos de acceso no autorizado.
    
    Parámetros query:
    - dias: Número de días atrás a consultar (default: 7)
    - usuario_id: Filtrar por usuario
    - empresa_id: Filtrar por empresa solicitada
    
    Solo admin puede ver intentos de otras empresas.
    Los usuarios normales solo ven sus propios intentos.
    """
    try:
        usuario = request.user
        dias = int(request.query_params.get('dias', 7))
        
        # Calcular fecha desde hace N días
        desde = timezone.now() - timezone.timedelta(days=dias)
        
        # Base query
        query = IntentoAccesoNoAutorizado.objects.filter(
            fecha_intento__gte=desde
        ).order_by('-fecha_intento')
        
        # Si no es admin, solo ver sus propios intentos
        es_admin = getattr(usuario, 'auth0_rol', '') == 'admin'
        if not es_admin:
            query = query.filter(usuario=usuario)
        
        # Filtros opcionales
        usuario_id = request.query_params.get('usuario_id')
        if usuario_id and es_admin:
            query = query.filter(usuario_id=usuario_id)
        
        empresa_solicitada = request.query_params.get('empresa_solicitada_id')
        if empresa_solicitada:
            query = query.filter(empresa_solicitada_id=empresa_solicitada)
        
        # Paginación
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 50))
        
        total = query.count()
        start = (page - 1) * page_size
        end = start + page_size
        
        intentos = query[start:end]
        
        datos = [
            {
                'id': str(i.id),
                'usuario': i.usuario.usuario_django.email if i.usuario else 'unknown',
                'empresa_solicitada_id': i.empresa_solicitada_id,
                'empresa_autorizada_id': i.empresa_autorizada_id,
                'endpoint': i.endpoint,
                'direccion_ip': i.direccion_ip,
                'token_identifier': i.token_identifier,
                'fecha_intento': i.fecha_intento.isoformat(),
            }
            for i in intentos
        ]
        
        return Response(
            {
                'total': total,
                'page': page,
                'page_size': page_size,
                'intentos': datos,
            },
            status=status.HTTP_200_OK
        )
    
    except Exception as e:
        logger.error(f"Error listando intentos de acceso: {str(e)}")
        return Response(
            {'error': 'Error al listar intentos'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def estadisticas_asr(request):
    """
    Endpoint que retorna estadísticas consolidadas de ASR.
    
    - Rechazos de integridad por endpoint
    - Intentos de acceso no autorizado por empresa
    - Top IPs sospechosas
    """
    try:
        from .models import RechazoIntegridad
        from django.db.models import Count
        
        dias = int(request.query_params.get('dias', 30))
        desde = timezone.now() - timezone.timedelta(days=dias)
        
        # Rechazos por endpoint
        rechazos_por_endpoint = RechazoIntegridad.objects.filter(
            fecha_rechazo__gte=desde
        ).values('endpoint').annotate(count=Count('id')).order_by('-count')[:10]
        
        # Rechazos por IP
        rechazos_por_ip = RechazoIntegridad.objects.filter(
            fecha_rechazo__gte=desde
        ).values('direccion_ip').annotate(count=Count('id')).order_by('-count')[:10]
        
        # Motivos de rechazo más comunes
        motivos_comunes = RechazoIntegridad.objects.filter(
            fecha_rechazo__gte=desde
        ).values('motivo_rechazo').annotate(count=Count('id')).order_by('-count')[:5]
        
        # Intentos no autorizados por empresa
        intentos_por_empresa = IntentoAccesoNoAutorizado.objects.filter(
            fecha_intento__gte=desde
        ).values('empresa_solicitada_id').annotate(count=Count('id')).order_by('-count')[:10]
        
        return Response(
            {
                'periodo_dias': dias,
                'desde': desde.isoformat(),
                'hasta': timezone.now().isoformat(),
                'rechazos_por_endpoint': [
                    {'endpoint': r['endpoint'], 'count': r['count']}
                    for r in rechazos_por_endpoint
                ],
                'rechazos_por_ip': [
                    {'ip': r['direccion_ip'], 'count': r['count']}
                    for r in rechazos_por_ip
                ],
                'motivos_comunes': [
                    {'motivo': m['motivo_rechazo'], 'count': m['count']}
                    for m in motivos_comunes
                ],
                'intentos_por_empresa': [
                    {'empresa_id': i['empresa_solicitada_id'], 'count': i['count']}
                    for i in intentos_por_empresa
                ],
                'total_rechazos': RechazoIntegridad.objects.filter(
                    fecha_rechazo__gte=desde
                ).count(),
                'total_intentos_no_autorizados': IntentoAccesoNoAutorizado.objects.filter(
                    fecha_intento__gte=desde
                ).count(),
            },
            status=status.HTTP_200_OK
        )
    
    except Exception as e:
        logger.error(f"Error generando estadísticas ASR: {str(e)}")
        return Response(
            {'error': 'Error al generar estadísticas'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ======================== AUTH0 VIEWS ========================

from django.shortcuts import redirect
from django.http import HttpResponseRedirect
from urllib.parse import urlencode
from django.conf import settings

@api_view(['GET'])
@permission_classes([AllowAny])
def auth0_login(request):
    """Inicia el flujo de login con Auth0"""
    try:
        # Usar la URL de social_django para iniciar el flujo de Auth0
        # social_django proporciona: /complete/auth0/?code=...&state=...
        domain = settings.SOCIAL_AUTH_AUTH0_DOMAIN
        client_id = settings.SOCIAL_AUTH_AUTH0_KEY
        
        # Construir la URL de autorización de Auth0
        auth0_authorize_url = f"https://{domain}/authorize"
        
        # El callback debe apuntar a /complete/auth0/ (manejado por social_django)
        callback_url = request.build_absolute_uri('/complete/auth0/')
        
        params = {
            'client_id': client_id,
            'redirect_uri': callback_url,
            'response_type': 'code',
            'scope': 'openid profile email',
        }
        
        redirect_url = f"{auth0_authorize_url}?{urlencode(params)}"
        return redirect(redirect_url)
        
    except Exception as e:
        logger.error(f"Error en auth0_login: {str(e)}")
        return Response(
            {'error': 'Error al iniciar sesión con Auth0'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def auth0_callback_handler(request):
    """Callback handler para Auth0 que genera JWT en lugar de mantener sesión
    
    Este endpoint es llamado por social_django después de la autenticación.
    En lugar de mantener la sesión Django, generamos un JWT y redirigimos
    al frontend con el token.
    """
    try:
        user = request.user
        
        if not user.is_authenticated:
            return redirect('/login/auth0?error=auth_failed')
        
        # Generar JWT para este usuario
        from .utilities import JWTManager
        tokens = JWTManager.generar_tokens(user)
        
        # Limpiar sesión Django inmediatamente (NO mantener sesión)
        from django.contrib.auth import logout as django_logout
        django_logout(request)
        
        # Redirigir al frontend con el JWT en la URL
        # El frontend extraerá el token y lo guardará en localStorage
        access_token = tokens.get('access')
        return redirect(f'/?auth_token={access_token}')
        
    except Exception as e:
        logger.error(f"Error en auth0_callback_handler: {str(e)}", exc_info=True)
        return redirect('/?error=callback_failed')


@api_view(['GET'])
@permission_classes([AllowAny])
def auth0_me(request):
    """Retorna info del usuario autenticado vía Auth0 (usando sesión Django o JWT)
    
    Este endpoint:
    1. Primero intenta verificar JWT en Authorization header (para usuarios JWT)
    2. Si no hay JWT, verifica sesión Django (para usuarios Auth0)
    3. Si ninguno está presente, retorna 401
    """
    try:
        user = request.user
        
        # Obtener el token del header si existe
        auth_header = request.headers.get('Authorization', '')
        has_bearer_token = auth_header.startswith('Bearer ')
        
        # Si viene con Bearer token, requiere autenticación válida
        if has_bearer_token:
            if not user.is_authenticated:
                return Response(
                    {'error': 'Token inválido o expirado'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        else:
            # Si no hay Bearer token, verifica sesión Django
            # Para Auth0 users que vienen de la sesión de Django
            if not user.is_authenticated:
                return Response(
                    {'error': 'No autenticado. Requiere Bearer token o sesión válida'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        
        # Si llegamos aquí, el usuario está autenticado (vía JWT o sesión)
        # Obtener información del usuario
        response_data = {
            'id': str(user.id),
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
        }
        
        # Intentar obtener el perfil extendido Usuario
        try:
            usuario = user.perfil_autenticacion
            response_data.update({
                'empresa': usuario.empresa,
                'rol': usuario.rol,
                'activo': usuario.activo,
            })
        except Exception:
            response_data.update({
                'empresa': 'Unknown',
                'rol': 'usuario',
                'activo': True,
            })
        
        # Obtener rol de social_auth si existe (Auth0)
        try:
            social_user = user.social_user.get(provider='auth0')
            extra_data = social_user.extra_data
            response_data['rol'] = extra_data.get('https://finops-api/rol', response_data.get('rol', 'usuario'))
            response_data['empresa'] = extra_data.get('https://finops-api/empresa', response_data.get('empresa', 'Unknown'))
        except Exception:
            pass
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error en auth0_me: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Error al obtener información del usuario'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
