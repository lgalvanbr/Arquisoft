# ***************** Universidad de los Andes ***********************
# ****** Departamento de Ingeniería de Sistemas y Computación ******
# ********** Arquitectura y diseño de Software - ISIS2503 **********
#
# Infraestructura para experimento Circuit Breaker - Arquisoft FinOps
#
# Flujo de trafico:
#   Cliente → Kong :8000 → app-a/b/c :8080 → PostgreSQL :5432
#
# Kong actua como:
#   - Load Balancer (round-robin entre 3 instancias)
#   - Circuit Breaker (threshold 66% via health checks activos)
#
# Instancias desplegadas:
#   - report-db         (PostgreSQL t3.micro)
#   - report-app-lb-a   (Django + Gunicorn t2.nano)
#   - report-app-lb-b   (Django + Gunicorn t2.nano)
#   - report-app-lb-c   (Django + Gunicorn t2.nano)
#   - cbd-kong          (Kong Gateway t2.micro)
# ******************************************************************

# ========== VARIABLES ==========

variable "key_name" {
  description = "Nombre del Key Pair creado en AWS (sin extension .pem)"
  type        = string
  default     = "finops-key"
}

variable "region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "project_prefix" {
  description = "Prefix used for naming AWS resources"
  type        = string
  default     = "report"
}

variable "instance_type_db" {
  description = "EC2 instance type for database"
  type        = string
  default     = "t3.micro"
}

variable "instance_type_app" {
  description = "EC2 instance type for application hosts"
  type        = string
  default     = "t2.nano"
}

variable "instance_type_kong" {
  description = "EC2 instance type for Kong Gateway"
  type        = string
  default     = "t2.micro"
}

# ========== LOCALS ==========

locals {
  project_name = "report-arquisoft"
  repository   = "https://github.com/lgalvanbr/Arquisoft.git"
  branch       = "main"

  common_tags = {
    Project   = local.project_name
    ManagedBy = "Terraform"
  }
}

# ========== PROVIDER ==========

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

# ========== DATA SOURCES ==========

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

data "aws_vpc" "default" {
  default = true
}

# ========== SECURITY GROUPS ==========

resource "aws_security_group" "traffic_ssh" {
  name        = "${var.project_prefix}-trafico-ssh"
  description = "Allow SSH access"

  ingress {
    description = "SSH desde cualquier origen"
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

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-trafico-ssh"
  })
}

resource "aws_security_group" "traffic_db" {
  name        = "${var.project_prefix}-trafico-db"
  description = "Allow PostgreSQL access"

  ingress {
    description = "PostgreSQL"
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

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-trafico-db"
  })
}

resource "aws_security_group" "traffic_http" {
  name        = "${var.project_prefix}-trafico-http"
  description = "Allow HTTP traffic to application on port 8080"

  ingress {
    description = "Gunicorn - Kong accede por este puerto"
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

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-trafico-http"
  })
}

resource "aws_security_group" "traffic_kong" {
  name        = "cbd-traffic-kong"
  description = "Kong Gateway proxy (8000) and admin API (8001)"

  ingress {
    description = "Kong proxy - entrada de trafico de usuarios"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Kong admin API - monitoreo del upstream"
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

  tags = merge(local.common_tags, {
    Name = "cbd-traffic-kong"
  })
}

# ========== EC2 DATABASE ==========

resource "aws_instance" "database" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type_db
  key_name                    = var.key_name
  associate_public_ip_address = true
  vpc_security_group_ids      = [
    aws_security_group.traffic_db.id,
    aws_security_group.traffic_ssh.id
  ]

  user_data = <<-EOT
#!/bin/bash
exec > /var/log/cloudynet-db-setup.log 2>&1
echo "[$(date)] Iniciando setup PostgreSQL..."

apt-get update -y -q
apt-get install -y -q postgresql postgresql-contrib
sleep 5

sudo -u postgres psql <<SQLEOF
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'report_user') THEN
    CREATE USER report_user WITH PASSWORD 'isis2503';
  END IF;
END
\$\$;
SQLEOF

sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = 'monitoring_db'" | grep -q 1 || \
  sudo -u postgres createdb -O report_user monitoring_db

sudo -u postgres psql -d monitoring_db \
  -c "GRANT ALL ON SCHEMA public TO report_user;" 2>/dev/null || true

PG_HBA="/etc/postgresql/16/main/pg_hba.conf"
PG_CONF="/etc/postgresql/16/main/postgresql.conf"

grep -q "^host all all 0.0.0.0/0" "$PG_HBA" || \
  echo "host all all 0.0.0.0/0 trust" >> "$PG_HBA"

sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" "$PG_CONF" || \
  grep -q "^listen_addresses" "$PG_CONF" || \
  echo "listen_addresses='*'" >> "$PG_CONF"

echo "max_connections=500" >> "$PG_CONF"

systemctl enable postgresql
systemctl restart postgresql

echo "[$(date)] PostgreSQL listo. DB: monitoring_db / User: report_user"
EOT

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-db"
    Role = "database"
  })
}

# ========== EC2 APP INSTANCES (a, b, c) ==========

resource "aws_instance" "app_instances" {
  for_each = toset(["a", "b", "c"])

  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type_app
  key_name                    = var.key_name
  associate_public_ip_address = true
  vpc_security_group_ids      = [
    aws_security_group.traffic_http.id,
    aws_security_group.traffic_ssh.id
  ]

  user_data = <<-EOT
#!/bin/bash
exec > /var/log/cloudynet-setup.log 2>&1

INSTANCE_ID="${each.key}"
DB_HOST="${aws_instance.database.private_ip}"
REPO="${local.repository}"
BRANCH="${local.branch}"
APP_DIR="/apps/Arquisoft"
VENV_DIR="/apps/venv"

echo "[$(date)] ===== Setup iniciado (app-$INSTANCE_ID) ====="

apt-get update -y -q
apt-get install -y -q python3 python3-pip python3-venv git \
  build-essential libpq-dev python3-dev netcat-openbsd curl
echo "[$(date)] Paquetes instalados."

mkdir -p /apps
if [ ! -d "$APP_DIR/.git" ]; then
  git clone "$REPO" "$APP_DIR"
else
  cd "$APP_DIR" && git fetch origin && git reset --hard origin/$BRANCH
fi
echo "[$(date)] Repositorio listo."

python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip -q
"$VENV_DIR/bin/pip" install -r "$APP_DIR/requirements.txt" -q
echo "[$(date)] Dependencias Python instaladas."

cat > /etc/cloudynet.env <<ENVEOF
DATABASE_HOST=$DB_HOST
DB_NAME=monitoring_db
DB_USER=report_user
DB_PASSWORD=isis2503
DB_PORT=5432
DJANGO_SETTINGS_MODULE=finops_platform.settings
PYTHONUNBUFFERED=1
ENVEOF
chmod 644 /etc/cloudynet.env
set -a; source /etc/cloudynet.env; set +a
echo "[$(date)] Variables de entorno configuradas."

echo "[$(date)] Esperando PostgreSQL en $DB_HOST:5432..."
for i in $(seq 1 30); do
  if nc -z "$DB_HOST" 5432 2>/dev/null; then
    echo "[$(date)] PostgreSQL disponible (intento $i)."
    break
  fi
  sleep 10
done

if [ "$INSTANCE_ID" = "a" ]; then
  echo "[$(date)] app-a: migraciones y seed..."
  cd "$APP_DIR"
  "$VENV_DIR/bin/python" manage.py migrate --noinput
  "$VENV_DIR/bin/python" manage.py seed_user \
    --username admin --email admin@bite.co \
    --password Admin1234! --empresa BITE.CO --rol admin 2>/dev/null || true
  "$VENV_DIR/bin/python" manage.py seed_user \
    --username usuario1 --email usuario1@bite.co \
    --password Usuario1234! --empresa BITE.CO --rol usuario 2>/dev/null || true
  echo "[$(date)] Migraciones y seed completados."
else
  echo "[$(date)] app-$INSTANCE_ID: esperando 90s a que app-a migre..."
  sleep 90
  cd "$APP_DIR" && "$VENV_DIR/bin/python" manage.py migrate --noinput
  echo "[$(date)] Migraciones verificadas en app-$INSTANCE_ID."
fi

GUNICORN_BIN="$VENV_DIR/bin/gunicorn"

cat > /etc/systemd/system/cloudynet.service <<SVCEOF
[Unit]
Description=CloudyNet FinOps Gunicorn (app-${each.key})
After=network-online.target
Wants=network-online.target

[Service]
Type=exec
User=root
WorkingDirectory=$APP_DIR
EnvironmentFile=/etc/cloudynet.env
ExecStart=$GUNICORN_BIN finops_platform.wsgi:application \
  --bind 0.0.0.0:8080 \
  --workers 4 \
  --timeout 120 \
  --access-logfile /var/log/gunicorn-access.log \
  --error-logfile /var/log/gunicorn-error.log
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
RestartSec=5
StandardOutput=append:/var/log/gunicorn-stdout.log
StandardError=append:/var/log/gunicorn-error.log

[Install]
WantedBy=multi-user.target
SVCEOF

cat > /usr/local/bin/cloudynet-update <<UPDEOF
#!/bin/bash
cd $APP_DIR
git fetch origin && git reset --hard origin/$BRANCH
$VENV_DIR/bin/pip install -r requirements.txt -q
set -a; source /etc/cloudynet.env; set +a
$VENV_DIR/bin/python manage.py migrate --noinput
systemctl restart cloudynet.service
systemctl is-active cloudynet.service
echo "Actualizacion completada."
UPDEOF
chmod +x /usr/local/bin/cloudynet-update

systemctl daemon-reload
systemctl enable cloudynet.service
systemctl start cloudynet.service

echo "[$(date)] cloudynet.service activo en puerto 8080."
echo "[$(date)] ===== Setup completado app-$INSTANCE_ID ====="
EOT

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-app-lb-${each.key}"
    Role = "application"
  })

  depends_on = [aws_instance.database]
}

# ========== EC2 KONG (Load Balancer + Circuit Breaker) ==========

resource "aws_instance" "kong" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type_kong
  key_name                    = var.key_name
  associate_public_ip_address = true
  vpc_security_group_ids      = [
    aws_security_group.traffic_kong.id,
    aws_security_group.traffic_ssh.id
  ]

  user_data = <<-EOT
#!/bin/bash
exec > /var/log/kong-setup.log 2>&1
echo "[$(date)] Instalando Docker para Kong..."

apt-get update -y -q
apt-get install -y -q ca-certificates curl gnupg lsb-release

mkdir -m 0755 -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  gpg --dearmor -o /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) \
  signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update -y -q
apt-get install -y -q docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin

usermod -aG docker ubuntu
systemctl enable docker
systemctl start docker

docker pull kong/kong-gateway:2.7.2.0-alpine

echo "[$(date)] Docker listo. Imagen Kong descargada."
EOT

  tags = merge(local.common_tags, {
    Name = "cbd-kong"
    Role = "load-balancer-circuit-breaker"
  })
}

# ========== OUTPUTS ==========

output "database_private_ip" {
  description = "IP privada de la DB"
  value       = aws_instance.database.private_ip
}

output "database_public_ip" {
  description = "IP publica de la DB"
  value       = aws_instance.database.public_ip
}

output "app_instances_private_ips" {
  description = "IPs privadas de las apps - copiar en kong.yml targets"
  value       = { for id, instance in aws_instance.app_instances : id => instance.private_ip }
}

output "app_instances_public_ips" {
  description = "IPs publicas de las apps - usar para SSH"
  value       = { for id, instance in aws_instance.app_instances : id => instance.public_ip }
}

output "kong_public_ip" {
  description = "IP publica de Kong - unico punto de entrada al sistema"
  value       = aws_instance.kong.public_ip
}

output "url_sistema" {
  description = "URL para acceder al sistema a traves de Kong"
  value       = "http://${aws_instance.kong.public_ip}:8000"
}

output "url_kong_admin" {
  description = "URL del admin API de Kong - monitorear upstream"
  value       = "http://${aws_instance.kong.public_ip}:8001"
}
