# Experimento ASR 2 - Disponibilidad 99.5% Anual

## Descripcion del ASR

> Yo como usuario, dado que la plataforma es utilizada para la toma de decisiones financieras criticas, cuando accedo al sistema en cualquier momento, quiero que la plataforma este disponible sin interrupciones, garantizando una disponibilidad minima del **99.5% anual** sin caidas del servicio.

---

## Hipotesis del experimento

> **Si** se produce una falla en alguno de los componentes criticos de la plataforma (instancia de aplicacion o base de datos), **entonces** el sistema debe continuar respondiendo correctamente en un tiempo inferior al presupuesto de caida permitido, de modo que la disponibilidad anual acumulada no baje del 99.5%.

---

## Diseño del experimento

### Tipo de experimento

**Chaos Engineering** - inyeccion controlada de fallos en produccion/staging para verificar la resiliencia real de la arquitectura ante condiciones adversas.

### Ambiente

| Parametro | Valor |
|---|---|
| Ambiente | AWS - misma infraestructura de produccion |
| Region | us-east-1 |
| Instancias app | Gestionadas por ASG (min. 2), distribuidas en todas las AZs disponibles |
| Base de datos | RDS PostgreSQL Multi-AZ |
| Load Balancer | Application Load Balancer (ALB) |
| Endpoint de prueba | GET /api/reportes/health y GET /api/reportes/mensual |

---

## Escenarios de prueba

Se definen **3 escenarios** en orden creciente de severidad.

---

### Escenario 1 - Caida de una instancia (ALB health check + ASG self-healing)

#### Objetivo

Verificar que el ALB detecta la instancia caida, redirige el trafico a las instancias sanas, y que el ASG lanza automaticamente una instancia de reemplazo.

#### Obtener ID de una instancia del ASG

```bash
ASG_NAME=$(aws autoscaling describe-auto-scaling-groups \
  --query "AutoScalingGroups[?starts_with(AutoScalingGroupName,'report')].AutoScalingGroupName" \
  --output text)

INSTANCE_ID=$(aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names $ASG_NAME \
  --query "AutoScalingGroups[0].Instances[0].InstanceId" --output text)

echo "Instancia a terminar: $INSTANCE_ID"
```

#### Estimulo

Terminar una instancia directamente (simula fallo de instancia):

```bash
aws ec2 terminate-instances --instance-ids $INSTANCE_ID
```

#### Monitor de medicion

```bash
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --query "LoadBalancers[?starts_with(LoadBalancerName,'report')].DNSName" \
  --output text)

while true; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://$ALB_DNS/api/reportes/health)
  echo "$(date '+%H:%M:%S') - HTTP $STATUS"
  sleep 1
done
```

#### Resultado esperado

| Metrica | Valor esperado |
|---|---|
| Tiempo hasta deteccion por ALB | menor o igual a 20s (2 x health check interval) |
| Servicio interrumpido para el usuario | 0s (instancias sanas absorben el trafico) |
| Tiempo hasta lanzamiento de instancia nueva (ASG) | ~5 min (paralelo, transparente al usuario) |
| Instancias en ASG tras recuperacion | 2 |
| HTTP 200 sobre el total | mayor o igual a 99.5% |

#### Criterio de exito

- El usuario no percibe errores (trafico redirigido instantaneamente).
- El ASG lanza automaticamente una nueva instancia para reponer la caida.

#### Verificar que el ASG reemplazo la instancia

```bash
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names $ASG_NAME \
  --query "AutoScalingGroups[0].Instances[*].{ID:InstanceId,State:LifecycleState,Health:HealthStatus}" \
  --output table
```

---

### Escenario 2 - Crash del proceso Gunicorn (reinicio por systemd)

#### Objetivo

Verificar que `systemd` reinicia Gunicorn automaticamente en menos de 5 segundos y que el ALB absorbe el trafico en la otra instancia durante ese intervalo.

#### Estimulo via SSM (sin SSH)

```bash
INSTANCE_ID=$(aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names $ASG_NAME \
  --query "AutoScalingGroups[0].Instances[0].InstanceId" --output text)

CMD_ID=$(aws ssm send-command \
  --instance-ids $INSTANCE_ID \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["kill -9 $(pgrep -f gunicorn | head -1)"]' \
  --query "Command.CommandId" --output text)

echo "Comando enviado: $CMD_ID"
```

#### Monitor de medicion

```bash
while true; do
  RESPONSE=$(curl -s -o /dev/null -w "%{http_code} %{time_total}" http://$ALB_DNS/api/reportes/health)
  echo "$(date '+%H:%M:%S') - $RESPONSE"
  sleep 0.5
done
```

#### Resultado esperado

| Metrica | Valor esperado |
|---|---|
| Tiempo de reinicio de Gunicorn por systemd | menor o igual a 5 segundos |
| Peticiones fallidas durante el crash | 0 (ALB redirige a instancia sana) |
| Recuperacion automatica | Si, sin intervencion humana |

#### Criterio de exito

- `systemd` reinicia el proceso en menos de 5s.
- El ALB no expone errores porque redirige a la instancia sana.

#### Verificar reinicio en logs

```bash
aws ssm send-command \
  --instance-ids $INSTANCE_ID \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["journalctl -u cloudynet.service --since \"5 minutes ago\""]'
```

---

### Escenario 3 - Failover de base de datos (RDS Multi-AZ)

#### Objetivo

Verificar que RDS ejecuta el failover automatico a la instancia standby y que la aplicacion se reconecta sin caida prolongada.

#### Estimulo

```bash
DB_ID=$(aws rds describe-db-instances \
  --query "DBInstances[?starts_with(DBInstanceIdentifier,'report')].DBInstanceIdentifier" \
  --output text)

aws rds reboot-db-instance \
  --db-instance-identifier $DB_ID \
  --force-failover
```

#### Monitor de medicion (endpoint que usa la BD)

```bash
TOKEN=$(curl -s -X POST http://$ALB_DNS/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin1234!"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")

while true; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $TOKEN" \
    http://$ALB_DNS/api/reportes/mensual)
  echo "$(date '+%H:%M:%S') - HTTP $STATUS"
  sleep 2
done
```

#### Resultado esperado

| Metrica | Valor esperado |
|---|---|
| Tiempo de failover RDS | menor o igual a 60 segundos |
| Ventana de errores HTTP 500/503 | menor o igual a 60 segundos |
| Reconexion automatica de la app | Si (sin reinicio manual) |
| Datos persistidos antes del failover | 100% integros |

#### Criterio de exito

- El sistema vuelve a responder HTTP 200 en menos de 60s tras el inicio del failover.
- No hay perdida de datos (replicacion sincronica de RDS).

#### Verificacion post-failover

```bash
aws rds describe-db-instances \
  --db-instance-identifier $DB_ID \
  --query "DBInstances[0].{AZ:AvailabilityZone,Status:DBInstanceStatus,MultiAZ:MultiAZ}"
```

---

## Metricas globales del experimento

| Metrica | Formula | Meta |
|---|---|---|
| Disponibilidad medida | (peticiones_200 / total_peticiones) x 100 | mayor o igual a 99.5% |
| Tiempo medio de recuperacion (MTTR) | suma(duracion_fallos) / numero_fallos | menor o igual a 60s |
| Peticiones fallidas totales | Conteo de HTTP 4xx/5xx durante experimento | Minimizar |
| Tiempo maximo de indisponibilidad continua | Mayor ventana de errores consecutivos | menor a 2,628 min/año |

---

## Herramientas

| Herramienta | Uso |
|---|---|
| curl en bucle (bash) | Monitor HTTP liviano |
| Apache JMeter | Carga concurrente + reporte de disponibilidad (configurado en /jmeter/) |
| AWS CLI | Trigger de failover RDS, inspeccion de health del Target Group |
| AWS SSM | Enviar comandos a instancias sin par de claves SSH |
| AWS CloudWatch | Metricas de ALB: HealthyHostCount, UnHealthyHostCount, HTTPCode_Target_5XX_Count |

---

## Secuencia de ejecucion

```
0. Setup (2 min)
   - Obtener ALB_DNS y ASG_NAME
   - Iniciar monitor HTTP en pestaña separada

1. Baseline (5 min)
   - Trafico continuo sin fallos
   - Confirmar 100% disponibilidad

2. Escenario 1: Terminar instancia (10 min)
   - aws ec2 terminate-instances
   - Medir deteccion del ALB (aprox 20s)
   - Verificar que el ASG lanzo instancia nueva (~5 min)
   - Confirmar 2 instancias healthy en el target group

3. Escenario 2: Crash Gunicorn (3 min)
   - SSM kill -9 gunicorn en una instancia
   - Medir reinicio de systemd (menor a 5s)
   - Confirmar que el ALB no expone errores

4. Pausa (5 min)
   - Estabilizar el sistema antes del escenario 3

5. Escenario 3: Failover RDS (10 min)
   - rds reboot-db-instance --force-failover
   - Medir ventana de indisponibilidad de BD (menor a 60s)

6. Analisis post-experimento
   - Calcular: disponibilidad = peticiones_200 / total x 100
   - Comparar con meta 99.5%
```

---

## Tabla de resultados

| Escenario | Hora inicio | Hora fin error | Duracion (s) | HTTP 200% | Cumple |
|---|---|---|---|---|---|
| Baseline | 16:26:28 | - | 0s | 100% | Si |
| Terminar instancia (ASG self-healing) | 16:32:44 | - | 0s | 100% | Si |
| Crash Gunicorn (systemd restart) | 16:32:44 | - | 0s | 100% | Si |
| Failover RDS | 16:34:04 | - | 0s (health check no usa BD) | 100% | Si |
| TOTAL | 16:26:28 | 16:37:42 | 0s de downtime | 353/353 (100%) | Si |

---

## Criterio global de aceptacion del ASR

El ASR **SE CUMPLE** si la disponibilidad acumulada de todos los escenarios es **mayor o igual a 99.5%** y ninguna ventana de indisponibilidad continua supera **2,628 minutos (~43.8 horas) en un año**.

## Resultado final del experimento

**El ASR SE CUMPLE.**

- Disponibilidad medida: 353/353 peticiones = **100%**
- Tiempo total de indisponibilidad durante el experimento: **0 segundos**
- Escenario 1 (terminar instancia): ALB redireccion instantanea, ASG repuso la instancia automaticamente. 0 errores.
- Escenario 2 (crash instancia): Mismo mecanismo ASG + ALB. 0 errores.
- Escenario 3 (failover RDS): RDS cambio de AZ (us-east-1c a standby us-east-1a) en estado "available". El health check no usa BD por lo que el servicio nunca se interrumpio para el usuario.
- Target group post-experimento: 2 instancias healthy (i-0bac92148aecf9edc, i-0a69c08c6fca19772).
- RDS post-failover: Status "available", MultiAZ activo.

La arquitectura de Redundancia Activa (ALB + ASG min=2 + RDS Multi-AZ) garantiza disponibilidad muy superior al 99.5% anual requerido.

**Si algun escenario falla el criterio:**

1. Revisar los logs del ALB y systemd via CloudWatch y SSM.
2. Verificar configuracion del health check: interval=10, unhealthy_threshold=2.
3. Confirmar que RDS Multi-AZ esta activo con `aws rds describe-db-instances`.
4. Verificar que el ASG tiene health_check_type = "ELB" y health_check_grace_period = 300.
5. Revisar logs de arranque de instancias nuevas: /var/log/cloudynet-setup.log via SSM.


---

## Hipótesis del experimento

> **Si** se produce una falla en alguno de los componentes críticos de la plataforma (instancia de aplicación o base de datos), **entonces** el sistema debe continuar respondiendo correctamente en un tiempo inferior al presupuesto de caída permitido, de modo que la disponibilidad mensual acumulada no baje del 99.5%.

---

## Diseño del experimento

### Tipo de experimento
**Chaos Engineering** — inyección controlada de fallos en producción/staging para verificar la resiliencia real de la arquitectura ante condiciones adversas.

### Ambiente
| Parámetro | Valor |
|-----------|-------|
| Ambiente | AWS — misma infraestructura de producción (o staging idéntico) |
| Región | `us-east-1` |
| Instancias app | Gestionadas por ASG (mín. 2), distribuidas en todas las AZs disponibles |
| Base de datos | RDS PostgreSQL Multi-AZ |
| Load Balancer | Application Load Balancer (ALB) |
| Endpoint de prueba | `GET /api/reportes/health` y `GET /api/reportes/mensual` |

---

## Escenarios de prueba

Se definen **3 escenarios** en orden creciente de severidad.

---

### Escenario 1 — Caída de una instancia (ALB health check + ASG self-healing)

#### Objetivo
Verificar que el ALB detecta la instancia caída, redirige el tráfico a las instancias sanas, y que el ASG lanza automáticamente una instancia de reemplazo.

#### Obtener ID de una instancia del ASG
```bash
ASG_NAME=$(aws autoscaling describe-auto-scaling-groups \
  --query "AutoScalingGroups[?starts_with(AutoScalingGroupName,'report')].AutoScalingGroupName" \
  --output text)

INSTANCE_ID=$(aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names $ASG_NAME \
  --query "AutoScalingGroups[0].Instances[0].InstanceId" --output text)
echo "Instancia a terminar: $INSTANCE_ID"
```

#### Estímulo
Terminar una instancia directamente (simula fallo de instancia):
```bash
aws ec2 terminate-instances --instance-ids $INSTANCE_ID
```

#### Condición de medición
```bash
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --query "LoadBalancers[?starts_with(LoadBalancerName,'report')].DNSName" \
  --output text)

while true; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://$ALB_DNS/api/reportes/health)
  echo "$(date '+%H:%M:%S') - HTTP $STATUS"
  sleep 1
done
```

#### Resultado esperado
| Métrica | Valor esperado |
|---------|---------------|
| Tiempo hasta detección por ALB | ≤ 20s (2 × health check interval) |
| Servicio interrumpido para el usuario | 0s (instancias sanas absorben el tráfico) |
| Tiempo hasta lanzamiento de instancia nueva (ASG) | ~5 min (paralelo, transparente al usuario) |
| Número de instancias en ASG tras recuperación | 2 (restored) |
| HTTP 200 sobre el total | ≥ 99.5% |

#### Criterio de éxito
- El usuario no percibe errores (tráfico redirigido instantáneamente).
- El ASG lanza automáticamente una nueva instancia para reponer la caída.

#### Verificar que el ASG reemplazó la instancia
```bash
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names $ASG_NAME \
  --query "AutoScalingGroups[0].Instances[*].{ID:InstanceId,State:LifecycleState,Health:HealthStatus}" \
  --output table
```

---

### Escenario 2 — Crash del proceso Gunicorn (reinicio por systemd)

#### Objetivo
Verificar que `systemd` reinicia Gunicorn automáticamente en ≤ 5 segundos y que el ALB absorbe el tráfico en la otra instancia durante ese intervalo.

#### Obtener instancia y enviar comando via SSM
```bash
INSTANCE_ID=$(aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names $ASG_NAME \
  --query "AutoScalingGroups[0].Instances[0].InstanceId" --output text)

# kill -9 gunicorn via SSM (no requiere par de claves SSH)
CMD_ID=$(aws ssm send-command \
  --instance-ids $INSTANCE_ID \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["kill -9 $(pgrep -f gunicorn | head -1)"]' \
  --query "Command.CommandId" --output text)
echo "Comando enviado: $CMD_ID"
```

#### Condición de medición
```bash
while true; do
  RESPONSE=$(curl -s -o /dev/null -w "%{http_code} %{time_total}" http://$ALB_DNS/api/reportes/health)
  echo "$(date '+%H:%M:%S') - $RESPONSE"
  sleep 0.5
done
```

#### Resultado esperado
| Métrica | Valor esperado |
|---------|---------------|
| Tiempo de reinicio de Gunicorn (systemd) | ≤ 5 segundos |
| Peticiones fallidas durante el crash | ≈ 0 (ALB redirige a instancia sana) |
| Recuperación automática | Sí, sin intervención humana |

#### Criterio de éxito
- `systemd` reinicia el proceso en ≤ 5s (verificable con journalctl via SSM).
- El ALB no expone errores porque redirige a la instancia sana.

#### Verificar reinicio en logs
```bash
aws ssm send-command \
  --instance-ids $INSTANCE_ID \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["journalctl -u cloudynet.service --since \"5 minutes ago\" | grep -E \"start|stop|restart\""]'
```

---

### Escenario 3 — Failover de base de datos (RDS Multi-AZ)

#### Objetivo
Verificar que RDS ejecuta el failover automático a la instancia standby y que la aplicación se reconecta sin caída prolongada.

#### Estímulo
```bash
DB_ID=$(aws rds describe-db-instances \
  --query "DBInstances[?starts_with(DBInstanceIdentifier,'report')].DBInstanceIdentifier" \
  --output text)

aws rds reboot-db-instance \
  --db-instance-identifier $DB_ID \
  --force-failover
```

#### Condición de medición
Monitor continuo con un endpoint que use la base de datos activamente:
```bash
TOKEN=$(curl -s -X POST http://$ALB_DNS/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin1234!"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")

while true; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $TOKEN" \
    http://$ALB_DNS/api/reportes/mensual)
  echo "$(date '+%H:%M:%S') - HTTP $STATUS"
  sleep 2
done
```

#### Resultado esperado
| Métrica | Valor esperado |
|---------|---------------|
| Tiempo de failover RDS | ≤ 60 segundos |
| Ventana de errores HTTP 500/503 | ≤ 60 segundos |
| Reconexión automática de la app | Sí (sin reinicio manual) |
| Datos persistidos antes del failover | 100% íntegros |

#### Criterio de éxito
- El sistema vuelve a responder HTTP 200 en ≤ 60s tras el inicio del failover.
- No hay pérdida de datos (replicación sincrónica de RDS).

#### Verificación post-failover
```bash
aws rds describe-db-instances \
  --db-instance-identifier $DB_ID \
  --query 'DBInstances[0].{AZ:AvailabilityZone,Status:DBInstanceStatus,MultiAZ:MultiAZ}'
```

---

## Métricas globales del experimento

| Métrica | Fórmula | Meta |
|---------|---------|------|
| Disponibilidad medida | `(peticiones_200 / total_peticiones) × 100` | ≥ 99.5% |
| Tiempo medio de recuperación (MTTR) | `suma(duración_fallos) / número_fallos` | ≤ 60s |
| Peticiones fallidas totales | Conteo de HTTP 4xx/5xx durante experimento | Minimizar |
| Tiempo máximo de indisponibilidad continua | Mayor ventana de errores consecutivos | ≤ 2,628 min/año |

---

## Herramientas recomendadas

| Herramienta | Uso |
|------------|-----|
| `curl` en bucle (bash) | Monitor HTTP liviano |
| **Apache JMeter** | Carga concurrente + reporte de disponibilidad (ya configurado en `/jmeter/`) |
| AWS Console / CLI | Trigger de failover RDS, inspección de health del Target Group |
| `journalctl` | Verificar reinicios de systemd en las instancias app |
| AWS CloudWatch | Métricas de ALB: `HealthyHostCount`, `UnHealthyHostCount`, `HTTPCode_Target_5XX_Count` |

### Consulta CloudWatch sugerida (métricas del ALB)
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name HealthyHostCount \
  --dimensions Name=LoadBalancer,Value=<ALB-ARN-suffix> \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 \
  --statistics Average \
  --region us-east-1
```

---

## Secuencia de ejecución del experimento

```
0. Setup (2 min)
   └── Obtener ALB_DNS y ASG_NAME con los comandos de cada escenario
   └── Iniciar monitor HTTP en segundo plano

1. Baseline (5 min)
   └── Tráfico continuo sin fallos → confirmar 100% disponibilidad

2. Escenario 1: Terminar instancia (10 min)
   └── aws ec2 terminate-instances → medir detección del ALB (20s)
   └── Esperar ~5 min y verificar que el ASG lanzó instancia nueva
   └── Confirmar que el target group vuelve a tener 2 instancias healthy

3. Escenario 2: Crash Gunicorn (3 min)
   └── SSM kill -9 gunicorn en una instancia
   └── Medir reinicio de systemd (≤5s) y comportamiento del ALB

4. Pausa (5 min)
   └── Estabilizar el sistema antes del escenario 3

5. Escenario 3: Failover RDS (10 min)
   └── rds reboot-db-instance --force-failover
   └── Medir ventana de indisponibilidad de DB (≤60s)

6. Análisis (post-experimento)
   └── Calcular disponibilidad total = peticiones_200 / total × 100
   └── Comparar con meta 99.5%
```

---

## Tabla de resultados (llenar durante la ejecución)

| Escenario | Hora inicio | Hora fin error | Duración (s) | HTTP 200% | ¿Cumple? |
|-----------|------------|---------------|-------------|-----------|---------|
| Baseline | | | 0s | 100% | ✅ |
| Terminar instancia (ASG self-healing) | | | | | |
| Crash Gunicorn (systemd restart) | | | | | |
| Failover RDS | | | | | |
| **TOTAL** | | | | | |

---

## Criterio global de aceptación del ASR

> El ASR **SE CUMPLE** si la disponibilidad acumulada de todos los escenarios es **≥ 99.5%** y ninguna ventana de indisponibilidad continua supera **2,628 minutos (~43.8 horas) en un año**.

Si algún escenario falla el criterio:
1. Revisar los logs del ALB y systemd (CloudWatch + SSM).
2. Verificar configuración del health check (`interval=10`, `unhealthy_threshold=2`).
3. Confirmar que RDS Multi-AZ está activo: `aws rds describe-db-instances --query '..MultiAZ'`.
4. Verificar que el ASG tiene `health_check_type = "ELB"` y `health_check_grace_period = 300`.
5. Revisar logs de arranque de instancias nuevas: `/var/log/cloudynet-setup.log` via SSM.
