from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
from datetime import timedelta

class Usuario(models.Model):
    """
    Modelo de extensión para Usuario que complementa el User nativo de Django
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario_django = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil_autenticacion')
    empresa = models.CharField(max_length=255, null=True, blank=True)
    rol = models.CharField(
        max_length=50,
        choices=[
            ('admin', 'Administrador'),
            ('usuario', 'Usuario'),
            ('gerente', 'Gerente'),
        ],
        default='usuario'
    )
    activo = models.BooleanField(default=True)
    bloqueado = models.BooleanField(default=False)
    fecha_bloqueo = models.DateTimeField(null=True, blank=True)
    razon_bloqueo = models.TextField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'usuarios'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return f"{self.usuario_django.username} ({self.usuario_django.email})"


class Token(models.Model):
    """
    Modelo para almacenar tokens JWT
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='tokens')
    token_access = models.TextField()
    token_refresh = models.TextField(null=True, blank=True)
    fecha_expiracion = models.DateTimeField()
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_revocacion = models.DateTimeField(null=True, blank=True)
    motivo_revocacion = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'tokens'
        verbose_name = 'Token'
        verbose_name_plural = 'Tokens'

    def __str__(self):
        return f"Token de {self.usuario.username}"

    def es_valido(self):
        """Verifica si el token aún es válido"""
        return self.activo and timezone.now() < self.fecha_expiracion


class AuditoriaAcceso(models.Model):
    """
    Modelo para registrar intentos de acceso y detectar anomalías
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='auditorias_acceso', null=True, blank=True)
    username = models.CharField(max_length=150)
    direccion_ip = models.GenericIPAddressField()
    user_agent = models.TextField(null=True, blank=True)
    tipo_evento = models.CharField(
        max_length=50,
        choices=[
            ('login_exitoso', 'Login Exitoso'),
            ('login_fallido', 'Login Fallido'),
            ('registro_exitoso', 'Registro Exitoso'),
            ('acceso_denegado', 'Acceso Denegado'),
            ('token_refresh', 'Refresh de Token'),
            ('cuenta_bloqueada', 'Cuenta Bloqueada'),
        ]
    )
    motivo_rechazo = models.CharField(max_length=255, null=True, blank=True)
    fecha_evento = models.DateTimeField(auto_now_add=True)
    detalles = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'auditoria_acceso'
        verbose_name = 'Auditoría de Acceso'
        verbose_name_plural = 'Auditorías de Acceso'
        indexes = [
            models.Index(fields=['username', 'fecha_evento']),
            models.Index(fields=['direccion_ip', 'fecha_evento']),
            models.Index(fields=['tipo_evento', 'fecha_evento']),
        ]

    def __str__(self):
        return f"{self.username} - {self.tipo_evento} - {self.fecha_evento}"


class IntentoBloqueado(models.Model):
    """
    Modelo para registrar intentos bloqueados y restricciones temporales
    ASR: Detección de anomalías en menos de 2 segundos
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    direccion_ip = models.GenericIPAddressField(db_index=True)
    username = models.CharField(max_length=150, null=True, blank=True, db_index=True)
    tipo_anomalia = models.CharField(
        max_length=50,
        choices=[
            ('multiples_intentos_fallidos', 'Múltiples Intentos Fallidos'),
            ('ataque_fuerza_bruta', 'Ataque de Fuerza Bruta'),
            ('patron_sospechoso', 'Patrón Sospechoso'),
        ]
    )
    numero_intentos = models.IntegerField(default=1)
    fecha_primer_intento = models.DateTimeField(auto_now_add=True)
    fecha_ultimo_intento = models.DateTimeField(auto_now=True)
    fecha_bloqueo_hasta = models.DateTimeField()
    activo = models.BooleanField(default=True)
    duracion_bloqueo_segundos = models.IntegerField(default=300)
    razon_bloqueo = models.TextField()

    class Meta:
        db_table = 'intentos_bloqueados'
        verbose_name = 'Intento Bloqueado'
        verbose_name_plural = 'Intentos Bloqueados'
        indexes = [
            models.Index(fields=['direccion_ip', 'activo']),
            models.Index(fields=['username', 'activo']),
            models.Index(fields=['fecha_bloqueo_hasta']),
        ]

    def __str__(self):
        return f"Bloqueo de {self.direccion_ip} - {self.tipo_anomalia}"

    def esta_bloqueado(self):
        """Verifica si el bloqueo aún está activo"""
        return self.activo and timezone.now() < self.fecha_bloqueo_hasta

    def desbloquear(self):
        """Desbloquea el acceso"""
        self.activo = False
        self.save()


class Permiso(models.Model):
    """
    Modelo para gestión de permisos
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.CharField(max_length=100, unique=True)
    nombre = models.CharField(max_length=255)
    descripcion = models.TextField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'permisos'
        verbose_name = 'Permiso'
        verbose_name_plural = 'Permisos'

    def __str__(self):
        return self.nombre


class RolPermiso(models.Model):
    """
    Modelo de asociación entre Roles y Permisos (relación M2M)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rol = models.CharField(max_length=50)
    permiso = models.ForeignKey(Permiso, on_delete=models.CASCADE)
    fecha_asignacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'rol_permisos'
        verbose_name = 'Rol Permiso'
        verbose_name_plural = 'Rol Permisos'
        unique_together = ['rol', 'permiso']

    def __str__(self):
        return f"{self.rol} - {self.permiso.codigo}"
