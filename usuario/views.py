from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.models import User
from django.middleware.csrf import get_token
import json

@require_http_methods(["GET"])
def listar_usuarios(request):
    """
    GET /usuario/listar/
    Retorna lista de todos los usuarios del sistema con su rol
    """
    try:
        from autenticacion.models import Usuario as UsuarioModel
        usuarios_data = []
        for user in User.objects.all():
            usuario_model = UsuarioModel.objects.filter(usuario_django=user).first()
            usuarios_data.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'rol': usuario_model.rol if usuario_model else 'usuario',
            })
        return JsonResponse({
            'total': len(usuarios_data),
            'usuarios': usuarios_data
        }, status=200)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@require_http_methods(["POST"])
def asignar_rol(request):
    """
    POST /usuario/asignar-rol/
    Asigna un rol a un usuario

    Body:
    {
        "usuario_id": int,
        "rol": str (admin, gerente, usuario)
    }
    """
    try:
        data = json.loads(request.body)

        usuario_id = data.get('usuario_id')
        rol = data.get('rol')

        if not usuario_id or not rol:
            return JsonResponse({
                'error': 'usuario_id y rol son requeridos'
            }, status=400)

        roles_validos = ['admin', 'gerente', 'usuario']
        if rol not in roles_validos:
            return JsonResponse({
                'error': f'Rol invalido. Debe ser uno de: {", ".join(roles_validos)}'
            }, status=400)

        try:
            django_user = User.objects.get(id=usuario_id)
        except User.DoesNotExist:
            return JsonResponse({
                'error': f'Usuario con id {usuario_id} no existe'
            }, status=404)

        from autenticacion.models import Usuario as UsuarioModel
        usuario_model = UsuarioModel.objects.filter(usuario_django=django_user).first()

        if usuario_model:
            usuario_model.rol = rol
            usuario_model.save()
        else:
            usuario_model = UsuarioModel.objects.create(
                usuario_django=django_user,
                rol=rol,
                activo=True,
            )

        return JsonResponse({
            'mensaje': f'Rol "{rol}" asignado exitosamente a {django_user.username}',
            'usuario': {
                'id': usuario_model.id,
                'username': django_user.username,
                'rol': usuario_model.rol,
            }
        }, status=200)

    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'JSON invalido en body'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@require_http_methods(["DELETE"])
def eliminar_usuario(request):
    """
    DELETE /usuario/eliminar/
    Elimina un usuario del sistema (Django User + Usuario model)

    Body:
    {
        "usuario_id": int
    }
    """
    try:
        data = json.loads(request.body)

        usuario_id = data.get('usuario_id')

        if not usuario_id:
            return JsonResponse({
                'error': 'usuario_id es requerido'
            }, status=400)

        try:
            django_user = User.objects.get(id=usuario_id)
        except User.DoesNotExist:
            return JsonResponse({
                'error': f'Usuario con id {usuario_id} no existe'
            }, status=404)

        username = django_user.username

        from autenticacion.models import Usuario as UsuarioModel
        usuario_model = UsuarioModel.objects.filter(usuario_django=django_user).first()

        if usuario_model:
            usuario_model.delete()

        django_user.delete()

        return JsonResponse({
            'mensaje': f'Usuario "{username}" eliminado exitosamente',
        }, status=200)

    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'JSON invalido en body'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


def usuario_view(request):
    """
    GET /usuario/
    Renderiza template de gestion de usuarios
    """
    return render(request, 'usuario/usuario.html')
