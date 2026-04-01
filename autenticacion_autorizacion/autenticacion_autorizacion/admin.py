"""
Configuración del admin de Django para el servicio de autenticación
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import Usuario, Token, AuditoriaAcceso, IntentoBloqueado, Permiso, RolPermiso


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'rol', 'empresa', 'activo', 'bloqueado', 'fecha_creacion']
    list_filter = ['rol', 'activo', 'bloqueado', 'fecha_creacion']
    search_fields = ['username', 'email', 'empresa']
    readonly_fields = ['id', 'fecha_creacion', 'fecha_actualizacion']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('id', 'username', 'email', 'first_name', 'last_name')
        }),
        ('Empresa', {
            'fields': ('empresa',)
        }),
        ('Permisos y Roles', {
            'fields': ('rol', 'groups', 'user_permissions', 'is_staff', 'is_superuser')
        }),
        ('Estado de Cuenta', {
            'fields': ('activo', 'bloqueado', 'fecha_bloqueo', 'razon_bloqueo')
        }),
        ('Fechas', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'es_valido_display', 'fecha_expiracion', 'fecha_creacion']
    list_filter = ['activo', 'fecha_creacion', 'fecha_expiracion']
    search_fields = ['usuario__username', 'usuario__email']
    readonly_fields = ['id', 'fecha_creacion', 'fecha_revocacion']
    
    def es_valido_display(self, obj):
        es_valido = obj.es_valido()
        color = 'green' if es_valido else 'red'
        texto = 'Válido' if es_valido else 'Expirado'
        return format_html(f'<span style="color: {color};">{texto}</span>')
    es_valido_display.short_description = 'Estado'


@admin.register(AuditoriaAcceso)
class AuditoriaAccesoAdmin(admin.ModelAdmin):
    list_display = ['username', 'tipo_evento', 'direccion_ip', 'fecha_evento']
    list_filter = ['tipo_evento', 'fecha_evento']
    search_fields = ['username', 'direccion_ip']
    readonly_fields = ['id', 'fecha_evento']
    date_hierarchy = 'fecha_evento'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(IntentoBloqueado)
class IntentoBloqueadoAdmin(admin.ModelAdmin):
    list_display = ['direccion_ip', 'username', 'tipo_anomalia', 'numero_intentos', 'esta_bloqueado_display']
    list_filter = ['tipo_anomalia', 'activo', 'fecha_primer_intento']
    search_fields = ['direccion_ip', 'username']
    readonly_fields = ['id', 'fecha_primer_intento']
    
    def esta_bloqueado_display(self, obj):
        bloqueado = obj.esta_bloqueado()
        color = 'red' if bloqueado else 'green'
        texto = 'Bloqueado' if bloqueado else 'Desbloqueado'
        return format_html(f'<span style="color: {color};">{texto}</span>')
    esta_bloqueado_display.short_description = 'Estado de Bloqueo'


@admin.register(Permiso)
class PermisoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre']
    search_fields = ['codigo', 'nombre']
    readonly_fields = ['id', 'fecha_creacion']


@admin.register(RolPermiso)
class RolPermisoAdmin(admin.ModelAdmin):
    list_display = ['rol', 'permiso', 'fecha_asignacion']
    list_filter = ['rol', 'fecha_asignacion']
    search_fields = ['rol', 'permiso__codigo']
