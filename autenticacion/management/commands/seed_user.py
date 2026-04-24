from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from autenticacion.models import Usuario


class Command(BaseCommand):
    help = 'Crea el usuario admin por defecto si no existe'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='admin')
        parser.add_argument('--email', default='admin@bite.co')
        parser.add_argument('--password', default='Admin1234!')
        parser.add_argument('--first_name', default='Admin')
        parser.add_argument('--last_name', default='CloudyNet')
        parser.add_argument('--empresa', default='BITE.CO')
        parser.add_argument('--rol', default='admin')

    def handle(self, *args, **options):
        username = options['username']
        if User.objects.filter(username=username).exists():
            self.stdout.write(f"Usuario '{username}' ya existe, no se crea de nuevo.")
            return
        u = Usuario.create_user(
            username=username,
            email=options['email'],
            password=options['password'],
            first_name=options['first_name'],
            last_name=options['last_name'],
            empresa=options['empresa'],
            rol=options['rol'],
        )
        self.stdout.write(self.style.SUCCESS(
            f"Usuario '{u.usuario_django.username}' creado con rol '{u.rol}'."
        ))
