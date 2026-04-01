"""
Modelos para el servicio de reportes - FinOps
ASR: 
- Soportar 12,000 usuarios concurrentes con 95% disponibilidad
- Reportes mensuales en máximo 100 ms
- Análisis de más de 2 segundos ejecutarse en segundo plano
"""
from django.db import models
import uuid
from datetime import timedelta

# ======================== MODELOS DE CONSUMO DE NUBE ========================

class ConsumoNube(models.Model):
    """
    Modelo para registrar consumo de recursos en la nube
    Consolida datos de AWS y GCP
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa_id = models.UUIDField(db_index=True)  # ID de la empresa cliente
    proveedor_nube = models.CharField(
        max_length=20,
        choices=[
            ('AWS', 'Amazon Web Services'),
            ('GCP', 'Google Cloud Platform'),
        ]
    )
    cuenta_nube = models.CharField(max_length=255)  # Account ID de AWS o Project ID de GCP
    proyecto = models.CharField(max_length=255, db_index=True)  # Proyecto dentro de la cuenta
    servicio = models.CharField(
        max_length=100,
        choices=[
            ('EC2', 'Elastic Compute Cloud'),
            ('RDS', 'Relational Database Service'),
            ('S3', 'Simple Storage Service'),
            ('Lambda', 'Lambda'),
            ('DynamoDB', 'DynamoDB'),
            ('CloudFront', 'CloudFront'),
            ('ElastiCache', 'ElastiCache'),
            ('Compute_Engine', 'Compute Engine'),
            ('Cloud_Storage', 'Cloud Storage'),
            ('Cloud_SQL', 'Cloud SQL'),
            ('BigQuery', 'BigQuery'),
            ('Firestore', 'Firestore'),
            ('otros', 'Otros Servicios'),
        ]
    )
    region = models.CharField(max_length=100)
    etiquetas = models.JSONField(default=dict)  # Tags/Labels para categorización
    costo_mensual = models.DecimalField(max_digits=15, decimal_places=4)
    unidades_consumidas = models.DecimalField(max_digits=20, decimal_places=4)
    unidad_medida = models.CharField(max_length=50)  # GB, vCPU-hour, etc.
    fecha_inicio = models.DateField(db_index=True)
    fecha_fin = models.DateField(db_index=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'consumo_nube'
        verbose_name = 'Consumo Nube'
        verbose_name_plural = 'Consumo Nube'
        indexes = [
            models.Index(fields=['empresa_id', 'fecha_inicio']),
            models.Index(fields=['empresa_id', 'proyecto', 'fecha_inicio']),
            models.Index(fields=['proveedor_nube', 'servicio', 'fecha_inicio']),
            models.Index(fields=['costo_mensual']),  # Para identificar recursos costosos
        ]
        ordering = ['-fecha_inicio']
    
    def __str__(self):
        return f"{self.empresa_id} - {self.proveedor_nube} - {self.servicio} - {self.costo_mensual}"


class AnálisisOptimización(models.Model):
    """
    Modelo para almacenar análisis de recursos infrautilizados
    Identifica desperdicio económico
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa_id = models.UUIDField(db_index=True)
    proveedor_nube = models.CharField(max_length=20, choices=[('AWS', 'AWS'), ('GCP', 'GCP')])
    tipo_anomalia = models.CharField(
        max_length=100,
        choices=[
            ('instancia_inactiva', 'Instancia Inactiva'),
            ('recurso_sobredimensionado', 'Recurso Sobredimensionado'),
            ('datos_retenidos_sin_uso', 'Datos Retenidos sin Uso'),
            ('etiquetado_incompleto', 'Etiquetado Incompleto'),
            ('reserva_no_utilizada', 'Reserva No Utilizada'),
            ('patron_uso_anómalo', 'Patrón de Uso Anómalo'),
        ]
    )
    recurso_id = models.CharField(max_length=255)
    nombre_recurso = models.CharField(max_length=255)
    proyecto = models.CharField(max_length=255)
    estimado_ahorro_mensual = models.DecimalField(max_digits=15, decimal_places=2)
    porcentaje_subutilizacion = models.DecimalField(max_digits=5, decimal_places=2)
    recomendacion = models.TextField()
    estado = models.CharField(
        max_length=20,
        choices=[
            ('detectado', 'Detectado'),
            ('notificado', 'Notificado'),
            ('actuando', 'En Proceso'),
            ('resuelto', 'Resuelto'),
        ],
        default='detectado'
    )
    fecha_deteccion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'analisis_optimizacion'
        verbose_name = 'Análisis de Optimización'
        verbose_name_plural = 'Análisis de Optimización'
        indexes = [
            models.Index(fields=['empresa_id', 'fecha_deteccion']),
            models.Index(fields=['tipo_anomalia']),
            models.Index(fields=['estimado_ahorro_mensual']),
        ]
    
    def __str__(self):
        return f"{self.empresa_id} - {self.tipo_anomalia} - ${self.estimado_ahorro_mensual}"


class ReporteMensual(models.Model):
    """
    Modelo para almacenar reportes mensuales de gasto
    ASR: Generar en máximo 100 ms
    Pre-calculado para optimizar rendimiento
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa_id = models.UUIDField(db_index=True)
    año = models.IntegerField()
    mes = models.IntegerField()
    costo_total_aws = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    costo_total_gcp = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    costo_total = models.DecimalField(max_digits=15, decimal_places=2)
    numero_recursos = models.IntegerField()
    numero_proyectos = models.IntegerField()
    detalles_por_servicio = models.JSONField(default=dict)  # {servicio: {costo, unidades}}
    detalles_por_proyecto = models.JSONField(default=dict)  # {proyecto: costo}
    detalles_por_region = models.JSONField(default=dict)  # {region: costo}
    anomalias_detectadas = models.IntegerField(default=0)
    ahorro_potencial = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'reportes_mensuales'
        verbose_name = 'Reporte Mensual'
        verbose_name_plural = 'Reportes Mensuales'
        unique_together = ['empresa_id', 'año', 'mes']
        indexes = [
            models.Index(fields=['empresa_id', 'año', 'mes']),
            models.Index(fields=['costo_total']),
        ]
    
    def __str__(self):
        return f"{self.empresa_id} - {self.año}/{self.mes:02d} - ${self.costo_total}"


class ResumenPorProyecto(models.Model):
    """
    Modelo para almacenar resumen por proyecto
    Facilita análisis por área o proyecto
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa_id = models.UUIDField(db_index=True)
    proyecto = models.CharField(max_length=255, db_index=True)
    año = models.IntegerField()
    mes = models.IntegerField()
    costo_total = models.DecimalField(max_digits=15, decimal_places=2)
    numero_recursos = models.IntegerField()
    servicios_utilizados = models.JSONField(default=list)
    tendencia_mes_anterior = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  # % cambio
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'resumen_por_proyecto'
        verbose_name = 'Resumen por Proyecto'
        verbose_name_plural = 'Resumen por Proyecto'
        unique_together = ['empresa_id', 'proyecto', 'año', 'mes']
        indexes = [
            models.Index(fields=['empresa_id', 'proyecto', 'año']),
        ]
    
    def __str__(self):
        return f"{self.proyecto} - {self.año}/{self.mes:02d} - ${self.costo_total}"


class TendenciasAnomalias(models.Model):
    """
    Modelo para almacenar detección de patrones anómalos de uso
    Ejecutado en background si toma más de 2 segundos
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa_id = models.UUIDField(db_index=True)
    tipo_tendencia = models.CharField(
        max_length=100,
        choices=[
            ('spike_costo_repentino', 'Spike de Costo Repentino'),
            ('degradacion_sostenida', 'Degradación Sostenida'),
            ('anomalia_patron_uso', 'Anomalía en Patrón de Uso'),
            ('correlacion_cambios', 'Correlación de Cambios'),
        ]
    )
    descripcion = models.TextField()
    periodo_inicio = models.DateField()
    periodo_fin = models.DateField()
    impacto_economico = models.DecimalField(max_digits=15, decimal_places=2)
    nivel_severidad = models.CharField(
        max_length=20,
        choices=[
            ('bajo', 'Bajo'),
            ('medio', 'Medio'),
            ('alto', 'Alto'),
            ('crítico', 'Crítico'),
        ]
    )
    detalles = models.JSONField(default=dict)
    notificacion_enviada = models.BooleanField(default=False)
    fecha_notificacion = models.DateTimeField(null=True, blank=True)
    fecha_deteccion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tendencias_anomalias'
        verbose_name = 'Tendencia Anomalía'
        verbose_name_plural = 'Tendencias Anomalías'
        indexes = [
            models.Index(fields=['empresa_id', 'fecha_deteccion']),
            models.Index(fields=['nivel_severidad']),
            models.Index(fields=['notificacion_enviada']),
        ]
    
    def __str__(self):
        return f"{self.empresa_id} - {self.tipo_tendencia} - Severidad: {self.nivel_severidad}"


class HistorialGeneracionReportes(models.Model):
    """
    Modelo para auditoría de generación de reportes
    Monitorea ASR: reportes < 100 ms, análisis en background si > 2 segundos
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa_id = models.UUIDField(db_index=True)
    usuario_id = models.UUIDField(db_index=True)
    tipo_reporte = models.CharField(
        max_length=100,
        choices=[
            ('reporte_mensual', 'Reporte Mensual'),
            ('reporte_por_proyecto', 'Reporte por Proyecto'),
            ('analisis_optimizacion', 'Análisis de Optimización'),
            ('tendencias_anomalias', 'Tendencias y Anomalías'),
            ('comparativa_periodos', 'Comparativa de Períodos'),
        ]
    )
    parametros = models.JSONField(default=dict)
    tiempo_ejecucion_ms = models.IntegerField()  # Para monitorear ASR
    ejecutado_background = models.BooleanField(default=False)
    estado = models.CharField(
        max_length=20,
        choices=[
            ('exitoso', 'Exitoso'),
            ('en_proceso', 'En Proceso'),
            ('error', 'Error'),
        ]
    )
    mensaje_error = models.TextField(null=True, blank=True)
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    notificacion_enviada = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'historial_generacion_reportes'
        verbose_name = 'Historial Generación Reportes'
        verbose_name_plural = 'Historial Generación Reportes'
        indexes = [
            models.Index(fields=['empresa_id', 'fecha_inicio']),
            models.Index(fields=['usuario_id', 'fecha_inicio']),
            models.Index(fields=['tiempo_ejecucion_ms']),  # Para monitorear ASR
            models.Index(fields=['estado']),
        ]
    
    def __str__(self):
        return f"{self.empresa_id} - {self.tipo_reporte} - {self.tiempo_ejecucion_ms}ms"
