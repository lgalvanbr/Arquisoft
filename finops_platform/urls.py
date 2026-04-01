"""
finops_platform URL Configuration

Main URL router for autenticacion and reportes apps
"""
from django.contrib import admin
from django.urls import path
from autenticacion import views as auth_views
from reportes import views as report_views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # ======================== ENDPOINTS DE AUTENTICACIÓN ========================
    path('api/auth/register', auth_views.register, name='register'),
    path('api/auth/login', auth_views.login, name='login'),
    path('api/auth/me', auth_views.obtener_usuario_actual, name='obtener_usuario_actual'),
    path('api/auth/refresh', auth_views.refresh_token, name='refresh_token'),
    path('api/auth/logout', auth_views.logout, name='logout'),
    
    # ======================== ENDPOINTS DE AUDITORÍA ========================
    path('api/auth/audit/historial', auth_views.historial_acceso, name='historial_acceso'),
    
    # ======================== ENDPOINTS DE REPORTES ========================
    path('api/reportes/mensual', report_views.obtener_reporte_mensual, name='obtener_reporte_mensual'),
    path('api/reportes/proyecto', report_views.obtener_reporte_proyecto, name='obtener_reporte_proyecto'),
    path('api/reportes/consumo', report_views.obtener_consumo_nube, name='obtener_consumo_nube'),
    path('api/reportes/gastos', report_views.obtener_gastos_por_servicio, name='obtener_gastos_por_servicio'),
    path('api/reportes/analisis', report_views.obtener_analisis_optimizacion, name='obtener_analisis_optimizacion'),
    path('api/reportes/tendencias', report_views.obtener_tendencias, name='obtener_tendencias'),
    path('api/reportes/historial', report_views.obtener_historial_reportes, name='obtener_historial_reportes'),
    
    # ======================== HEALTH CHECK ========================
    path('api/health', auth_views.health_check, name='health_check'),
    path('api/health', report_views.health_check, name='health_check'),
]
