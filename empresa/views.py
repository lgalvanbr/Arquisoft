from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.models import User
from .models import EmpresaModel, AsociacionUsuarioEmpresa
import json

@require_http_methods(["GET"])
def listar_empresas(request):
    """
    GET /api/empresas/
    Retorna lista de todas las empresas del sistema
    """
    try:
        empresas = EmpresaModel.objects.all().values('id', 'nombre', 'fecha_creacion')
        return JsonResponse({
            'total': empresas.count(),
            'empresas': list(empresas)
        }, status=200)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@require_http_methods(["POST"])
def crear_empresa(request):
    """
    POST /empresa/crear/
    Crea una nueva empresa
    
    Body:
    {
        "id": str,
        "nombre": str
    }
    """
    try:
        data = json.loads(request.body)
        
        empresa_id = data.get('id')
        nombre = data.get('nombre')
        
        if not empresa_id or not nombre:
            return JsonResponse({
                'error': 'id y nombre son requeridos'
            }, status=400)
        
        if EmpresaModel.objects.filter(id=empresa_id).exists():
            return JsonResponse({
                'error': f'Empresa con id {empresa_id} ya existe'
            }, status=409)
        
        empresa = EmpresaModel.objects.create(
            id=empresa_id,
            nombre=nombre
        )
        
        return JsonResponse({
            'mensaje': 'Empresa creada exitosamente',
            'empresa': {
                'id': empresa.id,
                'nombre': empresa.nombre,
                'fecha_creacion': empresa.fecha_creacion.isoformat()
            }
        }, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'JSON inválido en body'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@require_http_methods(["POST"])
def asociar_usuario_empresa(request):
    """
    POST /empresa/asociar/
    Asocia un usuario con una empresa
    
    Body:
    {
        "usuario_id": int,
        "empresa_id": str
    }
    """
    try:
        data = json.loads(request.body)
        
        usuario_id = data.get('usuario_id')
        empresa_id = data.get('empresa_id')
        
        if not usuario_id or not empresa_id:
            return JsonResponse({
                'error': 'usuario_id y empresa_id son requeridos'
            }, status=400)
        
        try:
            usuario = User.objects.get(id=usuario_id)
        except User.DoesNotExist:
            return JsonResponse({
                'error': f'Usuario con id {usuario_id} no existe'
            }, status=404)
        
        try:
            empresa = EmpresaModel.objects.get(id=empresa_id)
        except EmpresaModel.DoesNotExist:
            return JsonResponse({
                'error': f'Empresa con id {empresa_id} no existe'
            }, status=404)
        
        asociacion, creado = AsociacionUsuarioEmpresa.objects.get_or_create(
            usuario=usuario,
            empresa=empresa,
            defaults={'rol': 'usuario'}
        )
        
        if not creado:
            asociacion.activo = True
            asociacion.save()
        
        return JsonResponse({
            'mensaje': 'Asociación creada exitosamente' if creado else 'Asociación actualizada',
            'asociacion': {
                'usuario_id': usuario.id,
                'usuario_username': usuario.username,
                'empresa_id': empresa.id,
                'empresa_nombre': empresa.nombre,
                'rol': asociacion.rol,
                'fecha_asociacion': asociacion.fecha_asociacion.isoformat(),
                'activo': asociacion.activo
            }
        }, status=201 if creado else 200)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'JSON inválido en body'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


def empresa_view(request):
    """
    GET /empresa/
    Renderiza template de asociación usuario-empresa
    """
    return render(request, 'empresa/empresa.html')
