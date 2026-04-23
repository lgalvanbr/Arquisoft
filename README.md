# FinOps Platform · BITE.CO

Plataforma de gestión y optimización de costos cloud (AWS/GCP) con Load Balancer, autenticación JWT y frontend web.

---

## Arquitectura en AWS

```
Internet → ALB puerto 80 → EC2 app-a / app-b puerto 8080 → EC2 DB PostgreSQL
```

| Recurso | Tipo | Detalle |
|---|---|---|
| `report-db` | EC2 t3.micro | PostgreSQL 16 · `monitoring_db` |
| `report-app-lb-a` | EC2 t2.nano | Django + Gunicorn |
| `report-app-lb-b` | EC2 t2.nano | Django + Gunicorn |
| `report-alb` | Application LB | Round-robin · health `/api/reportes/health` |

---

## Prerrequisitos

- Cuenta de AWS con permisos EC2, ELB, VPC
- AWS CLI configurado (`aws configure`)
- Terraform instalado — [descargar](https://developer.hashicorp.com/terraform/downloads)
- Git
- JMeter (solo para pruebas de carga)

---

## Despliegue paso a paso

### 1. Clonar el repositorio

```bash
git clone https://github.com/lgalvanbr/Arquisoft.git
cd Arquisoft/terraform
```

### 2. Inicializar Terraform

```bash
terraform init
```

### 3. Revisar qué va a crear (opcional)

```bash
terraform plan
```

### 4. Desplegar la infraestructura

```bash
terraform apply
```

Escribe `yes` cuando lo pida. Tarda ~3 minutos en crear todos los recursos.

Al finalizar verás los outputs:

```
access_url           = "http://report-alb-XXXXXXXXX.us-east-1.elb.amazonaws.com"
alb_dns_name         = "report-alb-XXXXXXXXX.us-east-1.elb.amazonaws.com"
database_public_ip   = "X.X.X.X"
app_instances_public_ips = { "a" = "X.X.X.X", "b" = "X.X.X.X" }
```

### 5. Esperar que las instancias arranquen

Las instancias app tardan ~5 minutos en:
1. Instalar dependencias (pip, Django, Gunicorn)
2. Correr migraciones (solo app-a, espera a que DB esté lista)
3. Arrancar Gunicorn en puerto 8080 automáticamente

### 6. Verificar que funciona

```bash
# Reemplaza con tu ALB DNS del output de Terraform
ALB=report-alb-XXXXXXXXX.us-east-1.elb.amazonaws.com

curl http://$ALB/api/reportes/health
# Esperado: {"status": "healthy", "service": "reportes"}

curl http://$ALB/api/auth/health
# Esperado: {"status": "healthy"}
```

Si el health check falla, espera 2 minutos más y reintenta.

### 7. Abrir el frontend

Abre en tu navegador:

```
http://<alb_dns_name>
```

Desde ahí puedes registrar usuarios, hacer login y explorar todos los endpoints de la API.

---

## Reiniciar Gunicorn manualmente (si es necesario)

Si una instancia reinicia o Gunicorn se cae, conéctate vía EC2 Instance Connect:

1. AWS Console → EC2 → selecciona la instancia → **Connect** → **EC2 Instance Connect**
2. Corre:

```bash
sudo fuser -k 8080/tcp 2>/dev/null || true
cd /apps/Arquisoft
source /etc/environment
sudo /usr/local/bin/gunicorn finops_platform.wsgi:application \
  --bind 0.0.0.0:8080 \
  --workers 4 \
  --daemon \
  --log-file /var/log/gunicorn.log
curl http://localhost:8080/api/reportes/health
```

---

## Pruebas de carga con JMeter

### Configurar el DNS del ALB en el .jmx

```bash
# En tu máquina local — reemplaza con tu ALB DNS real
ALB=report-alb-XXXXXXXXX.us-east-1.elb.amazonaws.com

sed -i "s|report-alb-[0-9]*.us-east-1.elb.amazonaws.com|$ALB|g" jmeter/load-test-asr.jmx
```

En Windows PowerShell:
```powershell
$ALB = "report-alb-XXXXXXXXX.us-east-1.elb.amazonaws.com"
(Get-Content jmeter\load-test-asr.jmx) -replace 'report-alb-\d+\.us-east-1\.elb\.amazonaws\.com', $ALB | Set-Content jmeter\load-test-asr.jmx
```

### Ejecutar el test

```bash
# Headless (recomendado)
mkdir -p jmeter/results
jmeter -n -t jmeter/load-test-asr.jmx -l jmeter/results/results.jtl -j jmeter/results/test.log

# Ver resultados
tail -f jmeter/results/test.log
```

O abre el `.jmx` directamente en JMeter GUI para verlo en tiempo real.

### Plan del test

| Fase | Usuarios | Ramp-up | Duración |
|---|---|---|---|
| Phase 1 | 5,000 | 5 min | 10 min |
| Phase 2 | +7,000 (total 12,000) | 10 min | 10 min |

Endpoint bajo prueba: `GET /api/reportes/consumo`

### ASR objetivo

| Métrica | Objetivo |
|---|---|
| Disponibilidad | ≥ 95% |
| Tasa de error | < 5% |
| Throughput | ~100-200 req/seg |

---

## Destruir la infraestructura

```bash
cd terraform
terraform destroy
```

Escribe `yes`. Esto elimina **todas** las instancias EC2, el ALB y los security groups. No genera costos después de esto.

---

## Volver a desplegar desde cero

```bash
cd terraform
terraform apply
```

Eso es todo. Terraform crea todo de nuevo y las instancias se autoconfiguraн automáticamente.

---

## Endpoints de la API

### Autenticación

```bash
BASE=http://<alb_dns_name>

# Registrar usuario
curl -X POST $BASE/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","email":"admin@bite.co","password":"Admin1234!"}'

# Login
curl -X POST $BASE/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin1234!"}'

# Con el token del login:
TOKEN=<access_token_del_login>

# Info del usuario
curl $BASE/api/auth/me -H "Authorization: Bearer $TOKEN"

# Historial de accesos
curl $BASE/api/auth/audit/historial -H "Authorization: Bearer $TOKEN"
```

### Reportes

```bash
curl $BASE/api/reportes/mensual     -H "Authorization: Bearer $TOKEN"
curl $BASE/api/reportes/consumo     -H "Authorization: Bearer $TOKEN"
curl $BASE/api/reportes/gastos      -H "Authorization: Bearer $TOKEN"
curl $BASE/api/reportes/proyecto    -H "Authorization: Bearer $TOKEN"
curl $BASE/api/reportes/analisis    -H "Authorization: Bearer $TOKEN"
curl $BASE/api/reportes/tendencias  -H "Authorization: Bearer $TOKEN"
curl $BASE/api/reportes/historial   -H "Authorization: Bearer $TOKEN"
```

---

## Stack tecnológico

- **Backend**: Django 4.2 + Django REST Framework
- **Auth**: JWT (djangorestframework-simplejwt)
- **DB**: PostgreSQL 16
- **Servidor**: Gunicorn 21 (4 workers)
- **Infra**: AWS EC2 + Application Load Balancer
- **IaC**: Terraform ~5.x
- **Load testing**: Apache JMeter 5.6+


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

## 🧪 Testing ASR (Application Service Requirements)

### Load Testing with JMeter

Located in `/jmeter/` directory:

```bash
jmeter/
├── load-test-asr.jmx              # Main JMeter test plan
├── README.md                        # Full documentation
├── QUICKSTART.md                    # Quick reference guide
├── IMPLEMENTATION_SUMMARY.md        # Detailed implementation details
└── run-load-test.sh                 # Automated execution script
```

#### Quick Start

1. **Get ALB DNS** (after Terraform deployment):
   ```bash
   cd terraform/
   terraform output alb_dns_name
   ```

2. **Run the test**:
   ```bash
   # Option 1: GUI (interactive)
   jmeter -t jmeter/load-test-asr.jmx
   
   # Option 2: Headless (automatic)
   bash jmeter/run-load-test.sh ./results <alb-dns-name>
   ```

#### Test Configuration

- **Load Profile**: 5,000 → 12,000 concurrent users over 10 minutes
- **Endpoints Tested**:
  - `POST /api/auth/login` (JWT authentication)
  - `GET /api/reportes/proyecto` (with Bearer token)
  - `GET /api/reportes/consumo` (with Bearer token)
- **User**: `report_user` / `isis2503`
- **Authentication**: JWT Bearer tokens extracted from login response
- **Request Pattern**: Alternating between proyecto and consumo endpoints

#### ASR Success Criteria

✅ **Availability**: ≥95% (error rate < 5%)
✅ **Latency**: 2-5 seconds average (p50)
✅ **Consistency**: 95th percentile < 7 seconds
✅ **Throughput**: 100+ requests/sec at peak load

#### Results and Analysis

After test completion:
- **HTML Report**: `results_html/index.html` (charts and metrics)
- **Aggregate Report**: Percentile breakdown (p50, p90, p95, p99)
- **Error Analysis**: HTTP status codes and timeouts
- **Performance Trends**: Latency over time during ramp-up

See `jmeter/README.md` for detailed metrics interpretation and troubleshooting.

---

## 🏗️ Infrastructure as Code (Terraform)

AWS deployment files in `/terraform/`:

```bash
terraform/
├── deployment.tf                    # Complete AWS infrastructure
├── install_terraform.sh             # Terraform installation script
└── README.md                        # Deployment documentation
```

#### Infrastructure Components

- **Application Load Balancer** (report-alb)
  - Port 80 (HTTP)
  - Target Group with Round-Robin balancing
  - Health check: `/api/reportes/health` (30s intervals)

- **EC2 Instances** (report-app-lb-a, report-app-lb-b)
  - Instance type: t2.micro
  - Runs Django application on port 8080
  - PostgreSQL support via environment variables

- **RDS Database** (report-db)
  - Engine: PostgreSQL
  - Credentials: `report_user` / `isis2503`
  - Database name: `monitoring_db`

#### Django Configuration

`finops_platform/settings.py` configured for PostgreSQL with environment variables:
- `DATABASE_HOST`: RDS endpoint
- `DB_NAME`: Database name
- `DB_USER`: Database user
- `DB_PASSWORD`: Database password
- `DB_PORT`: PostgreSQL port (5432)

See `terraform/README.md` for deployment instructions.

---

## 📚 Documentación Adicional

- **Seguridad**: Todos los endpoints (excepto health check y registro) requieren token JWT
- **CORS**: Configurado para localhost:3000, 8000, 8001
- **Logging**: Se registran todos los eventos en logs/
- **Errores**: Respuestas HTTP estándar con mensajes descriptivos
- **JMeter Testing**: Completa validación del ASR (ver `jmeter/` directorio)
- **Terraform Deployment**: Infrastructure as Code en AWS (ver `terraform/` directorio)

---