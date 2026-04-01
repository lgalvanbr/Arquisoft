from django.contrib import admin
from .models import Usuario, Token, AuditoriaAcceso, IntentoBloqueado, Permiso, RolPermiso


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('get_username', 'get_email', 'empresa', 'rol', 'activo', 'bloqueado', 'fecha_creacion')
    list_filter = ('rol', 'activo', 'bloqueado', 'fecha_creacion')
    search_fields = ('usuario_django__username', 'usuario_django__email', 'empresa')
    readonly_fields = ('id', 'fecha_creacion', 'fecha_actualizacion')
    
    def get_username(self, obj):
        return obj.usuario_django.username
    get_username.short_description = 'Username'
    
    def get_email(self, obj):
        return obj.usuario_django.email
    get_email.short_description = 'Email'


@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'activo', 'fecha_expiracion', 'fecha_creacion')
    list_filter = ('activo', 'fecha_creacion')
    search_fields = ('usuario__username',)
    readonly_fields = ('id', 'fecha_creacion')


@admin.register(AuditoriaAcceso)
class AuditoriaAccesoAdmin(admin.ModelAdmin):
    list_display = ('username', 'tipo_evento', 'direccion_ip', 'fecha_evento')
    list_filter = ('tipo_evento', 'fecha_evento')
    search_fields = ('username', 'direccion_ip')
    readonly_fields = ('id', 'fecha_evento')


@admin.register(IntentoBloqueado)
class IntentoBloqueadoAdmin(admin.ModelAdmin):
    list_display = ('direccion_ip', 'username', 'tipo_anomalia', 'activo', 'fecha_bloqueo_hasta')
    list_filter = ('tipo_anomalia', 'activo', 'fecha_bloqueo_hasta')
    search_fields = ('direccion_ip', 'username')
    readonly_fields = ('id', 'fecha_primer_intento', 'fecha_ultimo_intento')


@admin.register(Permiso)
class PermisoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'fecha_creacion')
    list_filter = ('fecha_creacion',)
    search_fields = ('codigo', 'nombre')
    readonly_fields = ('id', 'fecha_creacion')


@admin.register(RolPermiso)
class RolPermisoAdmin(admin.ModelAdmin):
    list_display = ('rol', 'permiso', 'fecha_asignacion')
    list_filter = ('rol', 'fecha_asignacion')
    search_fields = ('rol', 'permiso__codigo')
    readonly_fields = ('id', 'fecha_asignacion')
