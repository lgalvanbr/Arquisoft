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

from .models import Usuario, Permiso, RolPermiso
from .utilities import JWTManager, DetectorAnomalias, AuditoriaManager

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
        
        if Usuario.objects.filter(username=username).exists():
            return Response(
                {'error': 'El usuario ya existe'},
                status=status.HTTP_409_CONFLICT
            )
        
        if Usuario.objects.filter(email=email).exists():
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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """Endpoint para logout del usuario"""
    try:
        usuario = request.user
        
        from .models import Token
        Token.objects.filter(usuario=usuario, activo=True).update(
            activo=False,
            fecha_revocacion=timezone.now(),
            motivo_revocacion='Logout del usuario'
        )
        
        logger.info(f"Logout: {usuario.username}")
        
        return Response(
            {'mensaje': 'Logout exitoso'},
            status=status.HTTP_200_OK
        )
    
    except Exception as e:
        logger.error(f"Error en logout: {str(e)}")
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
