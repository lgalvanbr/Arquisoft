# Experimento ASR 2 — Disponibilidad 99.5% Anual

## Descripción del ASR

> Yo como usuario, dado que la plataforma es utilizada para la toma de decisiones financieras críticas, cuando accedo al sistema en cualquier momento, quiero que la plataforma esté disponible sin interrupciones, garantizando una disponibilidad mínima del **99.5% anual** sin caídas del servicio.

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
