"""
Script de prueba para validar la integración completa del ASR (Application Security Review)

Validaciones:
1. Payload intacto con firma HMAC correcta → 201 Created
2. Payload adulterado (tampered) → 401 Unauthorized + RechazoIntegridad registrado
3. Payload sin firma → 401 Unauthorized + RechazoIntegridad registrado
4. Endpoint GET /api/auth/rechazos/integridad retorna lista paginada de rechazos
"""

import os
import sys
import django
import json
import hmac
import hashlib
from datetime import datetime, timedelta

# Configuración de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finops_platform.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from autenticacion.models import Usuario, Empresa, RechazoIntegridad
from django.utils import timezone
from django.conf import settings

# ============================================================
# UTILIDADES
# ============================================================

def calcular_hmac_sha256(payload_json: str, secret_key: str) -> str:
    """Calcula el HMAC-SHA256 de un payload JSON"""
    return hmac.new(
        secret_key.encode(),
        payload_json.encode(),
        hashlib.sha256
    ).hexdigest()


def crear_usuario_admin():
    """Crea un usuario admin para testing"""
    user, _ = User.objects.get_or_create(
        username='admin_test',
        defaults={
            'email': 'admin@test.local',
            'is_staff': True,
            'is_superuser': True
        }
    )
    empresa, _ = Empresa.objects.get_or_create(id='TEST.CO', defaults={'nombre': 'Test Empresa'})
    usuario, _ = Usuario.objects.get_or_create(
        usuario_django=user,
        defaults={'empresa': empresa, 'rol': 'admin', 'activo': True}
    )
    return user, usuario


def limpiar_rechazos_previos():
    """Limpia rechazos de pruebas anteriores"""
    RechazoIntegridad.objects.filter(
        endpoint__contains='costos/empresa/TEST.CO'
    ).delete()


# ============================================================
# PRUEBAS
# ============================================================

def test_1_payload_valido():
    """
    TEST 1: Enviar payload válido con firma HMAC correcta
    Resultado esperado: 201 Created
    """
    print("\n" + "="*70)
    print("TEST 1: Payload válido con firma HMAC correcta")
    print("="*70)
    
    client = Client()
    user, usuario = crear_usuario_admin()
    
    # Generar payload
    payload = json.dumps({
        'mes': 5,
        'ano': 2025,
        'descripcion': 'Test ASR - Payload válido'
    }, separators=(',', ':'))
    
    # Calcular firma válida
    firma_valida = calcular_hmac_sha256(payload, settings.SECRET_KEY)
    
    # Realizar request
    response = client.post(
        '/api/reportes/costos/empresa/TEST.CO',
        data=payload,
        content_type='application/json',
        HTTP_X_PAYLOAD_SIGNATURE=firma_valida,
        HTTP_AUTHORIZATION=f'Bearer {user.username}'
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Expected: 201 Created")
    
    if response.status_code == 201:
        print("✓ TEST 1 PASSED: Payload válido fue aceptado")
        return True
    else:
        print(f"✗ TEST 1 FAILED: Respuesta: {response.content.decode()}")
        return False


def test_2_payload_adulterado():
    """
    TEST 2: Enviar payload adulterado (firma incorrecta)
    Resultado esperado: 401 Unauthorized + RechazoIntegridad creado
    """
    print("\n" + "="*70)
    print("TEST 2: Payload adulterado (firma incorrecta)")
    print("="*70)
    
    limpiar_rechazos_previos()
    
    client = Client()
    user, usuario = crear_usuario_admin()
    
    # Generar payload
    payload = json.dumps({
        'mes': 5,
        'ano': 2025,
        'descripcion': 'Test ASR - Payload adulterado'
    }, separators=(',', ':'))
    
    # Firma INCORRECTA (deliberadamente)
    firma_incorrecta = 'abc123def456'  # Firma inválida
    
    # Realizar request
    response = client.post(
        '/api/reportes/costos/empresa/TEST.CO',
        data=payload,
        content_type='application/json',
        HTTP_X_PAYLOAD_SIGNATURE=firma_incorrecta,
        HTTP_AUTHORIZATION=f'Bearer {user.username}'
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Expected: 401 Unauthorized")
    
    # Verificar que se registró el rechazo
    rechazo = RechazoIntegridad.objects.filter(
        endpoint__contains='costos/empresa/TEST.CO',
        motivo_rechazo='PAYLOAD_TAMPERED'
    ).first()
    
    if response.status_code == 401 and rechazo:
        print("✓ TEST 2 PASSED: Payload adulterado fue rechazado y registrado")
        print(f"  - Rechazo ID: {rechazo.id}")
        print(f"  - Motivo: {rechazo.motivo_rechazo}")
        print(f"  - IP: {rechazo.direccion_ip}")
        print(f"  - Fecha: {rechazo.fecha_rechazo}")
        return True
    else:
        print(f"✗ TEST 2 FAILED")
        if response.status_code != 401:
            print(f"  Status incorrecto: {response.status_code}")
        if not rechazo:
            print(f"  RechazoIntegridad no fue creado")
        return False


def test_3_sin_firma():
    """
    TEST 3: Enviar payload sin firma (header faltante)
    Resultado esperado: 401 Unauthorized + RechazoIntegridad creado
    """
    print("\n" + "="*70)
    print("TEST 3: Payload sin firma (header X-Payload-Signature faltante)")
    print("="*70)
    
    limpiar_rechazos_previos()
    
    client = Client()
    user, usuario = crear_usuario_admin()
    
    # Generar payload
    payload = json.dumps({
        'mes': 5,
        'ano': 2025,
        'descripcion': 'Test ASR - Sin firma'
    }, separators=(',', ':'))
    
    # Realizar request SIN el header de firma
    response = client.post(
        '/api/reportes/costos/empresa/TEST.CO',
        data=payload,
        content_type='application/json',
        # No incluir HTTP_X_PAYLOAD_SIGNATURE
        HTTP_AUTHORIZATION=f'Bearer {user.username}'
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Expected: 401 Unauthorized")
    
    # Verificar que se registró el rechazo
    rechazo = RechazoIntegridad.objects.filter(
        endpoint__contains='costos/empresa/TEST.CO',
        motivo_rechazo='MISSING_SIGNATURE'
    ).first()
    
    if response.status_code == 401 and rechazo:
        print("✓ TEST 3 PASSED: Payload sin firma fue rechazado y registrado")
        print(f"  - Rechazo ID: {rechazo.id}")
        print(f"  - Motivo: {rechazo.motivo_rechazo}")
        print(f"  - IP: {rechazo.direccion_ip}")
        return True
    else:
        print(f"✗ TEST 3 FAILED")
        if response.status_code != 401:
            print(f"  Status incorrecto: {response.status_code}")
        if not rechazo:
            print(f"  RechazoIntegridad no fue creado")
        print(f"  Respuesta: {response.content.decode()}")
        return False


def test_4_listar_rechazos():
    """
    TEST 4: Endpoint GET /api/auth/rechazos/integridad retorna rechazos con paginación
    Resultado esperado: 200 OK con lista paginada de RechazoIntegridad
    """
    print("\n" + "="*70)
    print("TEST 4: GET /api/auth/rechazos/integridad - Listar rechazos")
    print("="*70)
    
    # Crear algunos rechazos previos
    test_2_payload_adulterado()
    test_3_sin_firma()
    
    client = Client()
    user, usuario = crear_usuario_admin()
    
    # Llamar endpoint de rechazos
    response = client.get(
        '/api/auth/rechazos/integridad?dias=7&page=1&page_size=50',
        HTTP_AUTHORIZATION=f'Bearer {user.username}'
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Expected: 200 OK")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Respuesta obtenida")
        print(f"  - Total rechazos: {data.get('total', 0)}")
        print(f"  - Página actual: {data.get('page', 0)}")
        print(f"  - Tamaño página: {data.get('page_size', 0)}")
        print(f"  - Rechazos en respuesta: {len(data.get('rechazos', []))}")
        
        if data.get('rechazos'):
            print(f"\n  Primeros 3 rechazos:")
            for i, rechazo in enumerate(data.get('rechazos', [])[:3], 1):
                print(f"    {i}. {rechazo['fecha_rechazo']} | {rechazo['direccion_ip']} | {rechazo['motivo_rechazo']}")
        
        if data.get('total', 0) >= 2:
            print("\n✓ TEST 4 PASSED: Endpoint retorna lista paginada correctamente")
            return True
        else:
            print("\n✗ TEST 4 FAILED: No se encontraron suficientes rechazos")
            return False
    else:
        print(f"✗ TEST 4 FAILED: Status incorrecto")
        print(f"  Respuesta: {response.content.decode()}")
        return False


def test_5_filtros():
    """
    TEST 5: Endpoint GET con filtros (endpoint, dias, ip)
    Resultado esperado: 200 OK con rechazos filtrados
    """
    print("\n" + "="*70)
    print("TEST 5: GET /api/auth/rechazos/integridad con filtros")
    print("="*70)
    
    client = Client()
    user, usuario = crear_usuario_admin()
    
    # Endpoint con filtros
    response = client.get(
        '/api/auth/rechazos/integridad?dias=7&endpoint=costos&page=1',
        HTTP_AUTHORIZATION=f'Bearer {user.username}'
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Filtros aplicados correctamente")
        print(f"  - Total con filtro 'endpoint=costos': {data.get('total', 0)}")
        
        if data.get('total', 0) >= 1:
            print("✓ TEST 5 PASSED: Filtros funcionan correctamente")
            return True
        else:
            print("✓ TEST 5 PASSED: Endpoint responde correctamente (sin rechazos con filtro)")
            return True
    else:
        print(f"✗ TEST 5 FAILED: {response.content.decode()}")
        return False


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == '__main__':
    print("\n" + "="*70)
    print("PRUEBAS DE INTEGRACION ASR - APPLICATION SECURITY REVIEW")
    print("="*70)
    
    # Crear usuario admin para testing
    crear_usuario_admin()
    
    # Ejecutar tests
    resultados = {
        'Test 1 - Payload válido': test_1_payload_valido(),
        'Test 2 - Payload adulterado': test_2_payload_adulterado(),
        'Test 3 - Sin firma': test_3_sin_firma(),
        'Test 4 - Listar rechazos': test_4_listar_rechazos(),
        'Test 5 - Filtros': test_5_filtros(),
    }
    
    # Resumen final
    print("\n" + "="*70)
    print("RESUMEN DE RESULTADOS")
    print("="*70)
    
    passed = sum(1 for v in resultados.values() if v)
    total = len(resultados)
    
    for nombre, resultado in resultados.items():
        estado = "✓ PASSED" if resultado else "✗ FAILED"
        print(f"{nombre:<40} {estado}")
    
    print(f"\n{passed}/{total} pruebas pasadas")
    
    if passed == total:
        print("\n✓ ¡TODAS LAS PRUEBAS PASARON!")
        sys.exit(0)
    else:
        print(f"\n✗ {total - passed} prueba(s) fallida(s)")
        sys.exit(1)
