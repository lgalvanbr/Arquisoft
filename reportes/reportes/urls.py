"""reportes URL Configuration - FinOps Service

Rutas de la API de Reportes y Análisis de FinOps
"""
from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # ======================== ENDPOINTS DE REPORTES ========================
    # Reportes mensuales (< 100 ms)
    path('api/reportes/mensual', views.obtener_reporte_mensual, name='obtener_reporte_mensual'),
    path('api/reportes/proyecto', views.obtener_reporte_por_proyecto, name='obtener_reporte_por_proyecto'),
    
    # Listado de consumo con filtros
    path('api/reportes/consumo', views.listar_gastos_consumo, name='listar_gastos_consumo'),
    path('api/reportes/gastos', views.listar_gastos_consumo, name='listar_gastos'),  # Alias
    
    # ======================== ENDPOINTS DE ANÁLISIS Y OPTIMIZACIÓN ========================
    # Análisis en background si > 2 segundos
    path('api/reportes/analisis/optimizacion', views.analizar_optimizacion, name='analizar_optimizacion'),
    
    # Tendencias y anomalías
    path('api/reportes/tendencias', views.detectar_tendencias, name='detectar_tendencias'),
    
    # ======================== ENDPOINTS DE AUDITORÍA ========================
    path('api/reportes/historial', views.historial_reportes, name='historial_reportes'),
    
    # ======================== HEALTH CHECK ========================
    path('api/health', views.health_check, name='health_check'),
]
