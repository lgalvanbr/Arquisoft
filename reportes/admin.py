from django.contrib import admin
from .models import ConsumoNube, ReporteMensual, ResumenPorProyecto, AnálisisOptimización, TendenciasAnomalias, HistorialGeneracionReportes


@admin.register(ConsumoNube)
class ConsumoNubeAdmin(admin.ModelAdmin):
    list_display = ('empresa_id', 'proveedor_nube', 'servicio', 'costo_mensual', 'fecha_registro')
    list_filter = ('proveedor_nube', 'servicio', 'fecha_registro')
    search_fields = ('empresa_id', 'proyecto')


@admin.register(ReporteMensual)
class ReporteMensualAdmin(admin.ModelAdmin):
    list_display = ('empresa_id', 'ano', 'mes', 'costo_total', 'fecha_generacion')
    list_filter = ('ano', 'mes')
    search_fields = ('empresa_id',)


@admin.register(ResumenPorProyecto)
class ResumenPorProyectoAdmin(admin.ModelAdmin):
    list_display = ('empresa_id', 'nombre_proyecto', 'costo_total', 'numero_recursos')
    search_fields = ('empresa_id', 'nombre_proyecto')


@admin.register(AnálisisOptimización)
class AnálisisOptimizaciónAdmin(admin.ModelAdmin):
    list_display = ('empresa_id', 'tipo_recomendacion', 'ahorro_potencial', 'estado')
    list_filter = ('estado', 'tipo_recomendacion')


@admin.register(TendenciasAnomalias)
class TendenciasAnomaliasAdmin(admin.ModelAdmin):
    list_display = ('empresa_id', 'tipo_anomalia', 'severidad', 'fecha_deteccion')
    list_filter = ('severidad', 'tipo_anomalia')


@admin.register(HistorialGeneracionReportes)
class HistorialGeneracionReportesAdmin(admin.ModelAdmin):
    list_display = ('empresa_id', 'tipo_reporte', 'estado', 'tiempo_ejecucion_ms')
    list_filter = ('estado', 'tipo_reporte')
