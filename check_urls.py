#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finops_platform.settings')
django.setup()

from django.urls import get_resolver

resolver = get_resolver()

# Obtener todas las URLs
patterns = []

def get_all_urls(urlpatterns, prefix=''):
    for pattern in urlpatterns:
        if hasattr(pattern, 'url_patterns'):
            # Es un include()
            get_all_urls(pattern.url_patterns, prefix + str(pattern.pattern))
        else:
            full_path = prefix + str(pattern.pattern)
            patterns.append(full_path)

get_all_urls(resolver.url_patterns)

# Buscar rutas de login
login_routes = [p for p in patterns if 'login' in p.lower() or 'auth' in p.lower()]
print("=== Rutas de Autenticación ===")
for route in sorted(login_routes):
    print(f"  {route}")

print("\n=== Primeras 40 rutas ===")
for route in sorted(patterns)[:40]:
    print(f"  {route}")
