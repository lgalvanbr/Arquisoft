# FinOps Platform - Despliegue con Auth0 (Opción A: Hardcode Manual)

## 📋 Descripción General

Este proyecto implementa autenticación Auth0 usando **django-social-auth** siguiendo el laboratorio ISIS2503.
La configuración de `LOGOUT_REDIRECT_URL` se realiza **manualmente después de obtener la IP pública** (Opción A).

## 🔧 Stack Técnico

- **Framework**: Django 4.2
- **Auth**: Auth0 + python-social-auth
- **Backend**: PostgreSQL
- **Servidor**: Gunicorn (4 workers, puerto 8080, systemd service)
- **Infraestructura**: AWS (Terraform)
  - Load Balancer en puerto 80
  - App instances (app-a, app-b) en puerto 8080 (Gunicorn)
  - Database (PostgreSQL) en puerto 5432

## 📁 Estructura de Archivos Relevantes

```
finops_platform/
├── settings.py                 # LOGOUT_REDIRECT_URL se edita aquí
├── urls.py                     # Rutas de social_django
├── templates/
│   └── index.html             # Login/Logout buttons
└── wsgi.py

autenticacion/
└── auth0backend.py            # Clase Auth0(BaseOAuth2)

terraform/
└── deployment.tf              # Infraestructura AWS

requirements.txt               # social-auth-app-django==4.0.0
```

## 🚀 Flujo de Despliegue (Opción A)

### Paso 1: Desplegar Infraestructura

```bash
cd terraform
terraform apply -auto-approve
```

**Salida esperada:**
```
Apply complete! Resources created in 1 resources added, 0 changed, 0 destroyed.

Outputs:

access_url = "http://report-alb-1234567890.us-east-1.elb.amazonaws.com"
app_instances_public_ips = {
  "a" = "54.123.45.67"
  "b" = "52.987.65.43"
}
database_public_ip = "18.234.56.78"
```

### Paso 2: Obtener IP Pública de app-a

```bash
# Desde terraform output
terraform output -raw "app_instances_public_ips"

# O si quieres extraerla directamente:
export APP_A_IP=$(terraform output -json app_instances_public_ips | jq -r '.a')
echo "App-a IP: $APP_A_IP"
# Ejemplo: App-a IP: 54.123.45.67
```

### Paso 3: Editar settings.py con la IP Pública

**Opción 3a: Editar localmente y hacer push**

```bash
# En tu máquina local
# Editar finops_platform/settings.py:
# Línea con LOGOUT_REDIRECT_URL, cambiar de:
#   LOGOUT_REDIRECT_URL = 'https://dev-vy27mzsmkwosyqhr.us.auth0.com/v2/logout?returnTo=http://localhost:8080'
# A:
#   LOGOUT_REDIRECT_URL = 'https://dev-vy27mzsmkwosyqhr.us.auth0.com/v2/logout?returnTo=http://54.123.45.67:8080'

git add finops_platform/settings.py
git commit -m "Update LOGOUT_REDIRECT_URL with production IP"
git push origin main
```

**Opción 3b: Editar directamente en la instancia via SSH**

```bash
# SSH a app-a
ssh -i key.pem ec2-user@54.123.45.67

# Editar settings.py en la instancia
nano /apps/Arquisoft/finops_platform/settings.py

# Buscar línea: LOGOUT_REDIRECT_URL = '...'
# Cambiar localhost:8080 por 54.123.45.67:8080
# Ctrl+X → Y → Enter

# Salir
exit
```

### Paso 4: SSH a app-a y Verificar que Gunicorn está Activo

```bash
# Conectar a la instancia
ssh -i key.pem ec2-user@54.123.45.67

# Verificar que el servicio cloudynet.service está activo
systemctl status cloudynet.service

# Salida esperada:
# ● cloudynet.service - CloudyNet FinOps Gunicorn (app-a)
#    Loaded: loaded (/etc/systemd/system/cloudynet.service; enabled; preset: enabled)
#    Active: active (running) since Sun 2025-05-04 12:34:56 UTC; 5min ago
```

**Nota**: Las migraciones se ejecutaron automáticamente durante cloud-init en el despliegue. 
No necesitas ejecutarlas manualmente a menos que fallasen.

### Verificación de Gunicorn

```bash
# Ver logs de Gunicorn
tail -f /var/log/gunicorn-access.log
tail -f /var/log/gunicorn-error.log

# Ver logs del setup inicial
tail -f /var/log/cloudynet-setup.log

# Verificar que Gunicorn escucha en puerto 8080
netstat -tlnp | grep 8080
```

### Paso 5: Acceder a la Aplicación

**Opción 5a: Acceso directo a app-a**
```
http://54.123.45.67:8080
```

**Opción 5b: A través del Load Balancer (http sin puerto)**
```
http://report-alb-1234567890.us-east-1.elb.amazonaws.com
```

## 🔐 Flujos de Autenticación

### Login Flow

```
1. Usuario abre http://<IP>:8080
   ↓
2. Click "Ingresar con Auth0"
   ↓
3. GET /login/auth0
   ↓ (ruta de social_django)
4. Redirige a:
   https://dev-vy27mzsmkwosyqhr.us.auth0.com/authorize?
     client_id=hLSCIWW4Wof9DJeDv58kPXBLX07YLZCA&
     redirect_uri=http://<IP>:8080/complete/auth0/&
     scope=openid+profile+email+role&
     ...
   ↓
5. Usuario se autentica en Auth0 popup
   ↓
6. Auth0 redirige a /complete/auth0/?code=...&state=...
   ↓ (social_django backend)
7. Backend intercambia code por access_token
   ↓
8. Backend llama get_user_details() → /userinfo endpoint
   ↓
9. Django crea User + SocialAuth record
   ↓
10. Redirige a LOGIN_REDIRECT_URL = "/"
    ↓
11. Dashboard visible ✓ (usuario autenticado)
```

### Logout Flow

```
1. Click "Cerrar sesión"
   ↓
2. GET /accounts/logout/
   ↓ (ruta de django.contrib.auth)
3. Destruye sesión Django
   ↓
4. Redirige a LOGOUT_REDIRECT_URL
   ↓
5. LOGOUT_REDIRECT_URL = "https://dev-vy27mzsmkwosyqhr.us.auth0.com/v2/logout?returnTo=http://54.123.45.67:8080"
   ↓
6. Auth0 cierra sesión y limpia cookies
   ↓
7. Redirige a http://54.123.45.67:8080
   ↓
8. Usuario logueado salida ✓ (vuelve a auth-section)
```

## 🔍 Troubleshooting

### Problema: Gunicorn no arranca automáticamente

**Solución**: Verificar logs del systemd service:
```bash
ssh -i key.pem ec2-user@<IP>
systemctl status cloudynet.service
journalctl -u cloudynet.service -n 50
```

### Problema: "LOGOUT_REDIRECT_URL inválida"
**Solución**: Verificar que la IP y puerto (8080) están correctos en settings.py

### Problema: Load Balancer devuelve 502
**Solución**: 
```bash
# Verificar que Gunicorn está running
ssh -i key.pem ec2-user@<IP>
systemctl status cloudynet.service

# Revisar logs
tail -f /var/log/gunicorn-error.log
journalctl -u cloudynet.service -f
```

### Problema: Login loop infinito
**Solución**: Verificar que `SOCIAL_AUTH_AUTH0_KEY` y `SOCIAL_AUTH_AUTH0_SECRET` coinciden con Auth0 credentials

### Problema: Migraciones no corridas
**Solución**:
```bash
ssh -i key.pem ec2-user@<IP>
cd /apps/Arquisoft
source /apps/venv/bin/activate
python manage.py migrate --noinput
systemctl restart cloudynet.service
```

### Problema: Actualizar código desde git
**Solución**: Usar el script `cloudynet-update` incluido:
```bash
ssh -i key.pem ec2-user@<IP>
sudo cloudynet-update

# Esto hace:
# 1. git fetch + reset --hard a la rama actual
# 2. Reinstala requirements.txt
# 3. Ejecuta migraciones
# 4. Reinicia Gunicorn
```

## 📝 Archivos Clave

### `finops_platform/settings.py`
```python
LOGIN_URL = "/login/auth0"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = 'https://dev-vy27mzsmkwosyqhr.us.auth0.com/v2/logout?returnTo=http://<IP>:8080'

SOCIAL_AUTH_AUTH0_DOMAIN = 'dev-vy27mzsmkwosyqhr.us.auth0.com'
SOCIAL_AUTH_AUTH0_KEY = 'hLSCIWW4Wof9DJeDv58kPXBLX07YLZCA'
SOCIAL_AUTH_AUTH0_SECRET = 'Jn1VRUtos80bWySfxL5HFHk-aMu30fZM0CyKsRyaREIsGwVAq6y2rXmN4GmCbRAZ'

SOCIAL_AUTH_AUTH0_SCOPE = ['openid', 'profile', 'email', 'role']

AUTHENTICATION_BACKENDS = (
    'autenticacion.auth0backend.Auth0',
    'django.contrib.auth.backends.ModelBackend',
)
```

### `autenticacion/auth0backend.py`
```python
class Auth0(BaseOAuth2):
    name = 'auth0'
    
    def authorization_url(self):
        return "https://" + self.setting('DOMAIN') + "/authorize"
    
    def access_token_url(self):
        return "https://" + self.setting('DOMAIN') + "/oauth/token"
    
    def get_user_details(self, response):
        # Llama a /userinfo endpoint
        url = 'https://' + self.setting('DOMAIN') + '/userinfo'
        headers = {'authorization': 'Bearer ' + response['access_token']}
        resp = requests.get(url, headers=headers)
        userinfo = resp.json()
        
        return {
            'username': userinfo['nickname'],
            'first_name': userinfo['name'],
            'picture': userinfo['picture'],
            'user_id': userinfo['sub']
        }

def getRole(user):
    """Extrae rol de Auth0 custom claims"""
    try:
        social_user = user.social_user.get(provider='auth0')
        extra_data = social_user.extra_data
        rol = extra_data.get('https://finops-api/rol', 'usuario')
        return rol
    except:
        return 'usuario'
```

### `finops_platform/urls.py`
```python
urlpatterns = [
    # Auth0 / Social Auth paths
    path('', include('django.contrib.auth.urls')),
    path('', include('social_django.urls')),
    
    # API endpoints
    path('api/auth/me', auth_views.obtener_usuario_actual),
    # ... más endpoints
]
```

### `finops_platform/templates/index.html`
```html
<!-- Login button -->
<a href="/login/auth0" class="btn">Ingresar con Auth0</a>

<!-- Logout button -->
<button onclick="location.href='/accounts/logout/'" class="btn">Cerrar sesión</button>
```

## ✅ Checklist de Despliegue

- [ ] Ejecutar `terraform apply -auto-approve`
- [ ] Obtener IP pública de app-a
- [ ] Editar LOGOUT_REDIRECT_URL en `settings.py` con IP real
- [ ] Git commit y push (o SSH y editar manualmente)
- [ ] SSH a app-a y verificar que `systemctl status cloudynet.service` está activo
- [ ] (Opcional) Verificar migraciones: `python manage.py migrate --noinput`
- [ ] Acceder a http://<IP>:8080
- [ ] Probar login con Auth0
- [ ] Probar logout
- [ ] Verificar logs: `tail -f /var/log/gunicorn-access.log`

## 🔗 Referencias

- [Django Social Auth Docs](https://python-social-auth.readthedocs.io/)
- [Auth0 OAuth2 Integration](https://auth0.com/docs/get-started/authentication-and-authorization-flow)
- [Lab ISIS2503](https://github.com/lgalvanbr/isis2503-laboratorio)
