# Arquitectura de Microservicios BITE.CO - FinOps Platform

## 📋 Descripción General

Plataforma centralizada de gestión y optimización de costos cloud que permite visualizar, analizar y controlar consumos en AWS y GCP en tiempo real.

### ASR (Application Service Requirements)

- **Usuarios Concurrentes**: 5,000 sostenidos, picos hasta 12,000 (máx 10 minutos)
- **Disponibilidad**: 95% mínimo
- **Reportes Mensuales**: < 100 ms
- **Análisis Complejos**: > 2 segundos → ejecutar en background
- **Detección de Anomalías**: < 2 segundos

---

## 🏗️ Componentes de la Arquitectura

### 1. Servicio de Autenticación y Autorización (`autenticacion_autorizacion/`)

**Responsabilidades:**
- Registro y autenticación de usuarios
- Generación y validación de tokens JWT
- Gestión de permisos por rol (admin, usuario, gerente)
- Detección de anomalías en intentos de acceso

**Modelos Clave:**
- `Usuario`: Modelo personalizado con roles y estado
- `Token`: Almacenamiento de JWT (access/refresh)
- `AuditoriaAcceso`: Auditoría de intentos de login
- `IntentoBloqueado`: Bloqueo temporal por múltiples intentos fallidos
- `Permiso` y `RolPermiso`: Gestión de permisos granulares

**Endpoints:**

```bash
# Autenticación
POST   /api/auth/register          # Registrar nuevo usuario
POST   /api/auth/login             # Login y obtener tokens
GET    /api/auth/me                # Info del usuario autenticado
POST   /api/auth/refresh           # Refrescar token
POST   /api/auth/logout            # Logout

# Auditoría
GET    /api/auth/audit/historial   # Historial de accesos

# Health Check
GET    /api/health                 # Estado del servicio
```

**Detección de Anomalías:**
- Máx 5 intentos fallidos en ventana de 10 minutos
- Bloqueo temporal de 5 minutos después de exceder
- Detección en < 2 segundos
- Registra eventos en `AuditoriaAcceso`

---

### 2. Servicio de Reportes (`reportes/`)

**Responsabilidades:**
- Consolidación de consumo AWS y GCP
- Generación de reportes mensuales (< 100 ms)
- Análisis de optimización (background si > 2s)
- Detección de tendencias y anomalías

**Modelos Clave:**
- `ConsumoNube`: Registro de consumo por servicio/proyecto
- `ReporteMensual`: Reporte pre-calculado (optimización)
- `ResumenPorProyecto`: Consolidación por proyecto
- `AnálisisOptimización`: Oportunidades de ahorro
- `TendenciasAnomalias`: Detección de patrones anómalos
- `HistorialGeneracionReportes`: Auditoría de reportes

**Endpoints:**

```bash
# Reportes
GET    /api/reportes/mensual       # Reporte mensual (< 100 ms)
GET    /api/reportes/proyecto      # Reporte por proyecto
GET    /api/reportes/consumo       # Listar consumo con filtros
GET    /api/reportes/gastos        # Alias de consumo

# Análisis
GET    /api/reportes/analisis/optimizacion  # Análisis (background si > 2s)
GET    /api/reportes/tendencias    # Tendencias y anomalías

# Auditoría
GET    /api/reportes/historial     # Historial de generación

# Health Check
GET    /api/health                 # Estado del servicio
```

---

## 🗄️ Base de Datos

### Configuración

```python
# Ambos servicios usan PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': '<servicio>_db',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### Tablas Principales

#### Autenticación
- `usuarios` - Usuarios del sistema
- `tokens` - Tokens JWT activos
- `auditoria_acceso` - Log de accesos
- `intentos_bloqueados` - Bloqueos por anomalías
- `permisos` - Catálogo de permisos
- `rol_permisos` - Asignación rol-permiso

#### Reportes
- `consumo_nube` - Consumo AWS/GCP por servicio
- `reportes_mensuales` - Reportes pre-calculados
- `resumen_por_proyecto` - Consolidación por proyecto
- `analisis_optimizacion` - Oportunidades identificadas
- `tendencias_anomalias` - Patrones detectados
- `historial_generacion_reportes` - Auditoría

---

## 🔐 Autenticación y Autorización

### Flujo de Autenticación

1. **Registro**: Usuario proporciona credenciales
2. **Login**: Se valida contraseña, se generan tokens
3. **Detección de Anomalías**: Se verifica intentos fallidos
4. **Bloqueo Temporal**: Si > 5 intentos en 10 minutos
5. **Auditoría**: Se registra evento en `AuditoriaAcceso`

### Tokens JWT

```python
# Access Token (1 hora)
{
    'user_id': 'uuid',
    'username': 'usuario',
    'email': 'usuario@example.com',
    'rol': 'admin|usuario|gerente',
    'exp': timestamp,
    'iat': timestamp
}

# Refresh Token (1 día)
{
    'user_id': 'uuid',
    'exp': timestamp,
    'iat': timestamp,
    'type': 'refresh'
}
```

---

## 📊 Reportes y Análisis

### Reporte Mensual (ASR < 100 ms)

Pre-calculado en background para optimizar:
```json
{
    "costo_total": 45230.50,
    "costo_aws": 30150.75,
    "costo_gcp": 15079.75,
    "numero_recursos": 245,
    "numero_proyectos": 12,
    "anomalias_detectadas": 5,
    "ahorro_potencial": 8500.00,
    "detalles_por_servicio": {
        "EC2": "15000.00",
        "RDS": "8500.00",
        "S3": "3200.00"
    }
}
```

### Análisis de Optimización (Background si > 2 segundos)

Detecta oportunidades:
- **Instancias Inactivas**: 0% utilización por 30 días
- **Sobredimensionamiento**: Recursos con baja utilización
- **Datos sin Uso**: Almacenamiento retenido innecesariamente
- **Etiquetado Incompleto**: Recursos sin tags de gobernanza

### Tendencias y Anomalías

- **Spike de Costos**: Incremento > 20% vs mes anterior
- **Degradación Sostenida**: Aumento consistente
- **Patrones Anómalos**: Cambios inesperados en uso

---

## 🚀 Despliegue en AWS

### Estructura Recomendada

```
AWS
├── RDS PostgreSQL (Multi-AZ)
│   ├── autenticacion_db
│   └── reportes_db
├── ECS Fargate
│   ├── Service: autenticacion_autorizacion
│   │   └── Load Balancer: ALB (puerto 8000)
│   └── Service: reportes
│       └── Load Balancer: ALB (puerto 8001)
├── ElastiCache Redis (opcional, para caché)
├── CloudWatch (logs y métricas)
└── Route 53 (DNS)
```

### Variables de Entorno

```bash
# Autenticación
DEBUG=False
ALLOWED_HOSTS=*
SECRET_KEY=<random-secure-key>
DATABASE_URL=postgresql://user:pass@host:5432/autenticacion_db
JWT_SECRET_KEY=<random-secure-key>

# Reportes
DEBUG=False
ALLOWED_HOSTS=*
SECRET_KEY=<random-secure-key>
DATABASE_URL=postgresql://user:pass@host:5432/reportes_db

# AWS/GCP
AWS_ACCESS_KEY_ID=<key>
AWS_SECRET_ACCESS_KEY=<secret>
AWS_DEFAULT_REGION=us-east-1
GCP_PROJECT_ID=<project-id>
GCP_CREDENTIALS_JSON=<credentials>
```

---

## 📈 Monitoreo ASR

### Métricas Clave

```python
# Tiempo de respuesta
- Reporte Mensual: < 100 ms
- Análisis Complejo: > 2s → background

# Disponibilidad
- Target: 95%
- SLA Violación: < 5% downtime/mes

# Carga
- Usuarios Concurrentes: 5,000
- Picos: 12,000 (máx 10 min)
```

### Registros

Cada operación se registra en:
- `HistorialGeneracionReportes`: Tiempo de ejecución
- `AuditoriaAcceso`: Accesos al sistema
- CloudWatch Logs: Errores y eventos

---

## 🔧 Instalación y Configuración

### Requisitos

```bash
Python 3.9+
PostgreSQL 13+
Django 4.2
djangorestframework 3.14
djangorestframework-simplejwt 5.2
```

### Setup Local

```bash
# 1. Clonar repositorio
git clone <repo>
cd Arquisoft

# 2. Crear virtual env
python -m venv env
source env/Scripts/activate  # Windows
source env/bin/activate       # Linux/Mac

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con credenciales

# 5. Crear bases de datos (PostgreSQL)
createdb autenticacion_db
createdb reportes_db

# 6. Ejecutar migraciones
# Autenticación
cd autenticacion_autorizacion
python manage.py migrate
python manage.py createsuperuser

# Reportes
cd ../reportes
python manage.py migrate
python manage.py createsuperuser

# 7. Ejecutar servidores
# Terminal 1 - Autenticación (puerto 8000)
python autenticacion_autorizacion/manage.py runserver 8000

# Terminal 2 - Reportes (puerto 8001)
python reportes/manage.py runserver 8001
```

---

## 📚 Documentación Adicional

- **Seguridad**: Todos los endpoints (excepto health check y registro) requieren token JWT
- **CORS**: Configurado para localhost:3000, 8000, 8001
- **Logging**: Se registran todos los eventos en logs/
- **Errores**: Respuestas HTTP estándar con mensajes descriptivos

---

## 🎯 Próximas Fases

1. **Integración AWS/GCP**: Conectar APIs para consumo real
2. **Background Jobs**: Celery para análisis > 2s
3. **Cache Distribuido**: Redis para reportes frecuentes
4. **Notificaciones**: Email para alertas
5. **Frontend**: Dashboard web en React/Angular
6. **Mobile**: App nativa para iOS/Android

---

**Versión**: 1.0.0  
**Última Actualización**: 2024-01-XX  
**Equipo**: BITE.CO Arquitectura
