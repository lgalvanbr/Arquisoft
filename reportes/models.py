"""
Modelos para el servicio de reportes - FinOps
"""
from django.db import models
import uuid


class ConsumoNube(models.Model):
    """Modelo para registrar consumo de recursos en la nube"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa_id = models.UUIDField(db_index=True)
    proveedor_nube = models.CharField(max_length=20, choices=[('AWS', 'Amazon Web Services'), ('GCP', 'Google Cloud Platform')])
    cuenta_nube = models.CharField(max_length=255)
    proyecto = models.CharField(max_length=255, db_index=True)
    servicio = models.CharField(max_length=100, choices=[
        ('EC2', 'Elastic Compute Cloud'),
        ('RDS', 'Relational Database Service'),
        ('S3', 'Simple Storage Service'),
        ('Lambda', 'Lambda'),
        ('DynamoDB', 'DynamoDB'),
    ])
    region = models.CharField(max_length=100)
    etiquetas = models.JSONField(default=dict)
    costo_mensual = models.DecimalField(max_digits=15, decimal_places=4)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'consumo_nube'
        verbose_name = 'Consumo de Nube'
        verbose_name_plural = 'Consumos de Nube'
        indexes = [
            models.Index(fields=['empresa_id', 'fecha_registro']),
            models.Index(fields=['proveedor_nube', 'fecha_registro']),
        ]


class ReporteMensual(models.Model):
    """Modelo para reportes mensuales de costos"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa_id = models.UUIDField(db_index=True)
    ano = models.IntegerField()
    mes = models.IntegerField()
    costo_total = models.DecimalField(max_digits=15, decimal_places=4)
    costo_aws = models.DecimalField(max_digits=15, decimal_places=4, default=0)
    costo_gcp = models.DecimalField(max_digits=15, decimal_places=4, default=0)
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    ultima_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'reporte_mensual'
        verbose_name = 'Reporte Mensual'
        verbose_name_plural = 'Reportes Mensuales'


class ResumenPorProyecto(models.Model):
    """Resumen de costos por proyecto"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa_id = models.UUIDField(db_index=True)
    nombre_proyecto = models.CharField(max_length=255)
    costo_total = models.DecimalField(max_digits=15, decimal_places=4)
    numero_recursos = models.IntegerField(default=0)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'resumen_proyecto'


class AnálisisOptimización(models.Model):
    """Análisis de oportunidades de optimización"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa_id = models.UUIDField(db_index=True)
    tipo_recomendacion = models.CharField(max_length=100)
    descripcion = models.TextField()
    ahorro_potencial = models.DecimalField(max_digits=15, decimal_places=4)
    estado = models.CharField(max_length=20, default='pendiente')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'analisis_optimizacion'


class TendenciasAnomalias(models.Model):
    """Tendencias y anomalías detectadas"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa_id = models.UUIDField(db_index=True)
    tipo_anomalia = models.CharField(max_length=100)
    descripcion = models.TextField()
    severidad = models.CharField(max_length=20, choices=[('baja', 'Baja'), ('media', 'Media'), ('alta', 'Alta')])
    fecha_deteccion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'tendencias_anomalias'


class HistorialGeneracionReportes(models.Model):
    """Historial de generación de reportes"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa_id = models.UUIDField(db_index=True)
    tipo_reporte = models.CharField(max_length=100)
    estado = models.CharField(max_length=20, choices=[('procesando', 'Procesando'), ('completado', 'Completado'), ('error', 'Error')])
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    tiempo_ejecucion_ms = models.IntegerField(null=True, blank=True)
    
    class Meta:
        db_table = 'historial_generacion_reportes'
