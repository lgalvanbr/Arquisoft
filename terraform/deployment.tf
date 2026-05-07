# ***************** Universidad de los Andes ***********************
# ****** Departamento de Ingeniería de Sistemas y Computación ******
# ********** Arquitectura y diseño de Software - ISIS2503 **********
#
# Infraestructura para laboratorio de Circuit Breaker - Arquisoft FinOps
# Kong como Load Balancer + Circuit Breaker (sin ALB)
# ==========================================

# ============================================================
# Variables
# ============================================================
variable "key_name" {
  description = "Nombre del Key Pair en AWS"
  type        = string
  default     = "finops-key"
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "instance_type_app" {
  type    = string
  default = "t2.nano"
}

variable "instance_type_kong" {
  type    = string
  default = "t2.micro"
}

variable "instance_type_db" {
  type    = string
  default = "t3.micro"
}

variable "project_prefix" {
  type    = string
  default = "cbd"
}

locals {
  common_tags = {
    Project     = "FinOps-CircuitBreaker"
    Environment = "lab"
  }
}

# ============================================================
# Provider
# ============================================================
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

# ============================================================
# AMI Ubuntu 24.04
# ============================================================
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# ============================================================
# Security Groups
# ============================================================

# SSH - acceso administrativo
resource "aws_security_group" "traffic_ssh" {
  name        = "${var.project_prefix}-traffic-ssh"
  description = "SSH access"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, { Name = "${var.project_prefix}-traffic-ssh" })
}

# App Django - puerto 8080
resource "aws_security_group" "traffic_django" {
  name        = "${var.project_prefix}-traffic-django"
  description = "Django app traffic on port 8080"

  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, { Name = "${var.project_prefix}-traffic-django" })
}

# Base de datos PostgreSQL - puerto 5432
resource "aws_security_group" "traffic_db" {
  name        = "${var.project_prefix}-traffic-db"
  description = "PostgreSQL traffic on port 5432"

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, { Name = "${var.project_prefix}-traffic-db" })
}

# Kong - puertos 8000 (proxy) y 8001 (admin API)
resource "aws_security_group" "traffic_kong" {
  name        = "${var.project_prefix}-traffic-kong"
  description = "Kong Gateway proxy and admin ports"

  ingress {
    description = "Kong proxy - punto de entrada del sistema"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Kong admin API - monitoreo del circuit breaker"
    from_port   = 8001
    to_port     = 8001
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, { Name = "${var.project_prefix}-traffic-kong" })
}

# ============================================================
# Base de datos PostgreSQL
# ============================================================
resource "aws_instance" "database" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type_db
  key_name                    = var.key_name
  associate_public_ip_address = true
  vpc_security_group_ids = [
    aws_security_group.traffic_db.id,
    aws_security_group.traffic_ssh.id
  ]

  user_data = <<-EOT
    #!/bin/bash
    sudo apt-get update -y
    sudo apt-get install -y postgresql-16 postgresql-contrib

    sudo -u postgres psql -c "CREATE DATABASE monitoring_db;"
    sudo -u postgres psql -c "CREATE USER report_user WITH PASSWORD 'isis2503';"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE monitoring_db TO report_user;"
    sudo -u postgres psql -d monitoring_db -c "GRANT ALL ON SCHEMA public TO report_user;"

    sudo sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" \
      /etc/postgresql/16/main/postgresql.conf
    sudo sed -i "s/max_connections = 100/max_connections = 500/" \
      /etc/postgresql/16/main/postgresql.conf

    echo "host all all 0.0.0.0/0 md5" | \
      sudo tee -a /etc/postgresql/16/main/pg_hba.conf

    sudo systemctl restart postgresql
    sudo systemctl enable postgresql
  EOT

  tags = merge(local.common_tags, { Name = "${var.project_prefix}-db" })
}

# ============================================================
# Instancias App Django (a, b, c) — 3 instancias para threshold 66%
# ============================================================
resource "aws_instance" "app_instances" {
  for_each = toset(["a", "b", "c"])

  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type_app
  key_name                    = var.key_name
  associate_public_ip_address = true
  vpc_security_group_ids = [
    aws_security_group.traffic_django.id,
    aws_security_group.traffic_ssh.id
  ]

  user_data = <<-EOT
    #!/bin/bash
    export DATABASE_HOST="${aws_instance.database.private_ip}"
    echo "DATABASE_HOST=${aws_instance.database.private_ip}" | \
      sudo tee -a /etc/environment

    sudo apt-get update -y
    sudo apt-get install -y python3-pip git build-essential \
      libpq-dev python3-dev

    mkdir -p /labs
    cd /labs

    git clone https://github.com/lgalvanbr/Arquisoft.git
    cd Arquisoft

    sudo pip3 install --break-system-packages \
      Django==4.2.0 \
      psycopg2-binary==2.9.6 \
      djangorestframework==3.14.0 \
      djangorestframework-simplejwt==5.2.2 \
      django-cors-headers==4.0.0 \
      python-decouple==3.8 \
      PyJWT==2.8.0 \
      gunicorn==21.2.0 \
      gevent==23.9.1 \
      whitenoise==6.6.0

    # Solo app-a corre las migraciones (evita conflictos de concurrencia)
    if [ "${each.key}" = "a" ]; then
      sleep 30  # espera que PostgreSQL esté listo
      export DATABASE_HOST="${aws_instance.database.private_ip}"
      sudo -E python3 manage.py migrate --noinput || true
      sudo -E python3 manage.py migrate --run-syncdb --noinput || true
    fi
  EOT

  depends_on = [aws_instance.database]

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-app-${each.key}"
    Role = "app-instance"
  })
}

# ============================================================
# Instancia Kong — Load Balancer + Circuit Breaker
# ============================================================
resource "aws_instance" "kong" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type_kong
  key_name                    = var.key_name
  associate_public_ip_address = true
  vpc_security_group_ids = [
    aws_security_group.traffic_kong.id,
    aws_security_group.traffic_ssh.id
  ]

  user_data = <<-EOT
    #!/bin/bash
    sudo apt-get update -y
    sudo apt-get install -y ca-certificates curl gnupg lsb-release

    # Instalar Docker
    sudo mkdir -m 0755 -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
      sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

    echo "deb [arch=$(dpkg --print-architecture) \
      signed-by=/etc/apt/keyrings/docker.gpg] \
      https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
      sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    sudo apt-get update -y
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io \
      docker-buildx-plugin docker-compose-plugin

    sudo usermod -aG docker ubuntu
    sudo systemctl enable docker
    sudo systemctl start docker

    # Pre-descargar la imagen de Kong para que esté lista
    sudo docker pull kong/kong-gateway:2.7.2.0-alpine
  EOT

  tags = merge(local.common_tags, { Name = "${var.project_prefix}-kong" })
}

# ============================================================
# Outputs — IPs necesarias para configurar Kong y el experimento
# ============================================================
output "database_private_ip" {
  description = "IP privada de la BD (para kong.yml y configuracion de apps)"
  value       = aws_instance.database.private_ip
}

output "database_public_ip" {
  description = "IP publica de la BD (para SSH de verificacion)"
  value       = aws_instance.database.public_ip
}

output "app_private_ips" {
  description = "IPs PRIVADAS de las instancias app — usar en kong.yml como targets"
  value = {
    for k, v in aws_instance.app_instances :
    "app-${k}" => v.private_ip
  }
}

output "app_public_ips" {
  description = "IPs PUBLICAS de las instancias app — usar para SSH"
  value = {
    for k, v in aws_instance.app_instances :
    "app-${k}" => v.public_ip
  }
}

output "kong_public_ip" {
  description = "IP publica de Kong — PUNTO DE ENTRADA del sistema"
  value       = aws_instance.kong.public_ip
}

output "kong_instrucciones" {
  description = "Comandos listos para configurar Kong (ejecutar por SSH en cbd-kong)"
  value       = <<-INSTRUCCIONES
    === PASO 1: Conectarse a Kong ===
    ssh -i ~/.ssh/finops-key.pem ubuntu@${aws_instance.kong.public_ip}

    === PASO 2: Crear kong.yml (reemplaza las IPs reales) ===
    Ver app_private_ips en outputs de Terraform para las IPs correctas

    === PASO 3: Levantar Kong ===
    sudo docker network create kong-net
    sudo docker run -d --name kong --user root \
      --network=kong-net \
      -v "$HOME:/kong/declarative/" \
      -e "KONG_DATABASE=off" \
      -e "KONG_DECLARATIVE_CONFIG=/kong/declarative/kong.yml" \
      -e "KONG_PROXY_ACCESS_LOG=/dev/stdout" \
      -e "KONG_ADMIN_ACCESS_LOG=/dev/stdout" \
      -e "KONG_PROXY_ERROR_LOG=/dev/stderr" \
      -e "KONG_ADMIN_ERROR_LOG=/dev/stderr" \
      -e "KONG_ADMIN_LISTEN=0.0.0.0:8001" \
      -p 8000:8000 -p 8001:8001 \
      kong/kong-gateway:2.7.2.0-alpine

    === PASO 4: Verificar ===
    curl http://localhost:8001/status
    curl http://localhost:8000/api/reportes/health
  INSTRUCCIONES
}
