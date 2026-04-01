# 🚀 QUICK START - Guía de Inicio Rápido

## Opción 1: Ejecución Local (Recomendado para Desarrollo)

### Requisitos Previos
```
Python 3.9+
PostgreSQL 13+
Git
pip y virtualenv
```

### Pasos

```bash
# 1. Clonar/Descargar proyecto
cd Arquisoft

# 2. Crear entorno virtual
python -m venv env

# Activar (Windows)
env\Scripts\activate

# Activar (Linux/Mac)
source env/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Crear bases de datos PostgreSQL
# En terminal PostgreSQL:
psql -U postgres
CREATE DATABASE autenticacion_db;
CREATE DATABASE reportes_db;
\q

# 5. Configurar variables de entorno
cp .env.example .env
# Editar .env si es necesario (por defecto localhost:postgres)

# 6. Crear migraciones e inicializar BD (Autenticación)
cd autenticacion_autorizacion
python manage.py migrate
python manage.py createsuperuser  # Crear admin
cd ..

# 7. Crear migraciones e inicializar BD (Reportes)
cd reportes
python manage.py migrate
python manage.py createsuperuser  # Crear admin
cd ..

# 8. Ejecutar servidores (en terminales separadas)

# Terminal 1: Servicio de Autenticación (Puerto 8000)
cd autenticacion_autorizacion
python manage.py runserver 8000

# Terminal 2: Servicio de Reportes (Puerto 8001)
cd reportes
python manage.py runserver 8001

# 9. Acceder
# - API Autenticación: http://localhost:8000/api/
# - Admin Autenticación: http://localhost:8000/admin (usuario/contraseña)
# - API Reportes: http://localhost:8001/api/
# - Admin Reportes: http://localhost:8001/admin (usuario/contraseña)
```

---

## Opción 2: Docker Compose (Recomendado para Producción)

### Requisitos Previos
```
Docker
Docker Compose
```

### Pasos

```bash
# 1. Clonar/Descargar proyecto
cd Arquisoft

# 2. Iniciar servicios
docker-compose up -d

# 3. Ver estado de servicios
docker-compose ps

# 4. Crear superusuarios (si es necesario)
docker-compose exec auth_service python manage.py createsuperuser
docker-compose exec reportes_service python manage.py createsuperuser

# 5. Acceder
# - API Autenticación: http://localhost:8000/api/
# - Admin Autenticación: http://localhost:8000/admin
# - API Reportes: http://localhost:8001/api/
# - Admin Reportes: http://localhost:8001/admin
# - Nginx: http://localhost

# Ver logs
docker-compose logs -f auth_service
docker-compose logs -f reportes_service

# Detener
docker-compose down

# Limpiar (datos incluidos)
docker-compose down -v
```

---

## 🧪 Pruebas Iniciales

### 1. Health Check
```bash
curl http://localhost:8000/api/health
curl http://localhost:8001/api/health
```

### 2. Registro de Usuario
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "test@example.com",
    "email": "test@example.com",
    "password": "Test123456!",
    "empresa": "BITE.CO"
  }'
```

### 3. Login
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "test@example.com",
    "password": "Test123456!"
  }'
```

**Guardar el token `access` para próximas pruebas**

### 4. Obtener Usuario Actual
```bash
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer <TOKEN_AQUI>"
```

### 5. Obtener Reporte Mensual
```bash
curl "http://localhost:8001/api/reportes/mensual?empresa_id=550e8400-e29b-41d4-a716-446655440000&año=2024&mes=1" \
  -H "Authorization: Bearer <TOKEN_AQUI>"
```

---

## 📊 Estructura de Carpetas Clave

```
Arquisoft/
├── autenticacion_autorizacion/
│   ├── autenticacion_autorizacion/
│   │   ├── models.py              ← Modelos de BD
│   │   ├── views.py               ← Endpoints
│   │   ├── urls.py                ← Rutas
│   │   ├── settings.py            ← Configuración
│   │   ├── utilities.py           ← Lógica de negocio
│   │   └── admin.py               ← Panel admin
│   ├── manage.py
│   └── Dockerfile
│
├── reportes/
│   ├── reportes/
│   │   ├── models.py              ← Modelos de BD
│   │   ├── views.py               ← Endpoints
│   │   ├── urls.py                ← Rutas
│   │   ├── settings.py            ← Configuración
│   │   ├── utilities.py           ← Lógica de negocio
│   │   └── admin.py               ← Panel admin
│   ├── manage.py
│   └── Dockerfile
│
├── requirements.txt               ← Dependencias Python
├── .env.example                   ← Variables de entorno
├── docker-compose.yml             ← Orquestación Docker
├── README.md                      ← Documentación general
├── API_ENDPOINTS.md               ← Documentación API
└── RESUMEN_EJECUTIVO.md          ← Resumen del proyecto
```

---

## 🔍 Comandos Útiles

### Django

```bash
# Ver estado de migraciones
python manage.py showmigrations

# Crear nueva migración
python manage.py makemigrations

# Aplicar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Shell de Django interactivo
python manage.py shell

# Ejecutar tests (cuando existan)
python manage.py test
```

### Docker

```bash
# Ver logs de un servicio
docker-compose logs auth_service

# Seguimiento de logs en vivo
docker-compose logs -f reportes_service

# Ejecutar comando en contenedor
docker-compose exec auth_service python manage.py createsuperuser

# Reconstruir imágenes
docker-compose build

# Detener servicios
docker-compose stop

# Iniciar servicios (sin recrear)
docker-compose start

# Eliminar todo
docker-compose down -v
```

---

## ⚙️ Variables de Entorno Importantes

```bash
# BD Autenticación
AUTH_DB_NAME=autenticacion_db
AUTH_DB_USER=postgres
AUTH_DB_PASSWORD=postgres
AUTH_DB_HOST=localhost
AUTH_DB_PORT=5432

# BD Reportes
REPORTES_DB_NAME=reportes_db
REPORTES_DB_USER=postgres
REPORTES_DB_PASSWORD=postgres
REPORTES_DB_HOST=localhost
REPORTES_DB_PORT=5432

# Seguridad
DEBUG=False
SECRET_KEY_AUTH=<random-key>
SECRET_KEY_REPORTES=<random-key>
JWT_SECRET_KEY=<random-key>

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000,http://localhost:8001
```

---

## 📱 Testing con Postman/Insomnia

### Colección de Requests Básico

#### 1. Register
```
POST http://localhost:8000/api/auth/register
Body: {
  "username": "test@bite.co",
  "email": "test@bite.co",
  "password": "SecurePass123!",
  "empresa": "BITE.CO"
}
```

#### 2. Login
```
POST http://localhost:8000/api/auth/login
Body: {
  "username": "test@bite.co",
  "password": "SecurePass123!"
}
Save: {{access_token}} = response.tokens.access
```

#### 3. Get Me
```
GET http://localhost:8000/api/auth/me
Headers: Authorization: Bearer {{access_token}}
```

#### 4. Get Reports
```
GET http://localhost:8001/api/reportes/mensual?empresa_id=UUID&año=2024&mes=1
Headers: Authorization: Bearer {{access_token}}
```

---

## 🐛 Solución de Problemas

### Error: "ModuleNotFoundError: No module named 'django'"
```bash
# Activar entorno virtual
source env/bin/activate  # Linux/Mac
env\Scripts\activate     # Windows

# Reinstalar dependencias
pip install -r requirements.txt
```

### Error: "Could not connect to database"
```bash
# Verificar PostgreSQL está corriendo
# Windows: PostgreSQL debe estar en servicios
# Linux: sudo systemctl start postgresql
# Mac: brew services start postgresql

# Verificar credenciales en .env
cat .env | grep DB_
```

### Error: "relation 'auth_usuario' does not exist"
```bash
# Ejecutar migraciones
python manage.py migrate
```

### Puerto en uso
```bash
# Linux/Mac: Encontrar proceso
lsof -i :8000

# Windows: Finder de puertos
netstat -ano | findstr :8000

# Usar otro puerto
python manage.py runserver 8002
```

---

## 📈 Próximos Pasos

1. **Configurar AWS/GCP**: Añadir credenciales para consumo real
2. **Agregar Tests**: Suite de pruebas unitarias
3. **Configurar Email**: Para notificaciones de anomalías
4. **Implementar CI/CD**: GitHub Actions o GitLab CI
5. **Crear Frontend**: Dashboard web con React
6. **Load Testing**: Probar con 12,000 usuarios
7. **Monitoring**: NewRelic, Datadog o similar

---

## 📞 Support

Para problemas o preguntas:
1. Revisar `README.md` para documentación completa
2. Revisar `API_ENDPOINTS.md` para ejemplos de API
3. Revisar `RESUMEN_EJECUTIVO.md` para arquitectura
4. Contactar al equipo de BITE.CO

---

**¡Felicidades! Tu plataforma FinOps está lista para usar.** 🎉

Accede a los paneles administrativos para comenzar a gestionar usuarios y recursos cloud.
