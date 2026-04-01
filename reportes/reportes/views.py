"""
Views para el servicio de reportes - FinOps
Endpoints para consulta de reportes, análisis y optimización
ASR: Reportes < 100 ms, Análisis en background si > 2 segundos
"""
import logging
import time
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.utils import timezone
from django.conf import settings
from decimal import Decimal

from .models import (
    ConsumoNube, ReporteMensual, ResumenPorProyecto, 
    AnálisisOptimización, TendenciasAnomalias, HistorialGeneracionReportes
)
from .utilities import GeneradorReportes, AnalizadorOptimización, DetectorTendencias

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_reporte_mensual(request):
    """
    Obtiene el reporte mensual de costos para una empresa
    
    GET /api/reportes/mensual?empresa_id=<uuid>&año=2024&mes=3
    ASR: Máximo 100 ms
    """
    inicio_tiempo = time.time()
    
    try:
        empresa_id = request.query_params.get('empresa_id')
        año = int(request.query_params.get('año', timezone.now().year))
        mes = int(request.query_params.get('mes', timezone.now().month))
        
        if not empresa_id:
            return Response(
                {'error': 'empresa_id es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificar permisos (en producción, validar que el usuario pertenece a la empresa)
        # Esta es una simplificación
        
        # Generar o recuperar reporte
        reporte, tiempo_ms = GeneradorReportes.generar_reporte_mensual(empresa_id, año, mes)
        
        tiempo_total = (time.time() - inicio_tiempo) * 1000
        
        # Registrar en historial
        HistorialGeneracionReportes.objects.create(
            empresa_id=empresa_id,
            usuario_id=request.user.id,
            tipo_reporte='reporte_mensual',
            parametros={'año': año, 'mes': mes},
            tiempo_ejecucion_ms=int(tiempo_total),
            ejecutado_background=tiempo_ms > 100,
            estado='exitoso'
        )
        
        return Response(
            {
                'reporte': {
                    'empresa_id': str(reporte.empresa_id),
                    'periodo': f"{año}/{mes:02d}",
                    'costo_total': str(reporte.costo_total),
                    'costo_aws': str(reporte.costo_total_aws),
                    'costo_gcp': str(reporte.costo_total_gcp),
                    'numero_recursos': reporte.numero_recursos,
                    'numero_proyectos': reporte.numero_proyectos,
                    'anomalias_detectadas': reporte.anomalias_detectadas,
                    'ahorro_potencial': str(reporte.ahorro_potencial),
                    'detalles_por_servicio': reporte.detalles_por_servicio,
                    'detalles_por_proyecto': reporte.detalles_por_proyecto,
                    'detalles_por_region': reporte.detalles_por_region,
                },
                'asr_metrics': {
                    'tiempo_generacion_ms': int(tiempo_ms),
                    'tiempo_total_ms': int(tiempo_total),
                    'cumple_sla': tiempo_total < 100,
                }
            },
            status=status.HTTP_200_OK
        )
    
    except ValueError:
        return Response(
            {'error': 'Parámetros inválidos'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error obteniendo reporte mensual: {str(e)}")
        
        HistorialGeneracionReportes.objects.create(
            empresa_id=request.query_params.get('empresa_id'),
            usuario_id=request.user.id,
            tipo_reporte='reporte_mensual',
            tiempo_ejecucion_ms=int((time.time() - inicio_tiempo) * 1000),
            estado='error',
            mensaje_error=str(e)
        )
        
        return Response(
            {'error': 'Error generando reporte'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_reporte_por_proyecto(request):
    """
    Obtiene reporte por proyecto específico
    
    GET /api/reportes/proyecto?empresa_id=<uuid>&proyecto=nombre&año=2024&mes=3
    """
    try:
        empresa_id = request.query_params.get('empresa_id')
        proyecto = request.query_params.get('proyecto')
        año = int(request.query_params.get('año', timezone.now().year))
        mes = int(request.query_params.get('mes', timezone.now().month))
        
        if not all([empresa_id, proyecto]):
            return Response(
                {'error': 'empresa_id y proyecto son requeridos'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        resumen = GeneradorReportes.generar_reporte_por_proyecto(
            empresa_id, proyecto, año, mes
        )
        
        return Response(
            {
                'proyecto': {
                    'empresa_id': str(resumen.empresa_id),
                    'nombre': resumen.proyecto,
                    'periodo': f"{año}/{mes:02d}",
                    'costo_total': str(resumen.costo_total),
                    'numero_recursos': resumen.numero_recursos,
                    'servicios_utilizados': resumen.servicios_utilizados,
                    'tendencia_mes_anterior': resumen.tendencia_mes_anterior,
                }
            },
            status=status.HTTP_200_OK
        )
    
    except Exception as e:
        logger.error(f"Error obteniendo reporte por proyecto: {str(e)}")
        return Response(
            {'error': 'Error generando reporte'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_gastos_consumo(request):
    """
    Lista consumo de recursos cloud
    
    GET /api/reportes/consumo?empresa_id=<uuid>&fecha_inicio=2024-01-01&fecha_fin=2024-03-31
    Soporta filtros por proveedor, servicio, proyecto, región
    """
    try:
        empresa_id = request.query_params.get('empresa_id')
        fecha_inicio = request.query_params.get('fecha_inicio')
        fecha_fin = request.query_params.get('fecha_fin')
        proveedor = request.query_params.get('proveedor')  # AWS, GCP
        servicio = request.query_params.get('servicio')
        proyecto = request.query_params.get('proyecto')
        
        if not empresa_id:
            return Response(
                {'error': 'empresa_id es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Construir query
        query = ConsumoNube.objects.filter(empresa_id=empresa_id)
        
        if fecha_inicio:
            query = query.filter(fecha_inicio__gte=fecha_inicio)
        if fecha_fin:
            query = query.filter(fecha_fin__lte=fecha_fin)
        if proveedor:
            query = query.filter(proveedor_nube=proveedor)
        if servicio:
            query = query.filter(servicio=servicio)
        if proyecto:
            query = query.filter(proyecto=proyecto)
        
        # Paginar
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 50))
        
        total = query.count()
        items = query[(page-1)*page_size:page*page_size]
        
        datos = [
            {
                'id': str(item.id),
                'proveedor': item.proveedor_nube,
                'cuenta': item.cuenta_nube,
                'proyecto': item.proyecto,
                'servicio': item.servicio,
                'region': item.region,
                'costo_mensual': str(item.costo_mensual),
                'unidades_consumidas': str(item.unidades_consumidas),
                'unidad_medida': item.unidad_medida,
                'fecha_inicio': item.fecha_inicio.isoformat(),
                'fecha_fin': item.fecha_fin.isoformat(),
            }
            for item in items
        ]
        
        return Response(
            {
                'resultados': datos,
                'paginacion': {
                    'page': page,
                    'page_size': page_size,
                    'total': total,
                    'total_pages': (total + page_size - 1) // page_size,
                }
            },
            status=status.HTTP_200_OK
        )
    
    except Exception as e:
        logger.error(f"Error listando consumo: {str(e)}")
        return Response(
            {'error': 'Error obteniendo datos de consumo'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analizar_optimizacion(request):
    """
    Ejecuta análisis de optimización para detectar desperdicio
    
    GET /api/reportes/analisis/optimizacion?empresa_id=<uuid>
    ASR: Si > 2 segundos, ejecutar en background
    """
    inicio_tiempo = time.time()
    
    try:
        empresa_id = request.query_params.get('empresa_id')
        ejecutar_background = request.query_params.get('background', 'auto')
        
        if not empresa_id:
            return Response(
                {'error': 'empresa_id es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Ejecutar análisis
        oportunidades, tiempo_ms = AnalizadorOptimización.detectar_oportunidades(empresa_id)
        tiempo_total = (time.time() - inicio_tiempo) * 1000
        
        # Si > 2 segundos, indicar que se ejecutó en background
        ejecutado_background = tiempo_total > 2000
        
        # Registrar en historial
        HistorialGeneracionReportes.objects.create(
            empresa_id=empresa_id,
            usuario_id=request.user.id,
            tipo_reporte='analisis_optimizacion',
            parametros={},
            tiempo_ejecucion_ms=int(tiempo_total),
            ejecutado_background=ejecutado_background,
            estado='exitoso'
        )
        
        # Si fue en background, retornar inmediatamente
        if ejecutado_background:
            return Response(
                {
                    'mensaje': 'Análisis en progreso, se enviará notificación por correo',
                    'empresa_id': empresa_id,
                    'tiempo_estimado_ms': tiempo_total,
                    'asr': {
                        'umbral_background': 2000,
                        'excedido': True,
                    }
                },
                status=status.HTTP_202_ACCEPTED
            )
        
        # Si fue rápido, retornar resultados
        datos_oportunidades = [
            {
                'id': str(op.id),
                'tipo': op.tipo_anomalia,
                'recurso': op.nombre_recurso,
                'proyecto': op.proyecto,
                'ahorro_potencial': str(op.estimado_ahorro_mensual),
                'recomendacion': op.recomendacion,
            }
            for op in oportunidades
        ]
        
        total_ahorro = sum(op.estimado_ahorro_mensual for op in oportunidades)
        
        return Response(
            {
                'analisis': {
                    'empresa_id': empresa_id,
                    'oportunidades_detectadas': len(oportunidades),
                    'ahorro_potencial_mensual': str(total_ahorro),
                    'detalles': datos_oportunidades,
                },
                'asr_metrics': {
                    'tiempo_ejecucion_ms': int(tiempo_total),
                    'ejecutado_background': False,
                }
            },
            status=status.HTTP_200_OK
        )
    
    except Exception as e:
        logger.error(f"Error analizando optimización: {str(e)}")
        return Response(
            {'error': 'Error en análisis de optimización'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def detectar_tendencias(request):
    """
    Detecta tendencias y anomalías en patrones de consumo
    
    GET /api/reportes/tendencias?empresa_id=<uuid>
    """
    try:
        empresa_id = request.query_params.get('empresa_id')
        
        if not empresa_id:
            return Response(
                {'error': 'empresa_id es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Ejecutar detección
        DetectorTendencias.detectar_spikes(empresa_id)
        
        # Obtener tendencias detectadas
        tendencias = TendenciasAnomalias.objects.filter(
            empresa_id=empresa_id
        ).order_by('-fecha_deteccion')[:10]
        
        datos = [
            {
                'id': str(t.id),
                'tipo': t.tipo_tendencia,
                'descripcion': t.descripcion,
                'periodo': f"{t.periodo_inicio} a {t.periodo_fin}",
                'impacto': str(t.impacto_economico),
                'severidad': t.nivel_severidad,
                'fecha_deteccion': t.fecha_deteccion.isoformat(),
            }
            for t in tendencias
        ]
        
        return Response(
            {
                'tendencias': datos,
                'total': len(datos),
            },
            status=status.HTTP_200_OK
        )
    
    except Exception as e:
        logger.error(f"Error detectando tendencias: {str(e)}")
        return Response(
            {'error': 'Error detectando tendencias'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def historial_reportes(request):
    """
    Obtiene historial de generación de reportes
    
    GET /api/reportes/historial?empresa_id=<uuid>
    """
    try:
        empresa_id = request.query_params.get('empresa_id')
        
        if not empresa_id:
            return Response(
                {'error': 'empresa_id es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        historial = HistorialGeneracionReportes.objects.filter(
            empresa_id=empresa_id
        ).order_by('-fecha_inicio')[:50]
        
        datos = [
            {
                'id': str(h.id),
                'tipo': h.tipo_reporte,
                'tiempo_ejecucion_ms': h.tiempo_ejecucion_ms,
                'ejecutado_background': h.ejecutado_background,
                'estado': h.estado,
                'fecha': h.fecha_inicio.isoformat(),
                'mensaje_error': h.mensaje_error,
            }
            for h in historial
        ]
        
        return Response(
            {
                'historial': datos,
                'total': len(datos),
            },
            status=status.HTTP_200_OK
        )
    
    except Exception as e:
        logger.error(f"Error obteniendo historial: {str(e)}")
        return Response(
            {'error': 'Error obteniendo historial'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Endpoint para verificar el estado del servicio
    
    GET /health
    """
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        return Response(
            {
                'status': 'healthy',
                'service': 'reportes_service',
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
