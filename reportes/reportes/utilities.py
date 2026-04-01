"""
Utilidades para el servicio de reportes - FinOps
Incluye generación de reportes, análisis de optimización y detección de anomalías
ASR: Reportes < 100 ms, Análisis en background si > 2 segundos
"""
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from django.utils import timezone
from django.conf import settings
from django.db.models import Sum, Count, Avg, Q
from .models import ConsumoNube, ReporteMensual, ResumenPorProyecto, TendenciasAnomalias, AnálisisOptimización

logger = logging.getLogger(__name__)


class GeneradorReportes:
    """
    Generador de reportes con optimización para ASR
    Reportes mensuales deben generarse en < 100 ms
    """
    
    @staticmethod
    def generar_reporte_mensual(empresa_id, año, mes):
        """
        Genera reporte mensual pre-calculado
        ASR: Máximo 100 ms
        """
        inicio_tiempo = timezone.now()
        
        try:
            # Obtener consumo del mes
            consumos = ConsumoNube.objects.filter(
                empresa_id=empresa_id,
                fecha_inicio__year=año,
                fecha_inicio__month=mes
            )
            
            # Calcular totales
            total_aws = consumos.filter(proveedor_nube='AWS').aggregate(
                total=Sum('costo_mensual')
            )['total'] or Decimal('0.00')
            
            total_gcp = consumos.filter(proveedor_nube='GCP').aggregate(
                total=Sum('costo_mensual')
            )['total'] or Decimal('0.00')
            
            total = total_aws + total_gcp
            
            # Detalles por servicio
            detalles_servicio = {}
            for servicio in consumos.values('servicio').distinct():
                costo = consumos.filter(
                    servicio=servicio['servicio']
                ).aggregate(total=Sum('costo_mensual'))['total'] or Decimal('0.00')
                detalles_servicio[servicio['servicio']] = str(costo)
            
            # Detalles por proyecto
            detalles_proyecto = {}
            for proyecto in consumos.values('proyecto').distinct():
                costo = consumos.filter(
                    proyecto=proyecto['proyecto']
                ).aggregate(total=Sum('costo_mensual'))['total'] or Decimal('0.00')
                detalles_proyecto[proyecto['proyecto']] = str(costo)
            
            # Detalles por región
            detalles_region = {}
            for region in consumos.values('region').distinct():
                costo = consumos.filter(
                    region=region['region']
                ).aggregate(total=Sum('costo_mensual'))['total'] or Decimal('0.00')
                detalles_region[region['region']] = str(costo)
            
            # Calcular anomalías y ahorro potencial
            anomalias = AnálisisOptimización.objects.filter(
                empresa_id=empresa_id,
                fecha_deteccion__year=año,
                fecha_deteccion__month=mes
            ).count()
            
            ahorro_potencial = AnálisisOptimización.objects.filter(
                empresa_id=empresa_id,
                fecha_deteccion__year=año,
                fecha_deteccion__month=mes
            ).aggregate(total=Sum('estimado_ahorro_mensual'))['total'] or Decimal('0.00')
            
            # Crear o actualizar reporte
            reporte, created = ReporteMensual.objects.update_or_create(
                empresa_id=empresa_id,
                año=año,
                mes=mes,
                defaults={
                    'costo_total_aws': total_aws,
                    'costo_total_gcp': total_gcp,
                    'costo_total': total,
                    'numero_recursos': consumos.count(),
                    'numero_proyectos': len(detalles_proyecto),
                    'detalles_por_servicio': detalles_servicio,
                    'detalles_por_proyecto': detalles_proyecto,
                    'detalles_por_region': detalles_region,
                    'anomalias_detectadas': anomalias,
                    'ahorro_potencial': ahorro_potencial,
                }
            )
            
            tiempo_ejecucion = (timezone.now() - inicio_tiempo).total_seconds() * 1000
            
            logger.info(
                f"Reporte generado para empresa {empresa_id} ({año}/{mes:02d}): "
                f"${total} en {tiempo_ejecucion:.2f}ms"
            )
            
            return reporte, tiempo_ejecucion
        
        except Exception as e:
            logger.error(f"Error generando reporte mensual: {str(e)}")
            raise
    
    @staticmethod
    def generar_reporte_por_proyecto(empresa_id, proyecto, año, mes):
        """
        Genera reporte resumido por proyecto
        """
        try:
            consumos = ConsumoNube.objects.filter(
                empresa_id=empresa_id,
                proyecto=proyecto,
                fecha_inicio__year=año,
                fecha_inicio__month=mes
            )
            
            costo_total = consumos.aggregate(total=Sum('costo_mensual'))['total'] or Decimal('0.00')
            
            servicios = list(consumos.values_list('servicio', flat=True).distinct())
            
            # Calcular tendencia vs mes anterior
            fecha_mes_anterior = datetime(año, mes, 1) - timedelta(days=1)
            consumos_mes_anterior = ConsumoNube.objects.filter(
                empresa_id=empresa_id,
                proyecto=proyecto,
                fecha_inicio__year=fecha_mes_anterior.year,
                fecha_inicio__month=fecha_mes_anterior.month
            )
            
            costo_mes_anterior = consumos_mes_anterior.aggregate(
                total=Sum('costo_mensual')
            )['total'] or Decimal('0.00')
            
            tendencia = None
            if costo_mes_anterior > 0:
                tendencia = float(((costo_total - costo_mes_anterior) / costo_mes_anterior) * 100)
            
            resumen, _ = ResumenPorProyecto.objects.update_or_create(
                empresa_id=empresa_id,
                proyecto=proyecto,
                año=año,
                mes=mes,
                defaults={
                    'costo_total': costo_total,
                    'numero_recursos': consumos.count(),
                    'servicios_utilizados': servicios,
                    'tendencia_mes_anterior': tendencia,
                }
            )
            
            return resumen
        
        except Exception as e:
            logger.error(f"Error generando reporte por proyecto: {str(e)}")
            raise


class AnalizadorOptimización:
    """
    Analizador de oportunidades de optimización
    Detecta infrautilización, recursos sobredimensionados, etc.
    """
    
    @staticmethod
    def detectar_oportunidades(empresa_id):
        """
        Detecta oportunidades de optimización
        Ejecutado en background si toma > 2 segundos
        """
        inicio_tiempo = timezone.now()
        oportunidades = []
        
        try:
            # 1. Detectar instancias inactivas (0 costo en últimos 30 días)
            oportunidades.extend(
                AnalizadorOptimización._detectar_instancias_inactivas(empresa_id)
            )
            
            # 2. Detectar recursos sobredimensionados
            oportunidades.extend(
                AnalizadorOptimización._detectar_sobredimensionamiento(empresa_id)
            )
            
            # 3. Detectar datos retenidos sin uso
            oportunidades.extend(
                AnalizadorOptimización._detectar_datos_sin_uso(empresa_id)
            )
            
            # 4. Detectar etiquetado incompleto
            oportunidades.extend(
                AnalizadorOptimización._detectar_etiquetado_incompleto(empresa_id)
            )
            
            tiempo_ejecucion = (timezone.now() - inicio_tiempo).total_seconds() * 1000
            
            logger.info(
                f"Análisis de optimización completado para {empresa_id}: "
                f"{len(oportunidades)} oportunidades detectadas en {tiempo_ejecucion:.2f}ms"
            )
            
            return oportunidades, tiempo_ejecucion
        
        except Exception as e:
            logger.error(f"Error analizando optimización: {str(e)}")
            raise
    
    @staticmethod
    def _detectar_instancias_inactivas(empresa_id):
        """Detecta instancias sin uso"""
        oportunidades = []
        
        # Buscar recursos sin consumo en últimos 30 días
        fecha_limite = timezone.now() - timedelta(days=30)
        
        consumos_inactivos = ConsumoNube.objects.filter(
            empresa_id=empresa_id,
            unidades_consumidas=Decimal('0'),
            fecha_inicio__gte=fecha_limite
        )
        
        for consumo in consumos_inactivos:
            op, _ = AnálisisOptimización.objects.get_or_create(
                empresa_id=empresa_id,
                recurso_id=consumo.cuenta_nube,
                tipo_anomalia='instancia_inactiva',
                defaults={
                    'proveedor_nube': consumo.proveedor_nube,
                    'nombre_recurso': consumo.servicio,
                    'proyecto': consumo.proyecto,
                    'estimado_ahorro_mensual': consumo.costo_mensual,
                    'porcentaje_subutilizacion': Decimal('100'),
                    'recomendacion': 'Terminar instancia inactiva para ahorrar costos'
                }
            )
            oportunidades.append(op)
        
        return oportunidades
    
    @staticmethod
    def _detectar_sobredimensionamiento(empresa_id):
        """Detecta recursos sobredimensionados"""
        # Implementar lógica de detección de sobredimensionamiento
        return []
    
    @staticmethod
    def _detectar_datos_sin_uso(empresa_id):
        """Detecta almacenamiento retenido sin uso"""
        # Implementar lógica de detección de datos sin uso
        return []
    
    @staticmethod
    def _detectar_etiquetado_incompleto(empresa_id):
        """Detecta recursos sin etiquetado adecuado"""
        oportunidades = []
        
        # Buscar recursos sin etiquetas
        consumos_sin_etiquetas = ConsumoNube.objects.filter(
            empresa_id=empresa_id,
            etiquetas__isnull=True
        )
        
        for consumo in consumos_sin_etiquetas:
            oportunidades.append({
                'empresa_id': empresa_id,
                'tipo_anomalia': 'etiquetado_incompleto',
                'nombre_recurso': consumo.servicio,
                'recomendacion': 'Agregar etiquetas para mejor gobernanza y seguimiento de costos'
            })
        
        return oportunidades


class DetectorTendencias:
    """
    Detector de tendencias y anomalías en patrones de consumo
    """
    
    @staticmethod
    def detectar_spikes(empresa_id):
        """
        Detecta incrementos repentinos en costos
        """
        try:
            # Obtener últimos 2 meses
            hoy = timezone.now()
            mes_actual = ConsumoNube.objects.filter(
                empresa_id=empresa_id,
                fecha_inicio__year=hoy.year,
                fecha_inicio__month=hoy.month
            ).aggregate(total=Sum('costo_mensual'))['total'] or Decimal('0.00')
            
            mes_anterior = hoy - timedelta(days=30)
            consumo_mes_anterior = ConsumoNube.objects.filter(
                empresa_id=empresa_id,
                fecha_inicio__year=mes_anterior.year,
                fecha_inicio__month=mes_anterior.month
            ).aggregate(total=Sum('costo_mensual'))['total'] or Decimal('0.00')
            
            # Calcular porcentaje de cambio
            if mes_anterior > 0:
                cambio_porcentaje = ((mes_actual - consumo_mes_anterior) / consumo_mes_anterior) * 100
                
                # Si cambio > 20%, registrar como anomalía
                if abs(cambio_porcentaje) > 20:
                    nivel_severidad = 'alto' if cambio_porcentaje > 50 else 'medio'
                    
                    TendenciasAnomalias.objects.create(
                        empresa_id=empresa_id,
                        tipo_tendencia='spike_costo_repentino',
                        descripcion=f"Incremento de {cambio_porcentaje:.2f}% en costos cloud",
                        periodo_inicio=mes_anterior.date(),
                        periodo_fin=hoy.date(),
                        impacto_economico=abs(mes_actual - consumo_mes_anterior),
                        nivel_severidad=nivel_severidad,
                        detalles={'cambio_porcentaje': float(cambio_porcentaje)}
                    )
            
            return True
        
        except Exception as e:
            logger.error(f"Error detectando tendencias: {str(e)}")
            return False
