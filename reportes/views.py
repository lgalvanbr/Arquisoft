"""
Views para el servicio de reportes - FinOps
"""
import logging
from django.utils import timezone
from django.db import connection
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_reporte_mensual(request):
    """GET /api/reportes/mensual"""
    try:
        return Response({
            'mensaje': 'Reporte mensual',
            'status': 'success'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return Response({'error': 'Error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
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
@permission_classes([AllowAny])
def health_check(request):
    """GET /api/reportes/health — Kong usa este endpoint para decidir si la instancia está sana"""
    try:
        # Verifica conectividad real con la BD — si falla, Kong retira esta instancia
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return Response({
            'status': 'healthy',
            'service': 'reportes',
            'timestamp': timezone.now().isoformat(),
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        # 503 es la señal correcta para Kong — no 500
        return Response({
            'status': 'unhealthy',
            'service': 'reportes',
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)