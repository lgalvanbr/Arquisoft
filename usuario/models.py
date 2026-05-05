from django.db import models
from django.contrib.auth.models import User

class UsuarioProfile(models.Model):
    """
    Profile simplificado para Usuario que usa el User nativo de Django
    """
    usuario_django = models.OneToOneField(User, on_delete=models.CASCADE, related_name='usuario_profile')
    
    class Meta:
        db_table = 'usuario_profiles'
        verbose_name = 'Usuario Profile'
        verbose_name_plural = 'Usuario Profiles'
    
    def __str__(self):
        return f"{self.usuario_django.username} ({self.usuario_django.email})"
