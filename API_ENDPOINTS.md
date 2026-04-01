# API Endpoints Documentación

## Servicio de Autenticación (Puerto 8000)

### 1. Registro de Usuario
```
POST /api/auth/register
Content-Type: application/json

Request:
{
    "username": "usuario@example.com",
    "email": "usuario@example.com",
    "password": "SecurePassword123!",
    "first_name": "Juan",
    "last_name": "Pérez",
    "empresa": "BITE.CO"
}

Response (201 Created):
{
    "mensaje": "Usuario registrado exitosamente",
    "usuario": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "username": "usuario@example.com",
        "email": "usuario@example.com",
        "empresa": "BITE.CO"
    }
}
```

### 2. Login
```
POST /api/auth/login
Content-Type: application/json

Request:
{
    "username": "usuario@example.com",
    "password": "SecurePassword123!"
}

Response (200 OK):
{
    "mensaje": "Login exitoso",
    "tokens": {
        "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    },
    "usuario": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "username": "usuario@example.com",
        "email": "usuario@example.com",
        "rol": "usuario",
        "empresa": "BITE.CO"
    }
}
```

### 3. Obtener Usuario Actual
```
GET /api/auth/me
Authorization: Bearer <access_token>

Response (200 OK):
{
    "usuario": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "username": "usuario@example.com",
        "email": "usuario@example.com",
        "first_name": "Juan",
        "last_name": "Pérez",
        "empresa": "BITE.CO",
        "rol": "usuario",
        "activo": true,
        "bloqueado": false
    },
    "permisos": ["view_reportes", "create_reportes"]
}
```

### 4. Refrescar Token
```
POST /api/auth/refresh
Authorization: Bearer <access_token>
Content-Type: application/json

Request:
{
    "refresh": "<refresh_token>"
}

Response (200 OK):
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

### 5. Logout
```
POST /api/auth/logout
Authorization: Bearer <access_token>

Response (200 OK):
{
    "mensaje": "Logout exitoso"
}
```

### 6. Historial de Acceso (Auditoría)
```
GET /api/auth/audit/historial?dias=7
Authorization: Bearer <access_token>

Response (200 OK):
{
    "usuario": "usuario@example.com",
    "historial": [
        {
            "id": "550e8400-e29b-41d4-a716-446655440001",
            "tipo_evento": "login_exitoso",
            "direccion_ip": "192.168.1.100",
            "fecha_evento": "2024-01-15T10:30:00Z",
            "user_agent": "Mozilla/5.0..."
        }
    ],
    "total": 15
}
```

### 7. Health Check
```
GET /api/health

Response (200 OK):
{
    "status": "healthy",
    "service": "auth_service",
    "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## Servicio de Reportes (Puerto 8001)

### 1. Obtener Reporte Mensual
```
GET /api/reportes/mensual?empresa_id=550e8400-e29b-41d4-a716-446655440000&año=2024&mes=1
Authorization: Bearer <access_token>

Response (200 OK):
{
    "reporte": {
        "empresa_id": "550e8400-e29b-41d4-a716-446655440000",
        "periodo": "2024/01",
        "costo_total": "45230.50",
        "costo_aws": "30150.75",
        "costo_gcp": "15079.75",
        "numero_recursos": 245,
        "numero_proyectos": 12,
        "anomalias_detectadas": 5,
        "ahorro_potencial": "8500.00",
        "detalles_por_servicio": {
            "EC2": "15000.00",
            "RDS": "8500.00",
            "S3": "3200.00"
        },
        "detalles_por_proyecto": {
            "Proyecto-A": "12000.00",
            "Proyecto-B": "33230.50"
        },
        "detalles_por_region": {
            "us-east-1": "28000.00",
            "eu-west-1": "17230.50"
        }
    },
    "asr_metrics": {
        "tiempo_generacion_ms": 45,
        "tiempo_total_ms": 58,
        "cumple_sla": true
    }
}
```

### 2. Reporte por Proyecto
```
GET /api/reportes/proyecto?empresa_id=550e8400-e29b-41d4-a716-446655440000&proyecto=Proyecto-A&año=2024&mes=1
Authorization: Bearer <access_token>

Response (200 OK):
{
    "proyecto": {
        "empresa_id": "550e8400-e29b-41d4-a716-446655440000",
        "nombre": "Proyecto-A",
        "periodo": "2024/01",
        "costo_total": "12000.00",
        "numero_recursos": 45,
        "servicios_utilizados": ["EC2", "RDS", "S3"],
        "tendencia_mes_anterior": 5.5
    }
}
```

### 3. Listar Consumo de Recursos
```
GET /api/reportes/consumo?empresa_id=550e8400-e29b-41d4-a716-446655440000&fecha_inicio=2024-01-01&fecha_fin=2024-01-31&proveedor=AWS&servicio=EC2
Authorization: Bearer <access_token>

Response (200 OK):
{
    "resultados": [
        {
            "id": "550e8400-e29b-41d4-a716-446655440002",
            "proveedor": "AWS",
            "cuenta": "123456789012",
            "proyecto": "Proyecto-A",
            "servicio": "EC2",
            "region": "us-east-1",
            "costo_mensual": "5000.00",
            "unidades_consumidas": "730",
            "unidad_medida": "vCPU-hour",
            "fecha_inicio": "2024-01-01",
            "fecha_fin": "2024-01-31"
        }
    ],
    "paginacion": {
        "page": 1,
        "page_size": 50,
        "total": 125,
        "total_pages": 3
    }
}
```

### 4. Análisis de Optimización
```
GET /api/reportes/analisis/optimizacion?empresa_id=550e8400-e29b-41d4-a716-446655440000
Authorization: Bearer <access_token>

Response (200 OK) - Si < 2 segundos:
{
    "analisis": {
        "empresa_id": "550e8400-e29b-41d4-a716-446655440000",
        "oportunidades_detectadas": 8,
        "ahorro_potencial_mensual": "8500.00",
        "detalles": [
            {
                "id": "550e8400-e29b-41d4-a716-446655440003",
                "tipo": "instancia_inactiva",
                "recurso": "i-0a1b2c3d4e5f6g7h8",
                "proyecto": "Proyecto-B",
                "ahorro_potencial": "500.00",
                "recomendacion": "Terminar instancia inactiva para ahorrar costos"
            }
        ]
    },
    "asr_metrics": {
        "tiempo_ejecucion_ms": 1850,
        "ejecutado_background": false
    }
}

Response (202 Accepted) - Si > 2 segundos:
{
    "mensaje": "Análisis en progreso, se enviará notificación por correo",
    "empresa_id": "550e8400-e29b-41d4-a716-446655440000",
    "tiempo_estimado_ms": 3500,
    "asr": {
        "umbral_background": 2000,
        "excedido": true
    }
}
```

### 5. Detectar Tendencias
```
GET /api/reportes/tendencias?empresa_id=550e8400-e29b-41d4-a716-446655440000
Authorization: Bearer <access_token>

Response (200 OK):
{
    "tendencias": [
        {
            "id": "550e8400-e29b-41d4-a716-446655440004",
            "tipo": "spike_costo_repentino",
            "descripcion": "Incremento de 35.50% en costos cloud",
            "periodo": "2024-01-01 a 2024-01-15",
            "impacto": "5000.00",
            "severidad": "alto",
            "fecha_deteccion": "2024-01-15T10:30:00Z"
        }
    ],
    "total": 2
}
```

### 6. Historial de Reportes
```
GET /api/reportes/historial?empresa_id=550e8400-e29b-41d4-a716-446655440000
Authorization: Bearer <access_token>

Response (200 OK):
{
    "historial": [
        {
            "id": "550e8400-e29b-41d4-a716-446655440005",
            "tipo": "reporte_mensual",
            "tiempo_ejecucion_ms": 58,
            "ejecutado_background": false,
            "estado": "exitoso",
            "fecha": "2024-01-15T10:30:00Z",
            "mensaje_error": null
        }
    ],
    "total": 15
}
```

### 7. Health Check
```
GET /api/health

Response (200 OK):
{
    "status": "healthy",
    "service": "reportes_service",
    "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## Códigos de Error HTTP

- `200 OK`: Operación exitosa
- `201 Created`: Recurso creado exitosamente
- `202 Accepted`: Solicitud aceptada (procesamiento en background)
- `400 Bad Request`: Parámetros inválidos
- `401 Unauthorized`: Token inválido o expirado
- `403 Forbidden`: Usuario no tiene permisos
- `409 Conflict`: El recurso ya existe
- `429 Too Many Requests`: Bloqueado por múltiples intentos fallidos
- `500 Internal Server Error`: Error del servidor

---

## Ejemplos cURL

### Registro
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "usuario@example.com",
    "email": "usuario@example.com",
    "password": "SecurePassword123!",
    "empresa": "BITE.CO"
  }'
```

### Login
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "usuario@example.com",
    "password": "SecurePassword123!"
  }'
```

### Obtener Reporte
```bash
curl -X GET "http://localhost:8001/api/reportes/mensual?empresa_id=550e8400-e29b-41d4-a716-446655440000&año=2024&mes=1" \
  -H "Authorization: Bearer <access_token>"
```

### Análisis de Optimización
```bash
curl -X GET "http://localhost:8001/api/reportes/analisis/optimizacion?empresa_id=550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer <access_token>"
```
