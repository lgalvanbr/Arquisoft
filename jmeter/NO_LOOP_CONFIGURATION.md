# JMeter Test: Sin Loop - 1 Request por Usuario

## Cambios Realizados

### Antes (Con Loop):
```
- Loop infinito (-1) en cada ThreadGroup
- Cada usuario hace ~40-50 requests
- Total: ~500,000+ requests en 20 minutos
- Throughput: ~400 requests/segundo
```

### Después (Sin Loop):
```
- Loop fijo (1) en cada ThreadGroup
- Cada usuario hace exactamente 1 request
- Total: 12,000 requests en 20 minutos
- Throughput: ~10 requests/segundo
```

---

## Detalles de Ejecución

### Phase 1: Base Load (0-10 minutos)
```
Usuarios: 5,000
Ramp-up: 0 segundos (instantáneo)
Duración: 600 segundos
Requests por usuario: 1
Total requests: 5,000
Endpoint: GET /api/reportes/consumo
```

**Timeline:**
- 0s: 5,000 usuarios aparecen instantáneamente
- 0s: Todos hacen 1 request a /api/reportes/consumo
- ~2-5s: Todos los requests se completan
- ~5-600s: Nada (waiting until phase 2)

### Phase 2: Incremental Load (10-20 minutos)
```
Usuarios: 7,000 adicionales
Ramp-up: 600 segundos (gradual)
Duración: 600 segundos
Requests por usuario: 1
Total requests: 7,000
Endpoint: GET /api/reportes/consumo
```

**Timeline:**
- 600s (10:00): Phase 2 comienza
- 600-1200s: 7,000 usuarios se agregan gradualmente (~11.67 usuarios/segundo)
- 600-1200s: Cada usuario hace 1 request al llegar
- ~1200s: Todos los 12,000 usuarios han hecho su 1 request

---

## Gráfico de Carga

```
Usuarios Concurrentes
           |
      12K |                                    ↓ todos terminan
           |                                   |
       7K |                    ↓ phase 2 ramp-up
           |                   /
       5K |     ↓ phase 1 instant
           |    |
        0 |____|__________________|___________
          0:00  0:05              10:00  15:00 20:00
          Phase 1              Phase 2
          (5s total)           (600s total)
```

### Timeline Detallado:

```
Tiempo (min) | Evento
0:00         | Phase 1 comienza: 5,000 usuarios cargan instantáneamente
0:00-0:05    | 5,000 usuarios hacen requests (5,000 total)
0:05-10:00   | Espera (no hay actividad)
10:00        | Phase 2 comienza: 7,000 usuarios comienzan ramp-up
10:00-20:00  | 7,000 usuarios se agregan gradualmente, cada uno hace 1 request
20:00        | Test termina
```

---

## Cambios en el Archivo JMeter

### ThreadGroup Phase 1:
```xml
<!-- Antes -->
<intProp name="LoopController.loops">-1</intProp>  <!-- Infinito -->

<!-- Después -->
<intProp name="LoopController.loops">1</intProp>   <!-- Solo 1 iteración -->
```

### ThreadGroup Phase 2:
```xml
<!-- Antes -->
<intProp name="LoopController.loops">-1</intProp>  <!-- Infinito -->

<!-- Después -->
<intProp name="LoopController.loops">1</intProp>   <!-- Solo 1 iteración -->
```

### LoopController de HTTPSampler:
```xml
<!-- Antes -->
<LoopController testname="Loop - GET /api/reportes/consumo">
  <boolProp name="LoopController.continue_forever">true</boolProp>
  <intProp name="LoopController.loops">-1</intProp>
</LoopController>

<!-- Después -->
<!-- ELIMINADO - El HTTPSampler se ejecuta directamente sin loop -->
```

---

## Métricas Esperadas

| Métrica | Valor |
|---------|-------|
| Total Usuarios | 12,000 |
| Total Requests | 12,000 |
| Requests/Usuario | 1 |
| Duración | 20 minutos |
| Throughput Promedio | ~10 req/sec |
| Phase 1 Throughput | ~1,000 req/sec (spike) |
| Phase 2 Throughput | ~11.67 req/sec (gradual) |

---

## Cómo Ejecutar

```bash
cd jmeter

# Headless mode (recomendado)
jmeter -n \
  -t load-test-asr.jmx \
  -l results/load-test-results.jtl \
  -j results/load-test.log

# O con GUI
jmeter -t load-test-asr.jmx
```

---

## Analizar Resultados

### Ver logs en tiempo real:
```bash
tail -f results/load-test.log
```

### Contar total de requests:
```bash
grep -c "^" results/load-test-results.jtl
# Expected: ~12,000 (aproximadamente)
```

### Ver distribución de latencias:
```bash
# Extraer columna de latencia
cut -d',' -f2 results/load-test-results.jtl | tail -n +2 | sort -n | tail -20
```

### Error rate:
```bash
total=$(grep -c "^" results/load-test-results.jtl)
errors=$(grep ",false" results/load-test-results.jtl | wc -l)
error_rate=$((errors * 100 / total))
echo "Error rate: ${error_rate}%"
```

---

## Consideraciones

### Ventajas de Sin Loop:
- ✅ Simple y claro: cada usuario hace 1 request
- ✅ Menos carga en JMeter
- ✅ Resultados más predecibles
- ✅ Fácil de analizar

### Desventajas de Sin Loop:
- ❌ Muy poco tráfico (~10 req/sec vs ~400 req/sec con loop)
- ❌ No es un load test realista
- ❌ No prueba bien la capacidad sostenida del servidor
- ❌ Phase 1 se completa en ~5 segundos (no 10 minutos)
- ❌ Difícil validar ASR (necesita tráfico sostenido)

---

## Diferencia con Loop

### Con Loop (anterior):
- 5,000 usuarios × 40 requests = 200,000 requests
- Tráfico sostenido durante 10 minutos
- Observas comportamiento bajo carga

### Sin Loop (actual):
- 5,000 usuarios × 1 request = 5,000 requests
- Tráfico en "ráfaga" (spike al principio)
- Observas respuesta inicial, no comportamiento sostenido

---

**Cambio en Git:** `3b0ac81`  
**Archivo:** `jmeter/load-test-asr.jmx`  
**Estado:** Ready to execute ✅
