from django.db import models
from django.contrib.auth.models import User
import uuid

class EmpresaModel(models.Model):
    """
    Modelo para representar empresas en el sistema
    """
    id = models.CharField(max_length=100, primary_key=True, editable=False)
    nombre = models.CharField(max_length=255, default='')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'empresa_models'
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'
    
    def __str__(self):
        return f"{self.nombre} ({self.id})"


class AsociacionUsuarioEmpresa(models.Model):
    """
    Modelo para asociar usuarios con empresas
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='empresas_asociadas')
    empresa = models.ForeignKey(EmpresaModel, on_delete=models.CASCADE, related_name='usuarios_asociados')
    rol = models.CharField(
        max_length=50,
        choices=[
            ('admin', 'Administrador'),
            ('usuario', 'Usuario'),
            ('gerente', 'Gerente'),
        ],
        default='usuario'
    )
    fecha_asociacion = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'asociacion_usuario_empresa'
        verbose_name = 'Asociación Usuario Empresa'
        verbose_name_plural = 'Asociaciones Usuario Empresa'
        unique_together = ('usuario', 'empresa')
    
    def __str__(self):
        return f"{self.usuario.username} - {self.empresa.nombre}"
