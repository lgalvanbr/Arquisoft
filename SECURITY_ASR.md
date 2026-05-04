# Funcionalidades de Seguridad - ASR Integridad y Confidencialidad

## 📋 Descripción General

El sistema implementa dos requisitos críticos de seguridad según el laboratorio ISIS2503:

### 1️⃣ **ASR Integridad: Detección de Manipulación de Payloads**
**Requisito:**
> Yo como administrador, dado que el sistema está en operación normal, cuando un atacante haga una petición de reporte de costos enviando un mensaje adulterado, quiero que el sistema detecte la manipulación. Esto debe suceder de forma que el 100% de esos mensajes son rechazados con error no autorizado, ningún dato es persistido en la base de datos, y el rechazo queda registrado en el log con fecha, IP de origen y motivo.

**Implementación:**
- Archivo: `reportes/validators.py`
- Decorador: `@validate_payload_integrity`
- Mecanismo: **HMAC-SHA256** (firma criptográfica del payload)

**Flujo:**
```
1. Cliente calcula HMAC-SHA256(body, SECRET_KEY)
2. Cliente envía header: X-Payload-Signature: <firma>
3. Server recibe request
4. Decorador @validate_payload_integrity intercepta
5. Server recalcula firma esperada
6. Compara con timing-safe comparison (HMAC)
   ✓ Si coinciden → request continúa
   ✗ Si NO coinciden:
      → Response 401 Unauthorized
      → Cero datos persistidos
      → Registro en tabla RechazoIntegridad con:
         - fecha_rechazo (timestamp)
         - direccion_ip (IP origen del atacante)
         - motivo_rechazo (ej: "Firma inválida")
         - endpoint (ruta atacada)
         - payload_recibido (datos para forensics)
```

**Uso en endpoints:**
```python
@require_http_methods(["POST"])
@validate_payload_integrity  # ← Este decorador valida firma
def crear_reporte_costos(request, empresa_id):
    # Si llegó aquí, payload está íntegro ✓
    ...
```

**Ejemplo: Cliente enviando firma válida**
```bash
curl -X POST http://localhost:8080/api/reportes/costos/crear/BITE.CO \
  -H "X-Payload-Signature: abc123def456..." \
  -H "Content-Type: application/json" \
  -d '{"mes": 5, "ano": 2025}'
```

**Ejemplo: Cliente sin firma (rechazado)**
```bash
curl -X POST http://localhost:8080/api/reportes/costos/crear/BITE.CO \
  -H "Content-Type: application/json" \
  -d '{"mes": 5, "ano": 2025}'

# Response:
# 401 Unauthorized
# {
#   "error": "No autorizado",
#   "detail": "Falta header de integridad: X-Payload-Signature"
# }

# Base de datos:
# INSERT INTO rechazos_integridad VALUES (
#   fecha_rechazo='2025-05-04 12:34:56',
#   direccion_ip='192.168.1.100',
#   endpoint='/api/reportes/costos/crear/BITE.CO',
#   motivo_rechazo='MISSING_SIGNATURE'
# )
```

---

### 2️⃣ **ASR Confidencialidad: Control de Acceso por Empresa**
**Requisito:**
> Yo como administrador autenticado, dado que el sistema está en operación normal, cuando un atacante con credenciales de la Empresa A hace una petición de reporte de costos manipulando el atributo company_id para solicitar datos de Empresa B, quiero que el sistema detecte el acceso no autorizado. Esto debe suceder de forma que el sistema responde con un error de no autorizado, no incluye ningún dato de Empresa B en la respuesta, y registra el intento en el log de auditoría con fecha, IP de origen e identificador del token usado.

**Implementación:**
- Archivo: `reportes/permissions.py`
- Decorador: `@check_company_access`
- Mecanismo: Validación de empresa vs. token Auth0

**Flujo:**
```
1. Usuario autenticado hace request con empresa_id en URL
   GET /api/reportes/costos/empresa/EMPRESA_B
   
2. Decorador @check_company_access intercepta
   
3. Extrae empresa_solicitada de:
   - URL parameter (empresa_id)
   - Query parameter (?empresa_id=)
   - Request body
   
4. Obtiene empresa_usuario del token Auth0:
   - social_user.extra_data['https://finops-api/empresa']
   
5. Compara:
   ✓ Si empresa_solicitada == empresa_usuario
      → request continúa, sin restricciones
      
   ✗ Si empresa_solicitada != empresa_usuario
      → Response 403 Forbidden
      → CERO datos retornados (ni de empresa A)
      → Registro en tabla IntentoAccesoNoAutorizado con:
         - usuario (quién lo intentó)
         - empresa_solicitada_id (EMPRESA_B - la que intentó acceder)
         - empresa_autorizada_id (EMPRESA_A - la suya)
         - endpoint (ruta atacada)
         - direccion_ip (IP origen)
         - token_identifier (sub del token Auth0)
         - fecha_intento (timestamp)
```

**Uso en endpoints:**
```python
@require_authentication  # ← Requiere usuario autenticado
@check_company_access   # ← Valida que accede a su empresa
def obtener_reporte_costos(request, empresa_id):
    # Si llegó aquí:
    # - Usuario está autenticado ✓
    # - usuario.company == empresa_id ✓
    # - Seguro retornar datos de empresa_id
    ...
```

**Ejemplo: Acceso autorizado (usuario BITE.CO accede BITE.CO)**
```bash
# Token contiene: empresa='BITE.CO'
curl -X GET http://localhost:8080/api/reportes/costos/empresa/BITE.CO \
  -H "Authorization: Bearer <token>"

# Response: 200 OK
# {
#   "reporte": {
#     "id": "rpt_BITE.CO_2025_05",
#     "costo_total": 2345.67,
#     ...
#   }
# }

# Base de datos:
# ✗ CERO registros en intentos_acceso_no_autorizado
# ✓ Registro en audit_log con action='ACCESO_EXITOSO'
```

**Ejemplo: Acceso no autorizado (usuario EMPRESA_A intenta acceder EMPRESA_B)**
```bash
# Token contiene: empresa='EMPRESA_A'
curl -X GET http://localhost:8080/api/reportes/costos/empresa/EMPRESA_B \
  -H "Authorization: Bearer <token>"

# Response: 403 Forbidden
# {
#   "error": "Acceso Denegado",
#   "detail": "No tienes permiso para acceder a esta empresa"
# }

# Base de datos:
# INSERT INTO intentos_acceso_no_autorizado VALUES (
#   usuario='usuario_A',
#   empresa_solicitada_id='EMPRESA_B',
#   empresa_autorizada_id='EMPRESA_A',
#   endpoint='/api/reportes/costos/empresa/EMPRESA_B',
#   direccion_ip='192.168.1.101',
#   token_identifier='auth0|5f9c4ab08e5...',  ← Token ID
#   fecha_intento='2025-05-04 12:35:45'
# )

# CERO datos de EMPRESA_B retornados ✓
```

---

## 🗄️ Modelos de Base de Datos

### `RechazoIntegridad` (Integridad)
```sql
CREATE TABLE rechazos_integridad (
    id UUID PRIMARY KEY,
    direccion_ip VARCHAR(45) INDEXED,          -- IP del atacante
    endpoint VARCHAR(255) INDEXED,              -- Endpoint atacado
    motivo_rechazo VARCHAR(500),                -- MISSING_SIGNATURE, PAYLOAD_TAMPERED, etc.
    payload_recibido JSON,                      -- Datos recibidos (para forensics)
    fecha_rechazo TIMESTAMP INDEXED,            -- Cuándo ocurrió
    user_agent TEXT                             -- Browser/client info
);
```

**Queries útiles para administrador:**
```sql
-- Ataques en último hora
SELECT COUNT(*), direccion_ip, motivo_rechazo
FROM rechazos_integridad
WHERE fecha_rechazo > NOW() - INTERVAL '1 hour'
GROUP BY direccion_ip, motivo_rechazo;

-- IPs más agresivas
SELECT direccion_ip, COUNT(*) as intentos
FROM rechazos_integridad
WHERE fecha_rechazo > NOW() - INTERVAL '24 hours'
GROUP BY direccion_ip
ORDER BY intentos DESC
LIMIT 10;
```

### `IntentoAccesoNoAutorizado` (Confidencialidad)
```sql
CREATE TABLE intentos_acceso_no_autorizado (
    id UUID PRIMARY KEY,
    usuario_id INTEGER REFERENCES usuarios(id),
    empresa_solicitada_id VARCHAR(100),         -- EMPRESA_B (target del ataque)
    empresa_autorizada_id VARCHAR(100),         -- EMPRESA_A (empresa del usuario)
    endpoint VARCHAR(255),                      -- Ruta atacada
    direccion_ip VARCHAR(45) INDEXED,           -- IP del atacante
    token_identifier VARCHAR(255),              -- Auth0 token sub claim
    fecha_intento TIMESTAMP INDEXED             -- Cuándo ocurrió
);
```

**Queries útiles para administrador:**
```sql
-- Intentos de acceso no autorizado en última hora
SELECT usuario.username, intento.empresa_solicitada_id, intento.direccion_ip
FROM intentos_acceso_no_autorizado intento
JOIN usuarios usuario ON intento.usuario_id = usuario.id
WHERE intento.fecha_intento > NOW() - INTERVAL '1 hour'
ORDER BY intento.fecha_intento DESC;

-- Usuarios sospechosos (múltiples intentos)
SELECT usuario.username, COUNT(*) as intentos
FROM intentos_acceso_no_autorizado intento
JOIN usuarios usuario ON intento.usuario_id = usuario.id
WHERE intento.fecha_intento > NOW() - INTERVAL '24 hours'
GROUP BY usuario.username
HAVING COUNT(*) > 3
ORDER BY intentos DESC;

-- Tokens comprometidos (múltiples intentos desde mismo token)
SELECT token_identifier, COUNT(*) as intentos
FROM intentos_acceso_no_autorizado
WHERE fecha_intento > NOW() - INTERVAL '24 hours'
GROUP BY token_identifier
HAVING COUNT(*) > 5;
```

---

## 🔧 Middleware de Auditoría

**Archivo:** `autenticacion/middleware.py`

Registra automáticamente en tabla `audit_log` todos los requests críticos:
- Errores 401/403 en endpoints `/api/reportes/` y `/api/auth/me`
- Accesos exitosos (200) en endpoints críticos

```python
class AuditLoggingMiddleware:
    # Endpoints monitoreados
    CRITICAL_ENDPOINTS = [
        '/api/reportes/',
        '/api/auth/me',
    ]
    
    # Acciones registradas
    ACCESO_NO_AUTORIZADO  # 403
    INTENTO_MANIPULACION  # 401
    ACCESO_EXITOSO        # 200
```

**Tabla audit_log:**
```sql
CREATE TABLE audit_log (
    id UUID PRIMARY KEY,
    user_id INTEGER REFERENCES auth_user(id),
    action VARCHAR(100),                    -- ACCESO_NO_AUTORIZADO, INTENTO_MANIPULACION, etc.
    resource VARCHAR(255),                  -- Endpoint
    method VARCHAR(10),                     -- GET, POST, etc.
    ip_address VARCHAR(45) INDEXED,         -- IP cliente
    status_code INTEGER,                    -- 200, 401, 403
    request_data JSON,                      -- Query params, etc.
    token_id VARCHAR(255),                  -- Auth0 token sub
    timestamp TIMESTAMP INDEXED             -- Cuándo ocurrió
);
```

---

## 📝 Decoradores Disponibles

### Para Integridad:
```python
from reportes.validators import (
    validate_payload_integrity,   # Valida HMAC-SHA256
    validate_report_request       # Valida formato empresa_id
)

@validate_payload_integrity
@validate_report_request
def mi_endpoint(request):
    pass
```

### Para Confidencialidad:
```python
from reportes.permissions import (
    require_authentication,       # Requiere usuario logueado
    check_company_access,         # Valida empresa
    check_admin_role              # Requiere admin
)

@require_authentication
@check_company_access
def mi_endpoint(request, empresa_id):
    pass
```

---

## ✅ Checklist de Cumplimiento

### ASR Integridad ✓
- [x] 100% de payloads adulterados son rechazados (401)
- [x] HMAC-SHA256 previene modificación en tránsito
- [x] Cero datos persistidos en intentos fallidos
- [x] Log con fecha, IP, motivo en tabla `rechazos_integridad`
- [x] Timing-safe comparison (no vulnerable a timing attacks)

### ASR Confidencialidad ✓
- [x] Acceso no autorizado devuelve 403 (no 200)
- [x] CERO datos retornados en respuesta
- [x] Log con fecha, IP, token_id en tabla `intentos_acceso_no_autorizado`
- [x] Validación contra empresa del token Auth0
- [x] Segregación de datos por empresa garantizada

---

## 🚀 Despliegue & Testing

### En desarrollo:
```bash
python manage.py migrate  # Crea tablas de auditoría

# Test ASR Integridad
curl -X POST http://localhost:8080/api/reportes/costos/crear/BITE.CO \
  -H "Content-Type: application/json" \
  -d '{"mes": 5, "ano": 2025}'
# Response: 401 (sin firma)

# Test ASR Confidencialidad
curl -X GET http://localhost:8080/api/reportes/costos/empresa/OTRA_EMPRESA \
  -H "Authorization: Bearer <token_EMPRESA_A>"
# Response: 403 (empresa mismatch)
```

### En producción:
```sql
-- Monitoreo de ataques en tiempo real
SELECT action, COUNT(*) FROM audit_log
WHERE timestamp > NOW() - INTERVAL '5 minutes'
GROUP BY action;

-- Alertas sobre IPs maliciosas
SELECT ip_address, COUNT(*) FROM rechazos_integridad
WHERE fecha_rechazo > NOW() - INTERVAL '1 hour'
GROUP BY ip_address
HAVING COUNT(*) > 10;
```
