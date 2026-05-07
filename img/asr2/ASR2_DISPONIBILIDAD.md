# ASR 2 - Disponibilidad 99.5% Anual

## Enunciado

> Yo como usuario, dado que la plataforma es utilizada para la toma de decisiones financieras criticas, cuando accedo al sistema en cualquier momento, quiero que la plataforma este disponible sin interrupciones. Esto debe suceder garantizando una disponibilidad minima del **99.5% anual** sin caidas del servicio.

---

## Calculo de presupuesto de caidas

| Periodo | Tiempo total | Caida maxima permitida (0.5%) |
|---|---|---|
| Año (365 dias) | 525,600 min | **2,628 minutos (~43.8 horas)** |
| Mes (30 dias) | 43,200 min | ~216 minutos (~3.6 horas) |
| Semana | 10,080 min | ~50 minutos |
| Dia | 1,440 min | ~7 minutos |

Cualquier fallo no mitigado que acumule mas de 43.8 horas de indisponibilidad en un año rompe el ASR.

---

## Estilo de arquitectura aplicado

**Redundancia Activa con Balanceo de Carga + Auto-recuperacion (Active Redundancy + Load Balancing + Self-Healing)**

El sistema sigue el patron de multiples replicas activas detras de un balanceador, gestionadas por un **Auto Scaling Group (ASG)**. Todas las instancias procesan trafico simultaneamente. Si una falla el health check del ALB, el ASG la termina y lanza una nueva automaticamente sin intervencion humana.

```
Usuario
   |
   v
ALB (Application Load Balancer)
   |         |         |
   v         v         v
instancia-1  instancia-2  instancia-N (nueva si hay fallo)
[AZ-1a]      [AZ-1b]      [ASG lanza automaticamente]
   |
   v
RDS PostgreSQL Multi-AZ
   |                        |
Primaria (AZ us-east-1a)   Standby (AZ us-east-1b) <- failover ~60s
```

Auto Scaling Group: min=2, max=4. Auto-reemplazo via Launch Template.

Este estilo garantiza que **ningun componente sea un Single Point of Failure (SPOF)** y que las instancias caidas se reemplacen automaticamente.

---

## Tacticas de disponibilidad aplicadas

Las tacticas de disponibilidad se clasifican en tres categorias: **detectar**, **recuperar** y **prevenir** fallos.

---

### 1. Detectar fallos

#### 1.1 Health Monitoring

El ALB ejecuta health checks activos sobre cada instancia cada **10 segundos**:

- `GET /api/reportes/health` espera HTTP 200
- Si 2 checks consecutivos fallan (20s), la instancia se marca como *unhealthy* y se excluye del pool
- Cuando se recupera (2 checks exitosos), vuelve al pool automaticamente

**Tactica**: *Ping/Echo* - el orquestador sondea periodicamente a los componentes para verificar su estado.

#### 1.2 Sanity Checking

`systemd` monitorea el proceso Gunicorn localmente:

- Si el proceso muere, lo reinicia en 5 segundos (`RestartSec=5`)
- Combinado con el health check del ALB, la deteccion opera en dos niveles: proceso y red

---

### 2. Recuperar de fallos

#### 2.1 Redundancia Activa (Hot Spare)

Minimo 2 instancias de aplicacion sirven trafico simultaneamente, gestionadas por el ASG. La perdida de una instancia no interrumpe el servicio; el ALB absorbe toda la carga con las instancias restantes y el ASG lanza una nueva para restaurar la capacidad.

- **Beneficio**: recuperacion instantanea (0s de downtime perceptible para el usuario)
- **Trade-off**: costo de mantener instancias redundantes activas (minimo 2)

#### 2.2 Auto-reemplazo de instancias (Self-Healing via ASG)

El Auto Scaling Group con `health_check_type = "ELB"` detecta instancias que fallan el health check del ALB y las **termina y reemplaza automaticamente** usando el Launch Template. El tiempo de reemplazo es ~5 min (tiempo de arranque de la nueva instancia).

- El ASG mantiene siempre `desired_capacity = 2` (minimo)
- No requiere intervencion humana para recuperar instancias caidas
- El Launch Template garantiza configuracion identica en cada instancia nueva

**Tactica**: *Spare* con auto-provisioning - el sistema se autorrepara reemplazando instancias defectuosas.

#### 2.3 Separacion por Zonas de Disponibilidad (Fault Isolation)

El ASG distribuye instancias en todas las AZs disponibles. Una falla de infraestructura fisica de AWS en una AZ no afecta instancias en otras AZs.

**Tactica**: *Fault Isolation* - los componentes redundantes estan en dominios de fallo independientes.

#### 2.4 RDS Multi-AZ

La base de datos tiene una replica standby sincronica en otra AZ. AWS gestiona el failover automatico:

- Replica datos sincronamente al standby
- Ante fallo de la primaria: failover automatico en ~60 segundos
- La app no requiere cambios: el endpoint DNS de RDS redirige automaticamente

**Tactica**: *Spare* con *Rollover* automatico - componente de respaldo listo para asumir en caso de fallo.

#### 2.5 Auto-reinicio del proceso (Restart)

`systemd` con `Restart=always` y `RestartSec=5` garantiza que si Gunicorn falla, el servicio se recupera en maximo 5 segundos sin intervencion humana.

**Tactica**: *Retry / Restart* - reintentar la operacion fallida automaticamente.

---

### 3. Prevenir fallos

#### 3.1 Separacion de Responsabilidades

La base de datos esta en una capa separada (RDS gestionado por AWS) en lugar de una EC2 auto-administrada. AWS se encarga de:

- Parches de seguridad del motor PostgreSQL
- Backups automaticos
- Monitoreo de hardware

**Tactica**: *Removal from Service* delegado - eliminar la gestion operacional reduce la probabilidad de error humano.

#### 3.2 Balanceo de Carga Round-Robin

La distribucion equitativa de carga entre instancias evita que una instancia se sature mientras otra esta ociosa, reduciendo la probabilidad de fallos por sobrecarga.

**Tactica**: *Load Balancing* - distribucion de carga para evitar puntos calientes.

---

## Analisis de disponibilidad por escenario

| Escenario de fallo | Sin mejoras | Con mejoras |
|---|---|---|
| Gunicorn se cae en una instancia | ~5s downtime si ALB no redirige a tiempo | 0s - ALB redirige, systemd reinicia en 5s |
| Instancia app muere completamente | Capacidad reducida, sin reemplazo | ASG lanza nueva instancia automaticamente (~5 min) |
| AZ completa de AWS falla | Instancias en esa AZ inaccesibles | ASG lanza instancias en otras AZs automaticamente |
| BD cae | Toda la plataforma cae (~horas para recuperar) | RDS failover en ~60s |
| Pico de trafico | Una instancia se satura | Round-robin distribuye carga; ASG puede escalar hasta 4 |

---

## Tiempo de indisponibilidad estimado

| Evento | Duracion aproximada |
|---|---|
| Caida de instancia app (detectada por health check ALB) | 20s (2 x 10s interval) |
| Reinicio de Gunicorn por systemd | 5s |
| Reemplazo de instancia por ASG (launch + boot) | ~5 min (paralelo, sin afectar disponibilidad) |
| Failover de RDS Multi-AZ | ~60s |
| Falla total de AZ (ASG relanza en otra AZ) | ~5 min (instancias nuevas en AZ sana) |

El peor caso para el usuario es el failover RDS (~60s). El reemplazo por ASG ocurre en paralelo sin interrumpir el servicio (las instancias sanas siguen activas).

**Disponibilidad estimada: >99.9%**, cumpliendo holgadamente el ASR de 99.5% anual.

---

## Componentes Terraform implementados

| Recurso Terraform | Tactica de disponibilidad |
|---|---|
| `aws_lb` (ALB) | Balanceo de carga, health monitoring |
| `aws_lb_target_group` con `interval=10` | Health monitoring activo (Ping/Echo) |
| `aws_launch_template` | Configuracion reproducible para nuevas instancias |
| `aws_autoscaling_group` (min=2, max=4, health_check_type=ELB) | Self-healing: auto-reemplazo de instancias caidas, fault isolation por AZ |
| `aws_autoscaling_attachment` | Registra automaticamente nuevas instancias en el ALB |
| `aws_db_instance` con `multi_az=true` | Spare + rollover automatico |
| `aws_db_subnet_group` | Prerequisito para Multi-AZ |
| systemd con `Restart=always` | Restart automatico del proceso |

---

## Limitaciones y mejoras futuras

| Limitacion actual | Mejora recomendada |
|---|---|
| HTTP sin cifrado (puerto 80) | HTTPS con certificado ACM + ALB HTTPS listener |
| Una sola region AWS | Multi-region con Route 53 failover para disponibilidad >99.99% |
| Sin escalado automatico por metrica | ASG Scaling Policies (CPU > 70% añadir instancia) |
| Credenciales de BD en texto plano en Terraform | AWS Secrets Manager para gestion segura de credenciales |


---

## Estilo de arquitectura aplicado

### Redundancia Activa con Balanceo de Carga + Auto-recuperación (Active Redundancy + Load Balancing + Self-Healing)

El sistema sigue el patrón de **múltiples réplicas activas** detrás de un balanceador, gestionadas por un **Auto Scaling Group (ASG)**. Todas las instancias procesan tráfico simultáneamente. Si una falla el health check del ALB, el ASG la termina y lanza una nueva automáticamente sin intervención humana.

```
Usuario → ALB (Application Load Balancer)
               ├── instancia-1 (AZ us-east-1a)  ┐
               ├── instancia-2 (AZ us-east-1b)  ├── Auto Scaling Group (min=2, max=4)
               └── instancia-N (nueva si hay fallo) ┘  ← auto-reemplazo vía Launch Template
                        ↓
               RDS PostgreSQL Multi-AZ
               ├── Primaria (AZ us-east-1a)
               └── Standby sincrónico (AZ us-east-1b)  ← failover automático ~60s
```

Este estilo garantiza que **ningún componente sea un Single Point of Failure (SPOF)** y que las instancias caídas se reemplacen automáticamente.

---

## Tácticas de disponibilidad aplicadas

Las tácticas de disponibilidad se clasifican en tres categorías: **detectar**, **recuperar** y **prevenir** fallos.

---

### 1. Detectar fallos

#### 1.1 Health Monitoring (Monitor de salud)
El ALB ejecuta health checks activos sobre cada instancia cada **10 segundos**:
- `GET /api/reportes/health` → espera HTTP 200
- Si 2 checks consecutivos fallan (20s), la instancia se marca *unhealthy* y se excluye del pool
- Cuando se recupera (2 checks exitosos), vuelve al pool automáticamente

**Táctica**: *Ping/Echo* — el orquestador sondea periódicamente a los componentes para verificar su estado.

#### 1.2 Sanity Checking
`systemd` monitorea el proceso Gunicorn localmente:
- Si el proceso muere, lo reinicia en 5 segundos (`RestartSec=5`)
- Combinado con el health check del ALB, la detección es en dos niveles: proceso y red

---

### 2. Recuperar de fallos

#### 2.1 Redundancia Activa (Hot Spare)
Mínimo 2 instancias de aplicación sirven tráfico simultáneamente, gestionadas por el ASG. La pérdida de una instancia no interrumpe el servicio; el ALB absorbe toda la carga con las instancias restantes y el ASG lanza una nueva para restaurar la capacidad.

- **Beneficio**: recuperación instantánea (0s de downtime perceptible para el usuario)
- **Trade-off**: costo de mantener instancias redundantes activas (mínimo 2)

#### 2.2 Auto-reemplazo de instancias (Self-Healing via ASG)
El Auto Scaling Group (`health_check_type = "ELB"`) detecta instancias que fallan el health check del ALB y las **termina y reemplaza automáticamente** usando el Launch Template. El tiempo de reemplazo es ~5 min (tiempo de arranque de la nueva instancia).

- El ASG mantiene siempre `desired_capacity = 2` (mínimo)
- No requiere intervención humana para recuperar instancias caídas
- El Launch Template garantiza configuración idéntica en cada instancia nueva

**Táctica**: *Spare* con auto-provisioning — el sistema se autorrepara reemplazando instancias defectuosas.

#### 2.3 Separación por Zonas de Disponibilidad (Fault Isolation)
El ASG distribuye instancias en todas las AZs disponibles (`vpc_zone_identifier = data.aws_subnets.default.ids`). Una falla de infraestructura física de AWS en una AZ no afecta instancias en otras AZs.

**Táctica**: *Fault Isolation* — los componentes redundantes están en dominios de fallo independientes.

#### 2.4 RDS Multi-AZ (Standby sincrónico para la DB)
La base de datos tiene una réplica standby sincrónica en otra AZ. AWS gestiona el failover automático:
- Replica datos síncronamente al standby
- Ante fallo de la primaria: failover automático en ~60 segundos
- La app no requiere cambios: el endpoint DNS de RDS redirige automáticamente

**Táctica**: *Spare* con *Rollover* automático — componente de respaldo listo para asumir en caso de fallo.

#### 2.5 Auto-reinicio del proceso (Restart)
`systemd` con `Restart=always` y `RestartSec=5` garantiza que si Gunicorn falla, el servicio se recupera en máximo 5 segundos sin intervención humana.

**Táctica**: *Retry / Restart* — reintentar la operación fallida automáticamente.

---

### 3. Prevenir fallos

#### 3.1 Separación de Responsabilidades
La base de datos está en una capa separada (RDS gestionado por AWS) en lugar de una EC2 auto-administrada. AWS se encarga de:
- Parches de seguridad del motor PostgreSQL
- Backups automáticos
- Monitoreo de hardware

**Táctica**: *Removal from Service* delegado — eliminar la gestión operacional reduce la probabilidad de error humano.

#### 3.2 Balanceo de Carga Round-Robin
La distribución equitativa de carga entre instancias evita que una instancia se sature mientras otra está ociosa, reduciendo la probabilidad de fallos por sobrecarga.

**Táctica**: *Load Balancing* — distribución de carga para evitar puntos calientes.

---

## Análisis de disponibilidad por escenario

| Escenario de fallo | Sin mejoras | Con mejoras |
|--------------------|------------|-------------|
| Gunicorn se cae en una instancia | ~5s downtime si ALB no redirige a tiempo | 0s — ALB redirige, systemd reinicia en 5s |
| Instancia app muere completamente | Capacidad reducida, sin reemplazo | ✅ ASG lanza nueva instancia automáticamente (~5 min) |
| AZ completa de AWS falla | ❌ instancias en esa AZ inaccesibles | ✅ ASG lanza instancias en otras AZs automáticamente |
| EC2 de BD cae | ❌ toda la plataforma cae (~horas para recuperar) | ✅ RDS failover en ~60s |
| Pico de tráfico | Una instancia se satura | Round-robin distribuye carga; ASG puede escalar hasta 4 |

---

## Tiempo de indisponibilidad estimado con la arquitectura implementada

| Evento | Duración aproximada |
|--------|-------------------|
| Caída de instancia app (detectada por health check ALB) | 20s (2 × 10s interval) |
| Reinicio de Gunicorn por systemd | 5s |
| Reemplazo de instancia por ASG (launch + boot) | ~5 min (paralelo, sin afectar disponibilidad) |
| Failover de RDS Multi-AZ | ~60s |
| Falla total de AZ (ASG relanza en otra AZ) | ~5 min (instancias nuevas en AZ sana) |

El peor caso para el usuario es el failover RDS (~60s). El reemplazo por ASG ocurre en paralelo sin interrumpir el servicio (las instancias sanas siguen activas). **Disponibilidad estimada: >99.9%**, cumpliendo holgadamente el ASR de 99.5% anual.

---

## Componentes Terraform implementados

| Recurso | Táctica |
|---------|---------|
| `aws_lb` (ALB) | Balanceo de carga, health monitoring |
| `aws_lb_target_group` con `interval=10` | Health monitoring activo (Ping/Echo) |
| `aws_launch_template` | Configuración reproducible para nuevas instancias |
| `aws_autoscaling_group` (`min=2, max=4, health_check_type=ELB`) | Self-healing: auto-reemplazo de instancias caídas, fault isolation por AZ |
| `aws_autoscaling_attachment` | Registra automáticamente nuevas instancias en el ALB |
| `aws_db_instance` con `multi_az=true` | Spare + rollover automático |
| `aws_db_subnet_group` | Prerequisito para Multi-AZ |
| `systemd Restart=always` | Restart automático del proceso |

---

## Limitaciones y mejoras futuras

| Limitación actual | Mejora recomendada |
|------------------|--------------------|
| HTTP sin cifrado (puerto 80) | HTTPS con certificado ACM + ALB HTTPS listener |
| Una sola región AWS | Multi-región con Route 53 failover para >99.99% |
| Sin escalado automático por métrica | ASG Scaling Policies (CPU > 70% → añadir instancia) |
| Backups manuales del código | RDS Automated Backups ya incluido en Multi-AZ |
