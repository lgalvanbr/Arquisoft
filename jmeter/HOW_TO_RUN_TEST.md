# 🚀 CÓMO EJECUTAR EL LOAD TEST

## Estado Actual

El test de carga JMeter está **listo para ejecutar** con la configuración final:

✅ **Secuencial:** Phase 1 → Phase 2  
✅ **Endpoint único:** `/api/reportes/consumo`  
✅ **Carga:** 5K → 12K usuarios  
✅ **Duración:** 20 minutos  

---

## Prerrequisitos

### 1. Instancias EC2 Recuperadas
```bash
# Verify gunicorn is running on all instances
aws ec2 describe-instance-status --region us-east-1 --query 'InstanceStatuses[?State.Name==`running`]'

# Should show 4 app instances + 1 database instance = 5 total
```

### 2. ALB Targets Healthy
```bash
aws elbv2 describe-target-health \
  --target-group-arn <TARGET_GROUP_ARN> \
  --region us-east-1
```

**Expected:** All targets show `"State": "healthy"`

### 3. ALB DNS Name
```bash
cd terraform
ALB_DNS=$(terraform output alb_dns_name | tr -d '"')
echo $ALB_DNS
# Output: report-alb-XXXXXXXXX.us-east-1.elb.amazonaws.com
```

### 4. Verify ALB Responds
```bash
curl -v http://$ALB_DNS/api/reportes/consumo
# Expected: HTTP 200 OK
```

---

## Ejecutar el Test

### Opción 1: JMeter GUI (Interfaz Gráfica)
```bash
cd jmeter
jmeter -t load-test-asr.jmx
```

**Ventajas:**
- Visual en tiempo real
- Gráficos en vivo
- Fácil de ver qué pasa

**Desventajas:**
- Requiere X11 o display gráfico
- Mayor consumo de recursos

---

### Opción 2: Headless Mode (Recomendado)
```bash
cd jmeter

# Ejecutar test sin GUI
jmeter -n \
  -t load-test-asr.jmx \
  -l results/load-test-results.jtl \
  -j results/load-test.log

# Ver logs en tiempo real (en otra terminal)
tail -f results/load-test.log
```

**Ventajas:**
- Menor consumo de recursos
- Mejor para servidores remotos
- Resultados claros en archivos

**Desventajas:**
- No es visual mientras se ejecuta

---

### Opción 3: Usar Script (Automated)
```bash
cd jmeter
bash run-load-test.sh
```

(Si existe el script)

---

## Monitorear Durante la Ejecución

### Terminal 1: JMeter Logs
```bash
tail -f results/load-test.log
```

**Expected output:**
```
2026-04-05 22:45:00 Started TestPlan
2026-04-05 22:45:01 Phase 1: Starting 5000 users instantly
2026-04-05 22:45:05 Phase 1: All 5000 users loaded
...
2026-04-05 22:55:00 Phase 2: Starting ramp-up of 7000 additional users
...
2026-04-05 23:05:00 Test finished
```

### Terminal 2: Gunicorn Logs on App Instances
```bash
# SSH to one app instance
ssh -i your-key.pem ubuntu@<APP_INSTANCE_IP>

# Monitor gunicorn
sudo journalctl -u gunicorn -f

# Expected: High throughput during test
```

### Terminal 3: System Metrics (if available)
```bash
# Monitor AWS resources
aws ec2 describe-instances --region us-east-1 \
  --query 'Reservations[].Instances[].[InstanceId,State.Name,PublicIpAddress]' \
  --output table
```

---

## Fases de Ejecución

### Fase 1: Base Load (Minutos 0-10)
```
Usuarios: 5,000 instantáneamente (ramp_time: 0s)
Duración: 600 segundos (10 minutos)
Endpoint: GET /api/reportes/consumo
```

**Qué esperar:**
- Spike inmediato de tráfico
- Latencia puede aumentar rápidamente
- Servidor debe responder
- Observar error rate

### Fase 2: Ramp-up (Minutos 10-20)
```
Usuarios: 7,000 gradualmente añadidos (ramp_time: 600s)
Duración: 600 segundos (10 minutos)
Usuarios finales: 5K + 7K = 12,000 total
Endpoint: GET /api/reportes/consumo
```

**Qué esperar:**
- Aumento gradual de usuarios
- Latencia continúa aumentando
- Sistema bajo estrés máximo
- Validar ASR requirements

---

## Validar Resultados

### 1. Test Completó Exitosamente
```bash
ls -la results/
# Expected files:
# - load-test-results.jtl  (CSV with all samples)
# - load-test.log          (JMeter execution log)
```

### 2. Ver Resumen Rápido
```bash
# Total samples
grep -c "^" results/load-test-results.jtl

# Error samples
grep ",false" results/load-test-results.jtl | wc -l

# Success rate
echo "scale=2; ($(grep -c ",true" results/load-test-results.jtl) / $(grep -c "^" results/load-test-results.jtl) * 100)" | bc
```

### 3. Analizar con JMeter (GUI)
```bash
jmeter -t load-test-asr.jmx -l results/load-test-results.jtl
```

Esto cargará el test en el GUI con los resultados.

---

## ASR Compliance Validation

Después de ejecutar, verifica estos métricas:

### Requisito 1: 12,000 Usuarios Concurrentes
✅ **Esperado:** Test ejecuta 5K + 7K = 12,000  
📊 **Verifica:** Phase 2 muestra ramping hasta 12K

### Requisito 2: Latencia p50 2-5 segundos
```bash
# Extraer latencias
grep "^" results/load-test-results.jtl | cut -d',' -f2 | sort -n | \
  awk '{sum+=$1; if(NR==int(NR/2)) p50=$1} END {print "p50:", p50, "ms"}'
```

**Esperado:** 2,000-5,000 ms (2-5 segundos)

### Requisito 3: Latencia p95 < 7 segundos
```bash
grep "^" results/load-test-results.jtl | cut -d',' -f2 | sort -n | \
  awk '{a[NR]=$1} END {print "p95:", a[int(NR*0.95)], "ms"}'
```

**Esperado:** < 7,000 ms

### Requisito 4: Error Rate < 5%
```bash
total=$(grep -c "^" results/load-test-results.jtl)
errors=$(grep ",false" results/load-test-results.jtl | wc -l)
error_rate=$((errors * 100 / total))
echo "Error rate: ${error_rate}%"
```

**Esperado:** < 5%

### Requisito 5: Disponibilidad ≥ 95%
```bash
# Si error rate es < 5%, availability es > 95% ✓
# Availability = 100% - error_rate
```

---

## Troubleshooting

### "Connection refused" al test
**Solución:**
1. Verificar ALB está responding: `curl http://$ALB_DNS/api/reportes/consumo`
2. Verificar instancias están healthy: `aws elbv2 describe-target-health ...`
3. Verificar security group permite puerto 80
4. Verificar ALB DNS es correcto en load-test-asr.jmx

### Test muy lento / timeouts
**Solución:**
1. Verificar capacidad de instancias: `sudo systemctl status gunicorn`
2. Verificar base de datos está respondiendo
3. Verificar network latency
4. Considerarescalar instancias (Phase 3 del roadmap)

### ALB targets no healthy
**Solución:**
1. SSH a una instancia
2. Verificar gunicorn: `sudo systemctl status gunicorn`
3. Ver logs: `sudo journalctl -u gunicorn -f`
4. Ejecutar recovery: `bash terraform/recovery-gunicorn.sh`

### JMeter process stuck
**Solución:**
```bash
# Detener JMeter
pkill -f jmeter

# Ver procesos Java
ps aux | grep java

# Limpiar si hay procesos residuales
killall java
```

---

## Próximos Pasos Después del Test

### Si los resultados CUMPLEN ASR:
1. ✅ Documentar resultados
2. ✅ Proceder a Phase 1 security fixes (CRÍTICO)
3. ✅ Proceder a Phase 2 improvements
4. ✅ Proceder a Phase 3 scaling

### Si los resultados NO cumplen ASR:
1. 📊 Analizar dónde falla (latencia, error rate, etc.)
2. 🔧 Implementar fixes específicos
3. ⚠️ Probablemente requiere Phase 3 scaling
4. 🔄 Re-ejecutar test

---

## Ejemplo Completo

```bash
# 1. Prepara ambiente
cd jmeter
mkdir -p results

# 2. Ejecuta test (headless, 20 minutos)
echo "Starting load test at $(date)..."
jmeter -n \
  -t load-test-asr.jmx \
  -l results/load-test-results.jtl \
  -j results/load-test.log

echo "Test finished at $(date)"

# 3. Analiza resultados
echo ""
echo "=== RESULTS SUMMARY ==="
total_samples=$(grep -c "^" results/load-test-results.jtl)
failed_samples=$(grep ",false" results/load-test-results.jtl | wc -l)
success_rate=$((($total_samples - $failed_samples) * 100 / $total_samples))

echo "Total samples: $total_samples"
echo "Failed samples: $failed_samples"
echo "Success rate: ${success_rate}%"
echo "Error rate: $((100 - success_rate))%"

# 4. Valida ASR
echo ""
echo "=== ASR VALIDATION ==="
if [ $((100 - success_rate)) -lt 5 ]; then
    echo "✅ Error rate < 5%: PASS"
else
    echo "❌ Error rate < 5%: FAIL (${((100 - success_rate))}%)"
fi
```

---

## Archivos Generados

Después del test, encontrarás:

```
results/
├── load-test-results.jtl   # CSV con todos los samples
├── load-test.log           # Logs de ejecución JMeter
└── [gráficos si usaste GUI]
```

---

**¡Listo para ejecutar!**

Comando rápido:
```bash
cd jmeter && jmeter -n -t load-test-asr.jmx -l results/load-test-results.jtl -j results/load-test.log
```

Durará ~20 minutos. ⏱️
