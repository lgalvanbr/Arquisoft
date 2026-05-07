# ***************** Universidad de los Andes ***********************
# ****** Departamento de Ingeniería de Sistemas y Computación ******
# ********** Arquitectura y diseño de Software - ISIS2503 **********
#
# Infraestructura Circuit Breaker - FinOps Platform BITE.CO
# Arquitectura: 2 servicios × 3 instancias + Kong (LB + CB)
#
# Cliente → Kong :8080
#             ├─ /api/auth     → autenticacion_upstream (auth-a/b/c :8000)
#             └─ /api/reportes → reportes_upstream      (rep-a/b/c  :8001)
# ==========================================

variable "key_name" {
  description = "Nombre del Key Pair en AWS"
  type        = string
  default     = "finops-key"
}

variable "region" {
  type    = string
  default = "us-east-1"
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

resource "aws_security_group" "traffic_auth" {
  name        = "${var.project_prefix}-traffic-auth"
  description = "Autenticacion service port 8000"
  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = merge(local.common_tags, { Name = "${var.project_prefix}-traffic-auth" })
}

resource "aws_security_group" "traffic_reportes" {
  name        = "${var.project_prefix}-traffic-reportes"
  description = "Reportes service port 8001"
  ingress {
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
  tags = merge(local.common_tags, { Name = "${var.project_prefix}-traffic-reportes" })
}

resource "aws_security_group" "traffic_db" {
  name        = "${var.project_prefix}-traffic-db"
  description = "PostgreSQL port 5432"
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

resource "aws_security_group" "traffic_kong" {
  name        = "${var.project_prefix}-traffic-kong"
  description = "Kong proxy :8080, admin :8001"
  ingress {
    description = "Kong proxy — punto de entrada del sistema"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    description = "Kong admin API"
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
# Instancias Servicio Autenticacion (a, b, c) — puerto 8000
# ============================================================
resource "aws_instance" "auth_instances" {
  for_each = toset(["a", "b", "c"])

  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type_app
  key_name                    = var.key_name
  associate_public_ip_address = true
  vpc_security_group_ids = [
    aws_security_group.traffic_auth.id,
    aws_security_group.traffic_ssh.id
  ]

  user_data = <<-EOT
    #!/bin/bash
    echo "DATABASE_HOST=${aws_instance.database.private_ip}" | sudo tee -a /etc/environment
    echo "SERVICE_PORT=8000" | sudo tee -a /etc/environment

    sudo apt-get update -y
    sudo apt-get install -y python3-pip git build-essential libpq-dev python3-dev

    mkdir -p /labs && cd /labs
    git clone https://github.com/lgalvanbr/Arquisoft.git
    cd Arquisoft

    sudo pip3 install --break-system-packages \
      Django==4.2.0 psycopg2-binary==2.9.6 djangorestframework==3.14.0 \
      djangorestframework-simplejwt==5.2.2 django-cors-headers==4.0.0 \
      python-decouple==3.8 PyJWT==2.8.0 gunicorn==21.2.0 \
      gevent==23.9.1 whitenoise==6.6.0

    if [ "${each.key}" = "a" ]; then
      sleep 30
      export DATABASE_HOST="${aws_instance.database.private_ip}"
      sudo -E python3 manage.py migrate --noinput || true
      sudo -E python3 manage.py migrate --run-syncdb --noinput || true
    fi
  EOT

  depends_on = [aws_instance.database]

  tags = merge(local.common_tags, {
    Name    = "${var.project_prefix}-auth-${each.key}"
    Service = "autenticacion"
  })
}

# ============================================================
# Instancias Servicio Reportes (a, b, c) — puerto 8001
# ============================================================
resource "aws_instance" "reportes_instances" {
  for_each = toset(["a", "b", "c"])

  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type_app
  key_name                    = var.key_name
  associate_public_ip_address = true
  vpc_security_group_ids = [
    aws_security_group.traffic_reportes.id,
    aws_security_group.traffic_ssh.id
  ]

  user_data = <<-EOT
    #!/bin/bash
    echo "DATABASE_HOST=${aws_instance.database.private_ip}" | sudo tee -a /etc/environment
    echo "SERVICE_PORT=8001" | sudo tee -a /etc/environment

    sudo apt-get update -y
    sudo apt-get install -y python3-pip git build-essential libpq-dev python3-dev

    mkdir -p /labs && cd /labs
    git clone https://github.com/lgalvanbr/Arquisoft.git
    cd Arquisoft

    sudo pip3 install --break-system-packages \
      Django==4.2.0 psycopg2-binary==2.9.6 djangorestframework==3.14.0 \
      djangorestframework-simplejwt==5.2.2 django-cors-headers==4.0.0 \
      python-decouple==3.8 PyJWT==2.8.0 gunicorn==21.2.0 \
      gevent==23.9.1 whitenoise==6.6.0
  EOT

  depends_on = [aws_instance.database]

  tags = merge(local.common_tags, {
    Name    = "${var.project_prefix}-rep-${each.key}"
    Service = "reportes"
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
    sudo docker pull kong/kong-gateway:2.7.2.0-alpine
  EOT

  tags = merge(local.common_tags, { Name = "${var.project_prefix}-kong" })
}

# ============================================================
# Outputs
# ============================================================
output "database_private_ip" {
  value = aws_instance.database.private_ip
}

output "auth_private_ips" {
  description = "IPs privadas autenticacion — para kong.yml autenticacion_upstream"
  value = { for k, v in aws_instance.auth_instances : "auth-${k}" => v.private_ip }
}

output "auth_public_ips" {
  description = "IPs publicas autenticacion — para SSH"
  value = { for k, v in aws_instance.auth_instances : "auth-${k}" => v.public_ip }
}

output "reportes_private_ips" {
  description = "IPs privadas reportes — para kong.yml reportes_upstream"
  value = { for k, v in aws_instance.reportes_instances : "rep-${k}" => v.private_ip }
}

output "reportes_public_ips" {
  description = "IPs publicas reportes — para SSH"
  value = { for k, v in aws_instance.reportes_instances : "rep-${k}" => v.public_ip }
}

output "kong_public_ip" {
  description = "PUNTO DE ENTRADA del sistema — http://<ip>:8080"
  value       = aws_instance.kong.public_ip
}
