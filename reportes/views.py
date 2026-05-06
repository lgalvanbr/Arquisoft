"""
Views para el servicio de reportes - FinOps
ASR Integridad: Validación de integridad de payloads
ASR Confidencialidad: Control de acceso por empresa
ASR Disponibilidad: Detección de SQL Injection en reportes de costos
"""
import logging
import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from .validators import validate_report_request
from .permissions import check_company_access, require_authentication
from autenticacion.auth0backend import getRole


logger = logging.getLogger(__name__)


def _get_user_company(request):
    """Obtiene la empresa del usuario, primero de Usuario.empresa, luego de AsociacionUsuarioEmpresa."""
    from autenticacion.models import Usuario as UsuarioModel
    try:
        local_usuario = UsuarioModel.objects.filter(usuario_django=request.user).first()
        if local_usuario and local_usuario.empresa:
            return str(local_usuario.empresa.id)
    except:
        pass
    
    try:
        from empresa.models import AsociacionUsuarioEmpresa
        asociacion = AsociacionUsuarioEmpresa.objects.filter(
            usuario=request.user, activo=True
        ).select_related('empresa').first()
        if asociacion:
            return asociacion.empresa.id
    except:
        pass
    
    return None


def _check_role(request, empresa_id=None):
    """
    Verificacion de rol inline para endpoints de reportes.
    
    Admin: acceso a cualquier empresa
    Manager: solo su propia empresa (verificada en DB)
    
    Returns (error_response, user_company) o (None, user_company)
    """
    role = getRole(request)
    allowed_roles = ["Admin", "Manager"]
    
    print("=== _check_role: role:", role)
    print("=== _check_role: allowed_roles:", allowed_roles)
    print("=== _check_role: empresa_id:", empresa_id)
    
    if role not in allowed_roles:
        return JsonResponse({
            'error': 'Acceso Denegado',
            'detail': 'No tienes acceso a esta zona'
        }, status=403), None
    
    if role == "Admin":
        print("=== _check_role: Admin - acceso permitido a cualquier empresa ===")
        return None, "any"
    
    # Manager: verificar que empresa_id coincida con su empresa en DB
    user_company = _get_user_company(request)
    
    print("=== _check_role: Manager - user_company:", user_company)
    
    if not user_company:
        return JsonResponse({
            'error': 'Acceso Denegado',
            'detail': 'No se encontro informacion de empresa para este usuario'
        }, status=403), None
    
    if empresa_id and str(user_company).upper() != str(empresa_id).upper():
        from .permissions import _log_unauthorized_access
        _log_unauthorized_access(request, empresa_id, user_company)
        return JsonResponse({
            'error': 'Acceso Denegado',
            'detail': 'No tienes permiso para acceder a esta empresa'
        }, status=403), None
    
    print("=== _check_role: Manager - acceso permitido a su empresa ===")
    return None, user_company


# ==================== REPORTES DE COSTOS ====================

@require_http_methods(["GET"])
@require_authentication
@check_company_access
@validate_report_request
def listar_reportes_costos(request, empresa_id):
    """
    GET /api/reportes/costos/empresa/{empresa_id}
    
    Obtiene reportes de costos existentes para una empresa.
    
    ASR Disponibilidad: Valida empresa_id contra SQL Injection
    ASR Confidencialidad:
    - Solo acceso a empresa propia
    - Si intenta acceder a empresa diferente: 403 Forbidden + log
    - Log incluye: fecha, IP origen, usuario, token ID
    """
    try:
        role = getRole(request)
        allowed_roles = ["Admin", "Manager"]
        
        if role not in allowed_roles:
            return JsonResponse({
                'error': 'Acceso Denegado',
                'detail': 'No tienes acceso a esta zona'
            }, status=403)
        
        if role == "Admin":
            print("=== listar_reportes_costos: Admin - acceso permitido ===")
        elif role == "Manager":
            user_company = _get_user_company(request)
            if not user_company or str(user_company).upper() != str(empresa_id).upper():
                from .permissions import _log_unauthorized_access
                _log_unauthorized_access(request, empresa_id, user_company or "N/A")
                return JsonResponse({
                    'error': 'Acceso Denegado',
                    'detail': 'No tienes permiso para acceder a esta empresa'
                }, status=403)
            print("=== listar_reportes_costos: Manager - acceso permitido a su empresa ===")
        
        usuario = request.user
        reportes = [
            {
                'id': f"rpt_{empresa_id}_2025_05",
                'empresa_id': empresa_id,
                'mes': 5,
                'ano': 2025,
                'usuario': usuario.email,
                'costo_total': 2345.67,  # Simulado
                'fecha_generacion': timezone.now().isoformat(),
                'status': 'disponible',
            },
            {
                'id': f"rpt_{empresa_id}_2025_04",
                'empresa_id': empresa_id,
                'mes': 4,
                'ano': 2025,
                'usuario': usuario.email,
                'costo_total': 2150.45,  # Simulado
                'fecha_generacion': timezone.now().isoformat(),
                'status': 'disponible',
            }
        ]
        
        logger.info(
            f"[REPORTES CONSULTADOS] Empresa: {empresa_id} | "
            f"Usuario: {usuario.email} | Total: {len(reportes)}"
        )
        
        return JsonResponse({
            'total': len(reportes),
            'reportes': reportes,
        }, status=200)
    
    except Exception as e:
        logger.error(f"Error en listar_reportes_costos: {str(e)}")
        return JsonResponse({
            'error': 'Error interno',
            'detail': str(e)
        }, status=500)


@require_http_methods(["POST"])
@require_authentication
@check_company_access
@validate_report_request
def crear_reporte_costos(request, empresa_id):
    """
    POST /api/reportes/crear/{empresa_id}
    
    Crea un nuevo reporte de costos para una empresa.
    
    Body esperado:
    {
        "mes": 5,
        "ano": 2025,
        "periodo": "mensual"  // opcional
    }
    
    ASR Confidencialidad:
    - Solo acceso a empresa propia
    - Si intenta acceder a empresa diferente: 403 Forbidden + log
    - Log incluye: fecha, IP origen, usuario, token ID
    """
    try:
        role = getRole(request)
        allowed_roles = ["Admin", "Manager"]
        
        if role not in allowed_roles:
            return JsonResponse({
                'error': 'Acceso Denegado',
                'detail': 'No tienes acceso a esta zona'
            }, status=403)
        
        if role == "Admin":
            print("=== crear_reporte_costos: Admin - acceso permitido a cualquier empresa ===")
        elif role == "Manager":
            user_company = _get_user_company(request)
            if not user_company or str(user_company).upper() != str(empresa_id).upper():
                from .permissions import _log_unauthorized_access
                _log_unauthorized_access(request, empresa_id, user_company or "N/A")
                return JsonResponse({
                    'error': 'Acceso Denegado',
                    'detail': 'No tienes permiso para acceder a esta empresa'
                }, status=403)
            print("=== crear_reporte_costos: Manager - acceso permitido a su empresa ===")
        
        usuario = request.user
        
        # POST: Crear reporte
        try:
            payload = json.loads(request.body)
        except:
            return JsonResponse({
                'error': 'Payload inválido',
                'detail': 'No se pudo parsear JSON'
            }, status=400)
        
        mes = payload.get('mes')
        ano = payload.get('ano')
        periodo = payload.get('periodo', 'mensual')
        
        if not mes or not ano:
            return JsonResponse({
                'error': 'Parámetros requeridos',
                'detail': 'mes y ano son obligatorios'
            }, status=400)
        
        if not (1 <= mes <= 12):
            return JsonResponse({
                'error': 'Mes inválido',
                'detail': 'El mes debe estar entre 1 y 12'
            }, status=400)
        
        if ano < 2020 or ano > 2099:
            return JsonResponse({
                'error': 'Año inválido',
                'detail': 'El año debe estar entre 2020 y 2099'
            }, status=400)
        
        reporte = {
            'id': f"rpt_{empresa_id}_{ano}_{mes:02d}",
            'empresa_id': empresa_id,
            'mes': mes,
            'ano': ano,
            'periodo': periodo,
            'usuario': usuario.email,
            'costo_total': 1250.50,  # Simulado
            'fecha_generacion': timezone.now().isoformat(),
            'status': 'generado',
        }
        
        logger.info(
            f"[REPORTE CREADO] Empresa: {empresa_id} | "
            f"Usuario: {usuario.email} | Período: {mes}/{ano} | "
            f"Tipo: {periodo}"
        )
        
        return JsonResponse({
            'mensaje': 'Reporte generado exitosamente',
            'reporte': reporte,
        }, status=201)
    
    except Exception as e:
        logger.error(f"Error en crear_reporte_costos: {str(e)}")
        return JsonResponse({
            'error': 'Error interno',
            'detail': str(e)
        }, status=500)


@require_http_methods(["DELETE"])
@require_authentication
@validate_report_request
def eliminar_reporte(request, empresa_id):
    """
    DELETE /reportes/eliminar/{empresa_id}
    
    Elimina un reporte de costos.
    
    ASR Disponibilidad:
    - Valida empresa_id contra SQL Injection
    - Si detecta inyección: 401 Unauthorized + log en RechazoIntegridad
    - 100% de intentos de inyección son rechazados
    - Ningún dato es eliminado de la base de datos
    """
    try:
        role = getRole(request)
        allowed_roles = ["Admin", "Manager"]
        
        if role not in allowed_roles:
            return JsonResponse({
                'error': 'Acceso Denegado',
                'detail': 'No tienes acceso a esta zona'
            }, status=403)
        
        if role == "Admin":
            print("=== eliminar_reporte: Admin - acceso permitido ===")
        elif role == "Manager":
            user_company = _get_user_company(request)
            if not user_company or str(user_company).upper() != str(empresa_id).upper():
                from .permissions import _log_unauthorized_access
                _log_unauthorized_access(request, empresa_id, user_company or "N/A")
                return JsonResponse({
                    'error': 'Acceso Denegado',
                    'detail': 'No tienes permiso para acceder a esta empresa'
                }, status=403)
            print("=== eliminar_reporte: Manager - acceso permitido a su empresa ===")
        
        usuario = request.user
        
        # En producción, aquí se eliminaría el reporte de la base de datos
        # Para esta demo, simulamos el éxito
        return JsonResponse({
            'mensaje': f'Reporte de empresa {empresa_id} eliminado exitosamente',
            'empresa_id': empresa_id,
            'usuario': usuario.email,
        }, status=200)
    
    except Exception as e:
        logger.error(f"Error en eliminar_reporte: {str(e)}")
        return JsonResponse({
            'error': 'Error interno',
            'detail': str(e)
        }, status=500)


@require_http_methods(["GET", "POST", "PUT", "DELETE", "PATCH"])
def catch_all_reportes(request, empresa_id):
    """
    Catch-all para cualquier método no manejado explícitamente.
    Valida SQL Injection antes de responder.
    """
    from .validators import _detect_sql_injection, _log_integrity_violation

    if _detect_sql_injection(empresa_id):
        _log_integrity_violation(
            request,
            'SQL_INJECTION_ATTEMPTED',
            f'Se detectó intento de SQL Injection en empresa_id: {empresa_id} (método: {request.method})'
        )
        return JsonResponse({
            'error': 'No autorizado',
            'detail': 'SQL Injection detectado. Solicitud rechazada.'
        }, status=401)

    return JsonResponse({
        'error': 'Método no permitido',
        'detail': f'Método {request.method} no soportado para esta ruta'
    }, status=405)


def listar_reportes_empresa(request, empresa_id):
    """
    GET /api/reportes/empresa/{empresa_id}
    Lista todos los reportes de una empresa.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'No autorizado'}, status=401)
    
    try:
        role = getRole(request)
        allowed_roles = ["Admin", "Manager"]
        
        if role not in allowed_roles:
            return JsonResponse({
                'error': 'Acceso Denegado',
                'detail': 'No tienes acceso a esta zona'
            }, status=403)
        
        if role == "Manager":
            user_company = _get_user_company(request)
            if not user_company or str(user_company).upper() != str(empresa_id).upper():
                from .permissions import _log_unauthorized_access
                _log_unauthorized_access(request, empresa_id, user_company or "N/A")
                return JsonResponse({
                    'error': 'Acceso Denegado',
                    'detail': 'No tienes permiso para acceder a esta empresa'
                }, status=403)
        
        reportes = [
            {
                'id': f"rpt_{empresa_id}_2025_05",
                'mes': 5,
                'ano': 2025,
                'costo_total': 2345.67,
                'fecha': '2025-05-04',
            },
            {
                'id': f"rpt_{empresa_id}_2025_04",
                'mes': 4,
                'ano': 2025,
                'costo_total': 2100.50,
                'fecha': '2025-04-04',
            },
        ]
        
        logger.info(
            f"[REPORTES LISTADOS] Empresa: {empresa_id} | "
            f"Usuario: {request.user.email}"
        )
        
        return JsonResponse({
            'empresa': empresa_id,
            'total': len(reportes),
            'reportes': reportes,
        }, status=200)
    
    except Exception as e:
        logger.error(f"Error en listar_reportes_empresa: {str(e)}")
        return JsonResponse({
            'error': 'Error interno',
            'detail': str(e)
        }, status=500)


# ==================== OTROS REPORTES ====================

@require_http_methods(["GET"])
@require_authentication
def obtener_reporte_proyecto(request):
    """GET /api/reportes/proyecto - Reportes por proyecto"""
    return JsonResponse({
        'proyectos': [
            {'nombre': 'Proyecto A', 'costo': 500.00, 'proveedor': 'AWS'},
            {'nombre': 'Proyecto B', 'costo': 750.50, 'proveedor': 'GCP'},
        ]
    }, status=200)


@require_http_methods(["GET"])
@require_authentication
def obtener_consumo_nube(request):
    """GET /api/reportes/consumo - Consumo cloud detallado"""
    return JsonResponse({
        'consumo_total': 3500.00,
        'por_proveedor': {
            'AWS': 2345.67,
            'GCP': 1154.33,
        }
    }, status=200)


@require_http_methods(["GET"])
@require_authentication
def obtener_gastos_por_servicio(request):
    """GET /api/reportes/gastos - Gastos desglosados por servicio"""
    return JsonResponse({
        'gastos': [
            {'servicio': 'EC2', 'costo': 1200.00, 'proveedor': 'AWS'},
            {'servicio': 'RDS', 'costo': 800.00, 'proveedor': 'AWS'},
            {'servicio': 'Compute Engine', 'costo': 750.50, 'proveedor': 'GCP'},
        ]
    }, status=200)


@require_http_methods(["GET"])
@require_authentication
def obtener_analisis_optimizacion(request):
    """GET /api/reportes/analisis - Análisis de optimización"""
    return JsonResponse({
        'oportunidades': [
            {'tipo': 'Idle RDS', 'ahorro': 840, 'prioridad': 'alta'},
            {'tipo': 'Unattached Volumes', 'ahorro': 425, 'prioridad': 'media'},
        ]
    }, status=200)


@require_http_methods(["GET"])
@require_authentication
def obtener_tendencias(request):
    """GET /api/reportes/tendencias - Tendencias de consumo"""
    return JsonResponse({
        'tendencia': 'crecimiento',
        'mes_anterior': 3200.00,
        'mes_actual': 3500.00,
        'variacion_porcentaje': 9.4,
    }, status=200)


@require_http_methods(["GET"])
@require_authentication
def obtener_historial_reportes(request):
    """GET /api/reportes/historial - Historial de reportes generados"""
    return JsonResponse({
        'total': 12,
        'ultimos': [
            {'id': 'rpt_001', 'fecha': '2025-05-04', 'estado': 'completado'},
            {'id': 'rpt_002', 'fecha': '2025-04-04', 'estado': 'completado'},
        ]
    }, status=200)


# ==================== HEALTH CHECK ====================

@require_http_methods(["GET"])
def health_check(request):
    """GET /api/reportes/health - Health check endpoint"""
    return JsonResponse({
        'status': 'healthy',
        'service': 'reportes',
        'timestamp': timezone.now().isoformat(),
    }, status=200)


# ==================== TEMPLATE VIEWS ====================

@require_http_methods(["GET"])
@login_required
def reportes_view(request):
    """Renderiza la página de reportes"""
    return render(request, 'reportes/reportes.html')
