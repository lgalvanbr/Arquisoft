# ASR1 — Latencia y bloqueo ante autenticación fallida

> **Escenario de calidad (ASR1):** Como consultor tecnológico de BITE.CO, ante múltiples intentos
> fallidos de autenticación (sistema operando correctamente), el sistema debe detectar el comportamiento
> anómalo y restringir el acceso temporalmente **en menos de 2 segundos**.
>
> **Resultado del experimento: promedio 245 ms con 5 000 muestras → criterio CUMPLIDO ✓**

[[_TOC_]]

---

## 1. Plantilla de diseño del experimento

| Campo | Detalle |
|:---|:---|
| **Título** | Validación de latencia end-to-end (< 2 s) para detección de intentos fallidos y restricción temporal (`IntentoBloqueado`) con ALB y dos instancias EC2 |
| **ASRs involucrados** | **ASR1 — Latencia:** detección de comportamiento anómalo y restricción de acceso en < 2 s bajo carga real |
| **Propósito** | Comprobar si el diseño (ALB + 2 instancias EC2 + modelo de bloqueo) satisface el ASR1: tiempo total desde la petición en el balanceador hasta la persistencia del bloqueo < 2 s, con health checks estables |
| **Resultados esperados** | Health check en estado _Healthy_ bajo carga JMeter; registro en `AuditoriaAcceso` y bloqueo en `IntentoBloqueado` con `activo = True`; latencia JMeter < 2 000 ms end-to-end |
| **Elementos de arquitectura** | ALB `report-alb` (Internet-facing); 2× EC2 t2.nano (`report-app-lb-a`, `report-app-lb-b`); Target Group `report-app-group` (HTTP:8080); Security Groups; modelos Django `IntentoBloqueado` y `AuditoriaAcceso` |
| **Estilo arquitectónico** | **Microservicios:** autenticación, usuarios, recursos cloud, reportes y empresa como servicios independientes — se valida el flujo crítico de autenticación/bloqueo expuesto tras el ALB |
| **Tácticas** | **Distribución de carga:** el ALB concentra el tráfico y prepara el escalado horizontal. **Aislamiento de recursos:** bases de datos separadas por dominio para reducir contención |
| **Infraestructura requerida** | ALB público; 2× EC2 t2.nano en us-east-1; 1× EC2 t3.micro para DB (`report-db`); Security Groups por capa; Target Group con health check activo; JMeter en equipo de pruebas |
| **Tecnologías** | AWS ALB, EC2, Security Groups, Target Groups; Django con `IntentoBloqueado` y `AuditoriaAcceso`; Apache JMeter para carga concurrente en el endpoint de login |
| **Descripción** | Se envían ráfagas de login fallidas al ALB → instancia activa aplica lógica de detección → persiste en `intentos_bloqueados` con `activo` y `fecha_bloqueo_hasta`. Se contrasta el tiempo total con el umbral de 2 s del ASR1 |
| **Plan de uso de IAG** | GitHub Copilot: (1) estructura base del test JMeter, (2) revisión de configuración de Security Groups, (3) redacción y estructuración del documento de evidencia |

---

## 2. Flujo de detección y bloqueo

El siguiente diagrama de secuencia muestra el comportamiento del sistema ante los 5 intentos fallidos de login y la activación del bloqueo:

:::mermaid
sequenceDiagram
    autonumber
    participant JM as JMeter<br/>(5 000 hilos)
    participant ALB as Application Load Balancer<br/>report-alb
    participant EC2 as EC2 API Auth<br/>(report-app-lb-b)
    participant DB as Base de datos<br/>(IntentoBloqueado)

    JM->>ALB: POST /api/auth/login (credenciales inválidas)
    ALB->>EC2: reenvía petición al target healthy
    EC2->>DB: consulta esta_bloqueado(IP)
    DB-->>EC2: no bloqueado
    EC2-->>ALB: 401 Unauthorized
    ALB-->>JM: 401 Unauthorized

    Note over JM,EC2: Intentos 2, 3 y 4 → mismo ciclo, acumulando conteo en DB

    JM->>ALB: POST /api/auth/login (intento 5)
    ALB->>EC2: reenvía petición
    EC2->>DB: INSERT IntentoBloqueado(activo=True, 300s)
    DB-->>EC2: bloqueo persistido
    EC2-->>ALB: 429 Too Many Requests
    ALB-->>JM: 429 + "ANOMALÍA DETECTADA"

    Note over JM,DB: Todos los intentos posteriores desde esa IP reciben 429 durante 300 s

    loop Health check cada ~15 s
        ALB->>EC2: GET /api/auth/health
        EC2-->>ALB: 200 OK (healthy)
    end
:::

---

## 3. Estados de una IP durante el experimento

:::mermaid
stateDiagram-v2
    [*] --> Normal : IP nueva / sin intentos
    Normal --> Sospechoso : 1 intento fallido de login
    Sospechoso --> Sospechoso : intentos 2 - 4 (conteo acumulando)
    Sospechoso --> Bloqueado : intento 5 → ANOMALÍA DETECTADA<br/>IntentoBloqueado activo=True
    Bloqueado --> Normal : 300 s transcurridos → bloqueo expirado
    Bloqueado --> Bloqueado : nuevos intentos → 429 (bloqueo activo)

    Normal : Respuesta normal<br/>HTTP 401
    Sospechoso : Bajo vigilancia<br/>HTTP 401 · conteo activo
    Bloqueado : IP RESTRINGIDA<br/>HTTP 429 · 300 s
:::

---

## 4. Infraestructura AWS desplegada

Application Load Balancer **report-alb** (Internet-facing, IPv4) enruta hacia dos instancias EC2 _report-app-lb-a_ y _report-app-lb-b_ (t2.nano), con un grupo objetivo **report-app-group** con 2 targets saludables en HTTP:8080.

### Instancias EC2

![AWS EC2 Instances](/.attachments/Instancias.png)

Tres instancias activas: `report-db` (t3.micro), `report-app-lb-a` y `report-app-lb-b` (t2.nano) — todas **Running**, status checks pasados.

### Application Load Balancer

![AWS ALB report-alb activo](/.attachments/Balanceador.png)

`report-alb` activo, tipo Application, esquema Internet-facing, IPv4.

### Target Group

![AWS Target Group report-app-group](/.attachments/targetGroup.png)

`report-app-group`: HTTP:8080, tipo Instance — **2 targets healthy**, 0 unhealthy.

### Security Groups

![AWS Security Groups](/.attachments/securityGroups.png)

Capas de red: `report-trafico-ssh`, `report-trafico-lb`, `report-trafico-http`, `report-trafico-db`, `trafico-rabbit`.

---

## 5. Ejecución del experimento

### Fase 1 — Configuración JMeter

Test _Prueba ASR2-BaseLoad_: 5 000 hilos, ramp-up 600 s, 1 iteración. Cada hilo realiza un `POST /api/auth/login` con credenciales inválidas contra el ALB.

**Thread Group — 5 000 hilos, ramp-up 600 s**

![JMeter Thread Group 5000 threads](/.attachments/Baseload.png)

5 000 usuarios virtuales, arranque progresivo de 600 s, Loop Count 1, acción ante error _Continue_.

**HTTP Request — POST /api/auth/login**

![JMeter HTTP Request POST](/.attachments/Request.png)

Destino: `report-alb-….us-east-1.elb.amazonaws.com:80`  
Body: `{"username":"atacado","password":"MALAPASSWORD"}`

**Summary Report inicial — verificación de conectividad**

![JMeter Summary Report 1 muestra 278ms](/.attachments/prueba1Thread.png)

1 muestra: **Average 278 ms**, Error 100% — endpoint activo, responde `401`.

---

### Fase 2 — Activación del bloqueo

Tras 5 intentos fallidos consecutivos desde la misma IP, el backend detecta la anomalía y bloquea la IP por **300 segundos**.

**Logs instancia report-app-lb-b — secuencia 401 → 429**

![Consola Django instancia B 401 429](/.attachments/healthCheck-b.png)

**Mensaje de bloqueo en consola**

![ANOMALIA DETECTADA 5 intentos bloqueado 300s](/.attachments/Bloqueo.png)

```
ANOMALÍA DETECTADA: 5 intentos fallidos de atacado
desde 186.154.38.92. Bloqueado por 300 segundos.
```

---

### Fase 3 — Health check durante la carga

**Instancia report-app-lb-a — GET /api/auth/health → 200**

![Django logs instancia A health 200](/.attachments/healthCheck-a.png)

`GET /api/auth/health HTTP/1.1" 200 92` cada ~15 s — servicio **healthy** durante toda la prueba.

---

### Fase 4 — Resultado final: 5 000 muestras

**Summary Report — Average 245 ms · Throughput 8.3/s**

![JMeter Summary Report 5000 muestras 245ms](/.attachments/pruebaBaseLoad.png)

5 000 muestras: **Average 245 ms**, Min 174 ms, Max 5 749 ms, Std Dev 352 ms, Error 100% (esperado), Throughput **8.3/s**.

---

## 6. Análisis de resultados

| Criterio ASR1 | Evidencia obtenida | Cumple |
|:---|:---|:---:|
| **Latencia < 2 s** | Average 245 ms con 5 000 muestras (JMeter Summary Report) | ✓ |
| **Detección de anomalía** | `ANOMALÍA DETECTADA` tras 5 intentos fallidos consecutivos desde misma IP | ✓ |
| **Restricción temporal (429)** | Respuestas cambian de `401` a `429` tras el bloqueo; duración 300 s | ✓ |
| **Persistencia en `IntentoBloqueado`** | Bloqueo registrado con IP `186.154.38.92`, `activo=True`, 300 s | ✓ |
| **Disponibilidad del servicio** | `GET /api/auth/health → 200` ininterrumpido durante toda la carga | ✓ |
| **Health check ALB** | Target Group con 2 targets healthy, 0 unhealthy durante toda la prueba | ✓ |

---

## 7. Decisiones de arquitectura

**a) Balanceo y punto único de entrada**  
El ALB concentra el tráfico y permite aplicar rate limiting de forma centralizada, independientemente de cuántas instancias EC2 haya detrás.

**b) Health check del API independiente**  
El endpoint `GET /api/auth/health` es independiente del flujo de login, permitiendo verificar disponibilidad sin confundir errores `401`/`429` con caída del servicio.

**c) Modelo `IntentoBloqueado` en base de datos**  
La persistencia de bloqueos sustenta la trazabilidad y garantiza coherencia entre la respuesta HTTP y el estado en base de datos, incluso al redirigir entre instancias.

**d) Microservicios y aislamiento**  
La separación del servicio de autenticación permite desplegar, escalar y depurar el flujo de bloqueo sin afectar otros dominios del sistema.
