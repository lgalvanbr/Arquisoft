"""
URL configuration for reportes app.

Rutas de reportes y análisis de costos en la nube.
Implementación según laboratorio ISIS2503
"""
from django.urls import path
from . import views

urlpatterns = [
    # ======================== TEMPLATE VIEW ========================
    path('', views.reportes_view, name='reportes_page'),
    
    # ======================== ENDPOINTS DE REPORTES ========================
    # Reportes de Costos
    path('costos/empresa/<str:empresa_id>', views.listar_reportes_costos, name='listar_reportes_costos'),
    path('crear/<str:empresa_id>', views.crear_reporte_costos, name='crear_reporte_costos'),
    path('eliminar/<str:empresa_id>', views.eliminar_reporte, name='eliminar_reporte'),
    
    # Otros reportes
    path('proyecto', views.obtener_reporte_proyecto, name='obtener_reporte_proyecto'),
    path('consumo', views.obtener_consumo_nube, name='obtener_consumo_nube'),
    path('gastos', views.obtener_gastos_por_servicio, name='obtener_gastos_por_servicio'),
    path('analisis', views.obtener_analisis_optimizacion, name='obtener_analisis_optimizacion'),
    path('tendencias', views.obtener_tendencias, name='obtener_tendencias'),
    path('historial', views.obtener_historial_reportes, name='obtener_historial_reportes'),
    
    # ======================== HEALTH CHECK ========================
    path('health', views.health_check, name='health_check'),
    
    # Catch-all: DEBE ir al final para no capturar rutas específicas
    path('<str:empresa_id>', views.catch_all_reportes, name='catch_all_reportes'),
]
