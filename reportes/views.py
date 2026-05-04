"""
Views para el servicio de reportes - FinOps
ASR Integridad: Validación de schemas
ASR Confidencialidad: Control de acceso por empresa
"""
import logging
import json
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
# from jsonschema import ValidationError  # TODO: Install jsonschema from requirements

from .validators import PayloadValidator
from .permissions import validar_acceso_empresa

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@validar_acceso_empresa
def crear_reporte_costos(request, empresa_id):
    """
    POST /api/reportes/costos/empresa/{empresa_id}
    
    Crea un reporte de costos para una empresa.
    
    Body:
    {
        "mes": 1-12,
        "ano": 2020-2099,
        "incluir_detalle": bool (opcional),
        "filtros": { "proveedor": "AWS|GCP", "proyecto": "nombre" } (opcional)
    }
    
    ASR Integridad:
    - Valida schema del payload
    - Rechaza si está adulterado (400)
    
    ASR Confidencialidad:
    - Solo acceso a empresa propia (403 si intenta acceder a otra)
    """
    try:
        # Obtener payload (ya validado por middleware)
        payload = getattr(request, 'payload', {})
        
        if not payload:
            return Response(
                {'error': 'Payload vacío o inválido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar schema
        try:
            PayloadValidator.validar_reporte_costos(payload)
        except ValidationError as e:
            logger.warning(
                f"[ASR INTEGRIDAD] Schema inválido en /api/reportes/costos | "
                f"Empresa: {empresa_id} | Error: {str(e)}"
            )
            return Response(
                {'error': f'Schema inválido: {e.message}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Si llegó aquí: payload válido, empresa autorizada
        usuario = request.user
        mes = payload.get('mes')
        ano = payload.get('ano')
        
        # Simular generación de reporte
        reporte = {
            'id': f"rpt_{empresa_id}_{ano}_{mes:02d}",
            'empresa_id': empresa_id,
            'mes': mes,
            'ano': ano,
            'usuario': usuario.usuario_django.email,
            'costo_total': 1250.50,  # Simulado
            'fecha_generacion': timezone.now().isoformat(),
            'status': 'generado',
        }
        
        logger.info(
            f"Reporte de costos generado | "
            f"Empresa: {empresa_id} | "
            f"Usuario: {usuario.usuario_django.email} | "
            f"Período: {mes}/{ano}"
        )
        
        return Response(
            {
                'mensaje': 'Reporte generado exitosamente',
                'reporte': reporte,
            },
            status=status.HTTP_201_CREATED
        )
    
    except Exception as e:
        logger.error(f"Error generando reporte de costos: {str(e)}")
        return Response(
            {'error': 'Error al generar reporte'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@validar_acceso_empresa
def obtener_reporte_costos(request, empresa_id):
    """
    GET /api/reportes/costos/empresa/{empresa_id}?mes=1&ano=2024
    
    Obtiene reporte de costos de una empresa.
    
    ASR Confidencialidad:
    - Solo acceso a empresa propia (403 si intenta acceder a otra)
    """
    try:
        usuario = request.user
        mes = request.query_params.get('mes')
        ano = request.query_params.get('ano')
        
        if not mes or not ano:
            return Response(
                {'error': 'Parámetros mes y ano requeridos'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Simular obtención de datos
        reporte = {
            'id': f"rpt_{empresa_id}_{ano}_{int(mes):02d}",
            'empresa_id': empresa_id,
            'mes': int(mes),
            'ano': int(ano),
            'costo_total': 1250.50,
            'costo_compute': 750.00,
            'costo_storage': 350.00,
            'costo_networking': 150.50,
            'fecha_generacion': timezone.now().isoformat(),
        }
        
        logger.info(
            f"Reporte consultado | "
            f"Empresa: {empresa_id} | "
            f"Usuario: {usuario.usuario_django.email}"
        )
        
        return Response(
            {
                'reporte': reporte,
            },
            status=status.HTTP_200_OK
        )
    
    except Exception as e:
        logger.error(f"Error obteniendo reporte de costos: {str(e)}")
        return Response(
            {'error': 'Error al obtener reporte'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@validar_acceso_empresa
def listar_reportes_empresa(request, empresa_id):
    """
    GET /api/reportes/empresa/{empresa_id}?limite=10&offset=0
    
    Lista todos los reportes de una empresa.
    
    ASR Confidencialidad:
    - Solo acceso a empresa propia (403 si intenta acceder a otra)
    """
    try:
        usuario = request.user
        limite = int(request.query_params.get('limite', 10))
        offset = int(request.query_params.get('offset', 0))
        
        # Simular obtención de lista
        reportes = [
            {
                'id': f"rpt_{empresa_id}_2024_{i:02d}",
                'empresa_id': empresa_id,
                'mes': i,
                'ano': 2024,
                'costo_total': 1200 + (i * 50),
                'fecha_generacion': timezone.now().isoformat(),
            }
            for i in range(1, 4)
        ]
        
        logger.info(
            f"Reportes listados | "
            f"Empresa: {empresa_id} | "
            f"Usuario: {usuario.usuario_django.email} | "
            f"Total: {len(reportes)}"
        )
        
        return Response(
            {
                'empresa_id': empresa_id,
                'total': len(reportes),
                'limite': limite,
                'offset': offset,
                'reportes': reportes[offset:offset+limite],
            },
            status=status.HTTP_200_OK
        )
    
    except Exception as e:
        logger.error(f"Error listando reportes: {str(e)}")
        return Response(
            {'error': 'Error al listar reportes'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_reporte_proyecto(request):
    """GET /api/reportes/proyecto"""
    return Response({'mensaje': 'Reporte por proyecto'}, status=status.HTTP_200_OK)


@api_view(['GET'])
def obtener_consumo_nube(request):
    """GET /api/reportes/consumo"""
    return Response({'mensaje': 'Consumo nube'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_gastos_por_servicio(request):
    """GET /api/reportes/gastos"""
    return Response({'mensaje': 'Gastos por servicio'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_analisis_optimizacion(request):
    """GET /api/reportes/analisis"""
    return Response({'mensaje': 'Análisis de optimización'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_tendencias(request):
    """GET /api/reportes/tendencias"""
    return Response({'mensaje': 'Tendencias y anomalías'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_historial_reportes(request):
    """GET /api/reportes/historial"""
    return Response({'mensaje': 'Historial de reportes'}, status=status.HTTP_200_OK)


@api_view(['GET'])
def health_check(request):
    """GET /api/health - Health check del servicio de reportes"""
    return Response({'status': 'healthy', 'service': 'reportes'}, status=status.HTTP_200_OK)
