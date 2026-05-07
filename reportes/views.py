"""
Views para el servicio de reportes - FinOps
"""
import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from autenticacion.models import AuditoriaAcceso

logger = logging.getLogger(__name__)


def _obtener_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


def _verificar_empresa(request, company_id_param):
    """
    Si el request incluye company_id, valida que coincida con la empresa del token autenticado.
    Detecta y registra en auditoría intentos de IDOR (acceso a datos de otra empresa).
    Retorna (True, None) si válido, (False, Response 403) si se detecta manipulación.
    """
    if company_id_param is None:
        return True, None

    empresa_token = str(request.user.empresa) if request.user.empresa else ''
    if company_id_param == empresa_token:
        return True, None

    ip = _obtener_ip(request)
    token_id = str(request.auth)[:20] if request.auth else 'N/A'

    try:
        AuditoriaAcceso.objects.create(
            usuario=request.user,
            username=request.user.username,
            direccion_ip=ip,
            tipo_evento='acceso_denegado',
            motivo_rechazo=(
                f'IDOR: acceso no autorizado a empresa {company_id_param} '
                f'con token de empresa {empresa_token}'
            ),
            detalles={
                'token_id': token_id,
                'company_id_solicitado': company_id_param,
                'empresa_token': empresa_token,
            }
        )
    except Exception as e:
        logger.error(f"Error registrando intento IDOR en auditoría: {e}")

    logger.warning(
        f"IDOR detectado: usuario={request.user.username} empresa_token={empresa_token} "
        f"company_id_solicitado={company_id_param} ip={ip} token_id={token_id}"
    )
    return False, Response(
        {'error': 'Acceso no autorizado: no puede acceder a datos de otra empresa'},
        status=status.HTTP_403_FORBIDDEN
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_reporte_mensual(request):
    """GET /api/reportes/mensual"""
    valido, error = _verificar_empresa(request, request.query_params.get('company_id'))
    if not valido:
        return error
    try:
        return Response({
            'mensaje': 'Reporte mensual',
            'status': 'success'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return Response({'error': 'Error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_reporte_proyecto(request):
    """GET /api/reportes/proyecto"""
    valido, error = _verificar_empresa(request, request.query_params.get('company_id'))
    if not valido:
        return error
    return Response({'mensaje': 'Reporte por proyecto'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_consumo_nube(request):
    """GET /api/reportes/consumo"""
    valido, error = _verificar_empresa(request, request.query_params.get('company_id'))
    if not valido:
        return error
    return Response({'mensaje': 'Consumo nube'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_gastos_por_servicio(request):
    """GET /api/reportes/gastos"""
    valido, error = _verificar_empresa(request, request.query_params.get('company_id'))
    if not valido:
        return error
    return Response({'mensaje': 'Gastos por servicio'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_analisis_optimizacion(request):
    """GET /api/reportes/analisis"""
    valido, error = _verificar_empresa(request, request.query_params.get('company_id'))
    if not valido:
        return error
    return Response({'mensaje': 'Análisis de optimización'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_tendencias(request):
    """GET /api/reportes/tendencias"""
    valido, error = _verificar_empresa(request, request.query_params.get('company_id'))
    if not valido:
        return error
    return Response({'mensaje': 'Tendencias y anomalías'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_historial_reportes(request):
    """GET /api/reportes/historial"""
    valido, error = _verificar_empresa(request, request.query_params.get('company_id'))
    if not valido:
        return error
    return Response({'mensaje': 'Historial de reportes'}, status=status.HTTP_200_OK)


@api_view(['GET'])
def health_check(request):
    """GET /api/health - Health check del servicio de reportes"""
    return Response({'status': 'healthy', 'service': 'reportes'}, status=status.HTTP_200_OK)

