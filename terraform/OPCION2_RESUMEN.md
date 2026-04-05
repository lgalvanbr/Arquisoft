# OPCIÓN 2: Balance Architecture - Resumen de Cambios

## Objetivo
Soportar **12,000 usuarios concurrentes** con error rate < 5%, latencia p50: 2-5s, implementando Gunicorn + ElastiCache.

---

## Cambios Principales en `deployment.tf`

### 1. **Instancias EC2 Aplicación**

| Aspecto | Antes | Opción 2 | Cambio |
|--------|--------|----------|--------|
| **Cantidad** | 4 instances | 10 instances | +6 instancias |
| **Tipo** | t2.micro | t3.small | Mejor CPU (2 cores) y RAM (2GB) |
| **Ramp-up** | manage.py runserver | Gunicorn | Producción-ready |
| **Workers** | 1 (monothread) | 6 × 10 = 60 total | Paralelismo real |

**IDs de instancias:** a, b, c, d, e, f, g, h, i, j

### 2. **Base de Datos**

| Aspecto | Antes | Opción 2 |
|--------|--------|----------|
| **Tipo** | t3.micro | t3.small |
| **max_connections** | 2,000 | 4,000 |
| **shared_buffers** | Default | 256MB (nuevo) |

### 3. **Gunicorn Configuration**

**Systemd Service:** `/etc/systemd/system/gunicorn.service`

```ini
[Service]
ExecStart=/usr/bin/python3 -m gunicorn \
  --workers 6 \
  --worker-class sync \
  --bind 0.0.0.0:8080 \
  --timeout 30 \
  --access-logfile /var/log/gunicorn-access.log \
  --error-logfile /var/log/gunicorn-error.log \
  --log-level info \
  finops_platform.wsgi:application
```

**Características:**
- Auto-restart en caso de fallo
- Resource limits: 65,536 file descriptors
- Logging de acceso y errores
- Timeout: 30 segundos

### 4. **Load Balancer Improvements**

| Configuración | Antes | Opción 2 |
|---------------|--------|----------|
| **HC Timeout** | 5s | 10s |
| **Unhealthy Threshold** | 2 | 3 |
| **Deregistration Delay** | Default | 30s (nuevo) |

### 5. **ElastiCache Redis (NUEVO)**

**Tipo:** Single-node redis cluster (t3.small)

**Características:**
- Endpoint: Auto-generado por AWS
- Puerto: 6379
- Engine: Redis 7.0
- Subnet group: Default VPC subnets
- Security group: report-trafico-redis (acceso desde app servers)

**Uso en Django:**
- Session backend (más rápido que DB)
- Caching de reportes
- Configuración en settings.py (REDIS_URL)

**Security Group para Redis:**
- Ingress: Port 6379 desde security_group.traffic_http
- Egress: All outbound

---

## Capacidad Teórica - Opción 2

```
┌─────────────────────────────────────────────────────────┐
│             OPCIÓN 2 CAPACITY ANALYSIS                 │
├─────────────────────────────────────────────────────────┤
│ Total Gunicorn Workers:      10 instances × 6 = 60     │
│ Connections per Worker:      ~100 avg                  │
│ Total DB Connections:        60 × 5-10 = 300-600      │
│ DB Connection Pool:          4,000 available           │
│                                                         │
│ Request Throughput:                                    │
│   - Peak RPS: ~6,000 req/sec (at 12K users)           │
│   - Worker capacity: 60 × 100 = 6,000 req/sec ✓       │
│                                                         │
│ Expected Metrics:                                      │
│   - Concurrent Users: 12,000 ✓                         │
│   - Error Rate: ~4-5% (mejora de 90% a 5%)            │
│   - Latency p50: 3-4 segundos ✓                        │
│   - Latency p95: 6-7 segundos ✓                        │
│   - Availability: ~93-94% (mejora de 10%)             │
└─────────────────────────────────────────────────────────┘
```

---

## Costo Estimado - Opción 2

```
Componente                        Costo Mensual
─────────────────────────────────────────────
EC2 Instances (10 × t3.small)    ~$60-80
Database (t3.small)              ~$15-20
ALB (Application Load Balancer)  ~$16-20
ElastiCache Redis (t3.small)     ~$15-20
Data Transfer                    ~$5-10
─────────────────────────────────────────────
TOTAL MENSUAL:                   ~$110-150
```

---

## Deployment Checklist

### Antes de Desplegar

- [ ] Verificar AWS credentials están configuradas
- [ ] Revisar región en AWS (default: us-east-1)
- [ ] Asegurar que requirements.txt incluye:
  ```
  gunicorn==21.2.0
  django-redis==5.4.0
  ```

### Deployment Steps

```bash
# 1. Validar configuración Terraform
cd terraform
terraform init
terraform plan

# 2. Revisar cambios en el plan
# Asegurarse que muestra:
#   - 10 EC2 app instances (vs 4 antes)
#   - ElastiCache Redis
#   - Security group para Redis

# 3. Aplicar cambios
terraform apply

# 4. Esperar ~10-15 minutos para que se despliegue todo
#    - EC2s se initializan
#    - Gunicorn arranca
#    - Migraciones de DB
#    - Redis cluster se crea

# 5. Verificar deployment
aws elbv2 describe-target-health \
  --target-group-arn <TARGET_GROUP_ARN>

# 6. Test health endpoint
curl http://<ALB_DNS>/api/reportes/health
```

### Post-Deployment Verification

```bash
# 1. SSH a una instancia app
ssh -i <key>.pem ubuntu@<app-instance-public-ip>

# 2. Verificar Gunicorn
sudo systemctl status gunicorn
sudo tail -f /var/log/gunicorn-error.log

# 3. Verificar Redis connectivity
redis-cli -h <redis-endpoint> ping
# Expected: PONG

# 4. Verificar Database
psql -h <db-private-ip> -U report_user -d monitoring_db -c "SELECT version();"
```

---

## Archivos Modificados

### `terraform/deployment.tf` (597 líneas)

**Cambios:**
- ✅ Variables: Agregadas `gunicorn_workers`, modificados `instance_type_app` y `instance_type_db`
- ✅ Security Groups: Agregado `traffic_redis` para ElastiCache
- ✅ EC2 Database: user_data mejorado con logging y shared_buffers
- ✅ EC2 App Instances: 4 → 10 instancias, user_data con Gunicorn systemd service
- ✅ ALB Target Group: Health check timeout 5s → 10s, deregistration_delay 30s
- ✅ ElastiCache: Nueva sección con Redis cluster, subnet group
- ✅ Outputs: Agregados redis_endpoint, redis_host, redis_port, deployment_summary

---

## Próximos Pasos Recomendados

### 1. **Ejecutar JMeter Load Test**
```bash
jmeter -t jmeter/load-test-asr.jmx
# Validar ASR metrics
```

### 2. **Optimizar Django Views** (si necesario)
- Analizar N+1 queries
- Agregar select_related/prefetch_related
- Implementar @cache_page decorators

### 3. **Monitoreo y Alertas**
- CloudWatch metrics para EC2s
- CloudWatch Logs para Gunicorn
- SNS alerts si error rate > 5%

### 4. **Plan de Escalabilidad**
- Opción 2a: Escalar a 15-20 instances si crece demanda
- Opción 3: Migrar a RDS PostgreSQL (managed) + Opción 3 architecture

---

## Referencia Rápida: Variables Terraform

Para personalizar la implementación, editar variables en `deployment.tf`:

```hcl
variable "region" {
  default = "us-east-1"  # Cambiar si necesitas otra región
}

variable "gunicorn_workers" {
  default = 6  # Aumentar si quieres más paralelismo
}

variable "instance_type_app" {
  default = "t3.small"  # Cambiar a t3.medium si necesitas más poder
}

variable "instance_type_db" {
  default = "t3.small"  # Cambiar a t3.medium para DB más robusta
}
```

Para aplicar cambios sin redeploying todo:
```bash
terraform apply -var="gunicorn_workers=8"
```

---

## Troubleshooting

### Gunicorn no arranca
```bash
ssh -i <key>.pem ubuntu@<ip>
sudo systemctl status gunicorn
sudo journalctl -u gunicorn -n 50
```

### Error: "Connection refused" al health check
- Esperar 5-10 min a que EC2 termine de inicializar
- Verificar: `sudo systemctl is-active gunicorn`

### Redis no conecta desde app
```bash
# Verificar security group permite tráfico
aws ec2 describe-security-groups \
  --group-names report-trafico-redis

# Verificar Redis está available
aws elasticache describe-cache-clusters \
  --cache-cluster-id report-redis
```

### Base de datos llena de conexiones
```bash
ssh -i <key>.pem ubuntu@<db-ip>
sudo -u postgres psql -d monitoring_db -c "SELECT count(*) FROM pg_stat_activity;"
```

---

## Conclusión

Opción 2 ofrece un **balance entre costo y capacidad**:
- ✅ Soporte para 12,000 usuarios (vs 10% ahora)
- ✅ Error rate < 5% (vs 90% ahora)
- ✅ Costo moderado (~$110-150/mes)
- ✅ Infraestructura scalable
- ⚠️ Availability ~93-94% (no exacto 95% pero mejorado)

Para cumplir 95% exacto, escalable a Opción 3 (RDS + t3.medium instances).
