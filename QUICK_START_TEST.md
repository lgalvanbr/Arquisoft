# ⚡ QUICK START - Ejecutar JMeter Test Ahora

## Estado Actual del Test

✅ **Configurado y listo**
- Sequential execution: Phase 1 → Phase 2
- Solo `/api/reportes/consumo`
- Sin loop: 1 request por usuario
- Phase 1: 5,000 usuarios → 5,000 requests
- Phase 2: 7,000 usuarios → 7,000 requests
- **Total: 12,000 requests en ~20 minutos**

---

## Requisito Previo: Verificar ALB Healthy

```bash
# Verificar targets están healthy
aws elbv2 describe-target-health \
  --target-group-arn <TARGET_GROUP_ARN> \
  --region us-east-1
```

**Debe mostrar:** 4 app instances con `"State": "healthy"`

Si NO están healthy → Ver `GUNICORN_RECOVERY.md`

---

## Opción 1: Ejecutar (RECOMENDADO)

```bash
cd jmeter
mkdir -p results

jmeter -n \
  -t load-test-asr.jmx \
  -l results/load-test-results.jtl \
  -j results/load-test.log
```

**Duración:** ~20 minutos

**Output:**
- `results/load-test-results.jtl` - CSV con todos los samples
- `results/load-test.log` - Logs de ejecución

---

## Ver Resultados en Tiempo Real

En otra terminal:

```bash
cd jmeter
tail -f results/load-test.log
```

---

## Análisis Rápido Después

```bash
# Total de requests
wc -l jmeter/results/load-test-results.jtl

# Error rate
grep ",false" jmeter/results/load-test-results.jtl | wc -l

# Success count
grep ",true" jmeter/results/load-test-results.jtl | wc -l
```

---

## Fases de Ejecución

### Phase 1 (Minutos 0-10)
- 5,000 usuarios aparecen instantáneamente
- Hacen 1 request cada uno
- Se completa en ~5 segundos
- Luego espera hasta minuto 10

### Phase 2 (Minutos 10-20)
- 7,000 usuarios adicionales se agregan gradualmente
- Cada uno hace 1 request
- Los usuarios se distribuyen a lo largo de 10 minutos

### Timeline
```
0:00  - Phase 1: 5K usuarios, 5K requests (spike)
0:05  - Phase 1 termina, espera
10:00 - Phase 2: 7K usuarios rampeados, 7K requests (gradual)
20:00 - Test termina
```

---

## Monitorear Gunicorn Durante Test

En otra terminal:

```bash
ssh -i your-key.pem ubuntu@<APP_IP>
sudo journalctl -u gunicorn -f
```

Deberías ver aumento de tráfico en Phase 1 y Phase 2.

---

## Validación ASR

Después del test, verifica:

```bash
# Error rate < 5%
total=$(wc -l < jmeter/results/load-test-results.jtl)
errors=$(grep ",false" jmeter/results/load-test-results.jtl | wc -l)
rate=$((errors * 100 / total))
echo "Error rate: ${rate}%"

# Latencia (extraer valores)
cut -d',' -f2 jmeter/results/load-test-results.jtl | tail -n +2 | sort -n
```

---

## Si Falla

### "Connection refused"
```bash
# Verifica ALB responde
curl -v http://<ALB_DNS>/api/reportes/consumo
```

### "Targets not healthy"
```bash
# Recuperar instancias
cd terraform
bash recovery-gunicorn.sh
```

### "Test stuck"
```bash
# Detener JMeter
pkill -f jmeter
```

---

**¡Listo para ejecutar!** 🚀

```bash
cd jmeter && jmeter -n -t load-test-asr.jmx -l results/load-test-results.jtl -j results/load-test.log
```

Espera ~20 minutos.
