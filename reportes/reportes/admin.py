"""
Configuración del admin de Django para el servicio de reportes
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    ConsumoNube, ReporteMensual, ResumenPorProyecto,
    AnálisisOptimización, TendenciasAnomalias, HistorialGeneracionReportes
)


@admin.register(ConsumoNube)
class ConsumoNubeAdmin(admin.ModelAdmin):
    list_display = ['empresa_id', 'proveedor_nube', 'servicio', 'costo_mensual', 'fecha_inicio']
    list_filter = ['proveedor_nube', 'servicio', 'region', 'fecha_inicio']
    search_fields = ['empresa_id', 'proyecto', 'servicio']
    readonly_fields = ['id', 'fecha_registro']
    date_hierarchy = 'fecha_inicio'


@admin.register(ReporteMensual)
class ReporteMensualAdmin(admin.ModelAdmin):
    list_display = ['empresa_id', 'año', 'mes', 'costo_total', 'numero_recursos', 'anomalias_detectadas']
    list_filter = ['año', 'mes', 'fecha_generacion']
    search_fields = ['empresa_id']
    readonly_fields = ['id', 'fecha_generacion']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('id', 'empresa_id', 'año', 'mes')
        }),
        ('Costos', {
            'fields': ('costo_total', 'costo_total_aws', 'costo_total_gcp', 'ahorro_potencial')
        }),
        ('Recursos', {
            'fields': ('numero_recursos', 'numero_proyectos', 'anomalias_detectadas')
        }),
        ('Detalles', {
            'fields': ('detalles_por_servicio', 'detalles_por_proyecto', 'detalles_por_region'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('fecha_generacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ResumenPorProyecto)
class ResumenPorProyectoAdmin(admin.ModelAdmin):
    list_display = ['proyecto', 'empresa_id', 'año', 'mes', 'costo_total', 'numero_recursos']
    list_filter = ['proyecto', 'año', 'mes']
    search_fields = ['proyecto', 'empresa_id']
    readonly_fields = ['id']


@admin.register(AnálisisOptimización)
class AnálisisOptimizaciónAdmin(admin.ModelAdmin):
    list_display = ['empresa_id', 'tipo_anomalia', 'nombre_recurso', 'estimado_ahorro_mensual', 'estado']
    list_filter = ['tipo_anomalia', 'estado', 'fecha_deteccion']
    search_fields = ['empresa_id', 'nombre_recurso', 'recurso_id']
    readonly_fields = ['id', 'fecha_deteccion']
    
    fieldsets = (
        ('Información del Recurso', {
            'fields': ('id', 'empresa_id', 'proveedor_nube', 'recurso_id', 'nombre_recurso', 'proyecto')
        }),
        ('Análisis', {
            'fields': ('tipo_anomalia', 'porcentaje_subutilizacion', 'estimado_ahorro_mensual')
        }),
        ('Recomendación', {
            'fields': ('recomendacion',)
        }),
        ('Estado', {
            'fields': ('estado', 'fecha_deteccion', 'fecha_resolucion')
        }),
    )


@admin.register(TendenciasAnomalias)
class TendenciasAnomalíasAdmin(admin.ModelAdmin):
    list_display = ['empresa_id', 'tipo_tendencia', 'nivel_severidad', 'impacto_economico', 'notificacion_enviada']
    list_filter = ['tipo_tendencia', 'nivel_severidad', 'notificacion_enviada', 'fecha_deteccion']
    search_fields = ['empresa_id', 'tipo_tendencia']
    readonly_fields = ['id', 'fecha_deteccion']
    date_hierarchy = 'fecha_deteccion'
    
    def get_severity_color(self, level):
        colors = {
            'bajo': 'green',
            'medio': 'orange',
            'alto': 'red',
            'crítico': 'darkred',
        }
        return colors.get(level, 'gray')


@admin.register(HistorialGeneracionReportes)
class HistorialGeneracionReportesAdmin(admin.ModelAdmin):
    list_display = ['empresa_id', 'tipo_reporte', 'tiempo_ejecucion_display', 'estado', 'fecha_inicio']
    list_filter = ['tipo_reporte', 'estado', 'ejecutado_background', 'fecha_inicio']
    search_fields = ['empresa_id', 'usuario_id']
    readonly_fields = ['id', 'fecha_inicio']
    date_hierarchy = 'fecha_inicio'
    
    def tiempo_ejecucion_display(self, obj):
        if obj.tiempo_ejecucion_ms < 100:
            color = 'green'
        elif obj.tiempo_ejecucion_ms < 2000:
            color = 'orange'
        else:
            color = 'red'
        
        texto = f"{obj.tiempo_ejecucion_ms}ms"
        return format_html(f'<span style="color: {color}; font-weight: bold;">{texto}</span>')
    tiempo_ejecucion_display.short_description = 'Tiempo de Ejecución'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
