# Terraform Deployment - Arquisoft FinOps Load Balancer

## Descripción General

Este directorio contiene la configuración de Terraform para desplegar la infraestructura de **Arquisoft FinOps** en AWS con un **Application Load Balancer (ALB)** que distribuye el tráfico entre múltiples instancias EC2.

## Arquitectura Desplegada

```
Internet (HTTP:80)
    |
[Application Load Balancer - report-alb]
    |
[Target Group - report-app-group]
    ├─ report-app-lb-a (EC2, puerto 8080)
    └─ report-app-lb-b (EC2, puerto 8080)
         |
    [PostgreSQL Database - report-db]
```

## Componentes

### 1. Security Groups (4)
- **report-trafico-ssh**: Puerto 22 - Acceso SSH
- **report-trafico-db**: Puerto 5432 - PostgreSQL
- **report-trafico-http**: Puerto 8080 - Aplicación Django
- **report-trafico-lb**: Puerto 80 - Load Balancer

### 2. EC2 Instances (3)

#### Base de Datos
- **Nombre**: report-db
- **Tipo**: t3.micro
- **SO**: Ubuntu 24.04 LTS
- **Software**: PostgreSQL 16
- **Credenciales**:
  - Usuario: report_user
  - Contraseña: isis2503
  - Base de datos: monitoring_db

#### Aplicación
- **Nombres**: report-app-lb-a, report-app-lb-b
- **Tipo**: t2.micro
- **SO**: Ubuntu 24.04 LTS
- **Software**: Python 3, Django, Arquisoft FinOps
- **Puerto**: 8080
- **Rama**: main

### 3. Load Balancer
- **Nombre**: report-alb
- **Tipo**: Application Load Balancer (ALB)
- **Protocolo**: HTTP (puerto 80)
- **Balanceo**: Round-Robin
- **Ubicación**: Internet-facing

### 4. Target Group
- **Nombre**: report-app-group
- **Puerto**: 8080
- **Protocolo**: HTTP
- **Health Check**: /api/reportes/health (cada 30s)
- **Balanceo**: Round-Robin

## Preparación

### 1. Instalar Terraform

cd terraform
sh ./install_terraform.sh

Este script instalará Terraform usando tfenv (Terraform Version Manager).

### 2. Verificar Instalación

terraform --version

## Despliegue

### 1. Inicializar Terraform

terraform init

Esto descargará los providers necesarios de AWS.

### 2. Ver Plan de Despliegue

terraform plan

Revisa los recursos que se van a crear. Busca errores o configuraciones inesperadas.

### 3. Aplicar Configuración

terraform apply

Se te pedirá confirmación. Escribe yes para proceder.

Tiempo estimado: 5-10 minutos

### 4. Obtener Outputs

terraform output

O valores específicos:

terraform output access_url
terraform output alb_dns_name
terraform output database_public_ip
terraform output app_instances_public_ips

## Outputs Disponibles

- alb_dns_name: DNS del Application Load Balancer
- access_url: URL completa (http://[ALB_DNS])
- alb_arn: ARN del ALB
- target_group_arn: ARN del Target Group
- database_public_ip: IP pública de la BD
- database_private_ip: IP privada de la BD
- app_instances_public_ips: IPs públicas de las instancias app (a, b)
- app_instances_private_ips: IPs privadas de las instancias app (a, b)

## Destruir Infraestructura

ADVERTENCIA: Esto eliminará todos los recursos creados

terraform destroy

Escribe yes para confirmar.

## Troubleshooting

### Error: Load balancer not reachable
- Verifica que /api/reportes/health esté disponible en puerto 8080
- Revisa security groups

### Las instancias app no se conectan a la BD
- Verifica que DATABASE_HOST esté configurada en /etc/environment
- Revisa que el security group de BD permita conexiones desde las app instances
