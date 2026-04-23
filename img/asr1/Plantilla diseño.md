# Plantilla de diseño del experimento — ASR1

> **ASR1 — Latencia:** Como consultor tecnológico de BITE.CO, ante múltiples intentos fallidos de
> autenticación (con el sistema operando correctamente), se debe detectar el comportamiento anómalo
> y restringir el acceso temporalmente **en menos de 2 segundos**.

---

## Datos del experimento

| Campo | Detalle |
|:---|:---|
| **Título** | Validación de latencia end-to-end (< 2 s) para detección de intentos fallidos y restricción temporal con ALB y dos instancias EC2 |
| **ASRs involucrados** | ASR1 — Latencia: detección de anomalía y restricción de acceso en < 2 s bajo carga real |
| **Propósito** | Comprobar si el diseño (ALB + 2 EC2 + modelo de bloqueo) satisface el ASR1: tiempo total desde la petición hasta la persistencia del bloqueo inferior a 2 s, con health checks estables |
| **Resultados esperados** | Health Check _Healthy_ bajo carga; <br/>registro en `AuditoriaAcceso`; <br/>bloqueo en `IntentoBloqueado` con `activo = True` y `fecha_bloqueo_hasta`; <br/>latencia JMeter < 2 000 ms end-to-end |
| **Elementos de arquitectura** | ALB `report-alb` (Internet-facing, IPv4); <br/>2× EC2 t2.nano: `report-app-lb-a`, `report-app-lb-b`; <br/>Target Group `report-app-group` (HTTP:8080); <br/>Modelos Django: `IntentoBloqueado`, `AuditoriaAcceso` |
| **Estilos de arquitectura** | **Microservicios:** autenticación, usuarios, recursos cloud, reportes y empresa como servicios independientes, desplegables y escalables por separado |
| **Tácticas asociadas** | **Distribución de carga:** el ALB concentra el tráfico y prepara el escalado horizontal <br/>**Aislamiento de recursos:** bases de datos separadas por dominio para reducir contención |
| **Infraestructura requerida** | ALB `report-alb`; <br/>2× EC2 t2.nano en us-east-1; <br/>1× EC2 t3.micro para DB (`report-db`); <br/>Target Group con 2 targets healthy; <br/>Estación JMeter |
| **Tecnologías** | AWS ALB, EC2, Security Groups, Target Groups; <br/>Django con `IntentoBloqueado` y `AuditoriaAcceso`; <br/>Apache JMeter para carga concurrente |
| **Descripción** | Ráfagas de login fallidas al ALB → EC2 aplica lógica de detección → persiste bloqueo en `intentos_bloqueados`. Métricas: tiempo JMeter (envío → respuesta) y consola AWS (estado del target). Se contrasta con el umbral de 2 s |
| **Plan de uso de IAG** | GitHub Copilot: <br/>(1) estructura base del plan de pruebas JMeter <br/>(2) revisión de configuración de Security Groups <br/>(3) redacción del documento de evidencia |

---

## Flujo del experimento

:::mermaid
graph LR;
    A[JMeter<br/>5 000 hilos] -->|POST /api/auth/login<br/>credenciales inválidas| B(ALB<br/>report-alb)
    B --> C{EC2 API Auth}
    C -->|intentos 1-4: 401| D[(DB<br/>AuditoriaAcceso)]
    C -->|intento 5: INSERT bloqueo| E[(DB<br/>IntentoBloqueado<br/>activo=True · 300 s)]
    E -->|429 Too Many Requests| B
    B -->|429| A
    C -->|health check| F[GET /api/auth/health<br/>→ 200 OK]
:::

---

## Checklist de validación

- [ ] Health Check del ALB en estado _Healthy_ durante toda la prueba
- [ ] Registro de intentos en `AuditoriaAcceso`
- [ ] Bloqueo creado en `IntentoBloqueado` con `activo = True` tras 5 intentos
- [ ] Campo `fecha_bloqueo_hasta` correcto (ahora + 300 s)
- [ ] Latencia promedio en JMeter < 2 000 ms
- [ ] Respuestas cambian de `401` a `429` tras el bloqueo
- [ ] IP del cliente tomada correctamente desde el ALB en `esta_bloqueado()`
- [ ] Consumo de recursos de la instancia EC2 dentro de límites operativos
