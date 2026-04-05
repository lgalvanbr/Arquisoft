# DEBUGGING: EC2 User Data Script Execution

## Problema Identificado

Las instancias EC2 no están:
- Creando el directorio `/apps`
- Clonando el repositorio Arquisoft
- Ejecutando el script user_data

## Causas Comunes

1. **Script no se ejecuta**: Sin `base64encode()`, AWS no interpreta el script correctamente
2. **Permisos insuficientes**: `mkdir -p /apps` sin `sudo` falla (EC2 ejecuta como root inicialmente, pero luego es ubuntu)
3. **Variables de Terraform no se interpolan**: Indentación incorrecta en heredoc puede causar esto
4. **Gunicorn no arranca**: Porque `/apps/Arquisoft` no existe

## Soluciones Aplicadas en Nuevo deployment.tf

✅ **user_data = base64encode(<<-EOT)** - Asegurar que AWS ejecute el script
✅ **sudo mkdir -p /apps** - Permisos correctos para crear directorio
✅ **sudo git clone** - Permisos correctos para clonar repo
✅ **Sin indentación en bash** - Permitir que variables de Terraform se interpolen correctamente

## Cómo Verificar en EC2

### 1. SSH a una instancia
```bash
ssh -i <tu-key>.pem ubuntu@<instance-public-ip>
```

### 2. Revisar si el script ejecutó
```bash
# Ver logs del user_data
sudo cat /var/log/cloud-init-output.log
sudo cat /var/log/cloud-init.log

# Verificar si /apps existe
ls -la /apps
ls -la /apps/Arquisoft

# Revisar si Gunicorn está corriendo
sudo systemctl status gunicorn
sudo journalctl -u gunicorn -n 50
```

### 3. Si /apps NO existe
```bash
# Crear manualmente para testing
sudo mkdir -p /apps
cd /apps
sudo git clone https://github.com/AriadnaVargas/Arquisoft.git
cd Arquisoft
sudo chown -R ubuntu:ubuntu /apps
```

### 4. Si Gunicorn no arranca
```bash
# Ver error exacto
sudo systemctl status gunicorn

# Ver logs detallados
sudo journalctl -u gunicorn -xe

# Intentar arrancar manualmente
cd /apps/Arquisoft
sudo python3 -m gunicorn --workers 4 --bind 0.0.0.0:8080 finops_platform.wsgi:application
```

### 5. Verificar que Django funciona
```bash
cd /apps/Arquisoft
python3 -c "import django; print(django.get_version())"
python3 manage.py shell -c "print('Django OK')"
```

## Pasos para Verificar Despliegue

```bash
# 1. Desplegar con Terraform
cd terraform
terraform init
terraform plan  # Revisar cambios
terraform apply # Desplegar (espera 10-15 min)

# 2. Obtener IPs de instancias
terraform output app_instances_public_ips

# 3. SSH a la primera instancia
ssh -i <key>.pem ubuntu@<ip-from-step-2>

# 4. Verificar despliegue
cat /var/log/cloud-init-output.log  # Buscar errores
ls -la /apps/Arquisoft              # ¿Existe el repo?
sudo systemctl status gunicorn      # ¿Gunicorn corre?
curl localhost:8080/api/reportes/health  # ¿Responde?

# 5. Si todo está bien
# El ALB debería mostrar todas las instancias como "healthy"
# Test con JMeter contra: http://<ALB-DNS>/api/reportes/proyecto
```

## Si aún no funciona

### Opción A: Debugging detallado
```bash
# Ver EXACTAMENTE qué pasó en el user_data
tail -f /var/log/cloud-init-output.log

# Ejecutar el script manualmente paso a paso
#!/bin/bash
set -x  # Debug mode
export DATABASE_HOST=<db-private-ip>
sudo mkdir -p /apps
cd /apps
sudo git clone https://github.com/AriadnaVargas/Arquisoft.git
cd Arquisoft
sudo pip3 install --upgrade pip --break-system-packages
sudo pip3 install -r requirements.txt --break-system-packages
```

### Opción B: Verificar terraform apply output
```bash
terraform apply -auto-approve 2>&1 | tee terraform-apply.log
# Buscar por "error" en el log
```

### Opción C: Revisar security groups
```bash
# ¿Las instancias pueden hacer outbound a GitHub?
ssh -i <key>.pem ubuntu@<instance-ip>
ping -c 1 github.com
curl -I https://github.com
```

## Checklist Final

- [ ] `/apps` existe y es accesible
- [ ] `/apps/Arquisoft` existe (repositorio clonado)
- [ ] `sudo systemctl status gunicorn` dice "active (running)"
- [ ] `curl localhost:8080/api/reportes/health` retorna 200 OK
- [ ] ALB health check muestra todas las instancias "healthy"
- [ ] JMeter load test funciona sin errores de conexión
