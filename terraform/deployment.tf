# ***************** Universidad de los Andes ***********************
# ****** Departamento de Ingeniería de Sistemas y Computación ******
# ********** Arquitectura y diseño de Software - ISIS2503 **********
#
# Infraestructura para laboratorio de Load Balancer - Arquisoft FinOps
#
# Elementos a desplegar en AWS:
# 1. Grupos de seguridad:
#    - report-trafico-ssh (puerto 22)
#    - report-trafico-db (puerto 5432)
#    - report-trafico-http (puerto 8080)
#    - report-trafico-lb (puerto 80)
#
# 2. Instancias EC2:
#    - report-db (PostgreSQL instalado y configurado)
#    - report-app-lb-a/b/c (3 × t3.small)
#
# 3. Load Balancer:
#    - Application Load Balancer (report-alb)
#    - Target Group (report-app-group) con health check en /api/reportes/health
#    - Listener en puerto 80
# ******************************************************************

# ========== VARIABLES ==========

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

# ========== LOCALS ==========

locals {
  project_name = "${var.project_prefix}-arquisoft"
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

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# ========== SECURITY GROUPS ==========

resource "aws_security_group" "traffic_ssh" {
    name        = "${var.project_prefix}-trafico-ssh"
    description = "Allow SSH access"

    ingress {
        description = "SSH access from anywhere"
        from_port   = 22
        to_port     = 22
        protocol    = "tcp"
        cidr_blocks = ["0.0.0.0/0"]
    }

    egress {
        description = "Allow all outbound traffic"
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
    description = "Traffic from anywhere to DB"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound traffic"
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
  description = "Allow HTTP traffic to application"

  ingress {
    description = "HTTP access for application"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-trafico-http"
  })
}

resource "aws_security_group" "traffic_lb" {
  name        = "${var.project_prefix}-trafico-lb"
  description = "Allow HTTP traffic from internet to load balancer"

  ingress {
    description = "HTTP traffic for load balancer"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-trafico-lb"
  })
}

# ========== EC2 DATABASE ==========

resource "aws_instance" "database" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type_db
  associate_public_ip_address = true
  vpc_security_group_ids      = [aws_security_group.traffic_db.id, aws_security_group.traffic_ssh.id]

  user_data_base64 = base64encode(<<-EOT
               #!/bin/bash

               sudo apt-get update -y
               sudo apt-get install -y postgresql postgresql-contrib

               sudo -u postgres psql -c "CREATE USER report_user WITH PASSWORD 'isis2503';"
               sudo -u postgres createdb -O report_user monitoring_db
               echo "host all all 0.0.0.0/0 trust" | sudo tee -a /etc/postgresql/16/main/pg_hba.conf
               echo "listen_addresses='*'" | sudo tee -a /etc/postgresql/16/main/postgresql.conf
               echo "max_connections=2000" | sudo tee -a /etc/postgresql/16/main/postgresql.conf
               sudo service postgresql restart
               EOT
  )

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-db"
    Role = "database"
  })
}

# ========== EC2 APP INSTANCES ==========

resource "aws_instance" "app_instances" {
  for_each = toset(["a", "b"])

  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type_app
  associate_public_ip_address = true
  vpc_security_group_ids      = [aws_security_group.traffic_http.id, aws_security_group.traffic_ssh.id]

  user_data = <<-EOT
#!/bin/bash
# =======================================================
# CloudyNet FinOps - Auto-setup script for app-${each.key}
# Runs once at first boot via cloud-init
# =======================================================
exec > /var/log/cloudynet-setup.log 2>&1
set -e

INSTANCE_ID="${each.key}"
DB_HOST="${aws_instance.database.private_ip}"
REPO="${local.repository}"
BRANCH="${local.branch}"
APP_DIR="/apps/Arquisoft"

echo "[$(date)] ===== CloudyNet setup iniciado (instancia: app-$INSTANCE_ID) ====="

# ── 1. Variables de entorno persistentes ──────────────────────────────
cat > /etc/cloudynet.env <<'ENVEOF'
DATABASE_HOST=${aws_instance.database.private_ip}
DATABASE_NAME=monitoring_db
DATABASE_USER=report_user
DATABASE_PASSWORD=isis2503
DATABASE_PORT=5432
DJANGO_SETTINGS_MODULE=finops_platform.settings
PYTHONUNBUFFERED=1
ENVEOF
chmod 644 /etc/cloudynet.env

# Cargar en /etc/environment para sesiones SSH también
grep -v '^$' /etc/cloudynet.env >> /etc/environment
export $(cat /etc/cloudynet.env | xargs)

echo "[$(date)] Variables de entorno configuradas."

# ── 2. Dependencias del sistema ───────────────────────────────────────
apt-get update -y -q
apt-get install -y -q python3-pip git build-essential libpq-dev python3-dev netcat-openbsd

echo "[$(date)] Paquetes del sistema instalados."

# ── 3. Clonar / actualizar repositorio ───────────────────────────────
mkdir -p /apps
if [ ! -d "$APP_DIR" ]; then
  git clone "$REPO" "$APP_DIR"
else
  cd "$APP_DIR" && git fetch origin && git checkout "$BRANCH" && git pull origin "$BRANCH"
fi

cd "$APP_DIR"
git checkout "$BRANCH"
echo "[$(date)] Repositorio listo en $APP_DIR."

# ── 4. Instalar dependencias Python ──────────────────────────────────
pip3 install --upgrade pip --break-system-packages -q
pip3 install -r requirements.txt --break-system-packages --ignore-installed -q
echo "[$(date)] Dependencias Python instaladas."

# ── 5. Esperar a que PostgreSQL esté disponible (máx 5 min) ──────────
echo "[$(date)] Esperando conexión con PostgreSQL en $DB_HOST:5432..."
for i in $(seq 1 30); do
  if nc -z "$DB_HOST" 5432 2>/dev/null; then
    echo "[$(date)] PostgreSQL disponible después de $i intento(s)."
    break
  fi
  echo "[$(date)] Intento $i/30 - DB no disponible, esperando 10s..."
  sleep 10
done

# ── 6. Migraciones (solo app-a para evitar race condition; app-b espera) ──
if [ "$INSTANCE_ID" = "a" ]; then
  echo "[$(date)] Ejecutando migraciones Django (instancia primaria)..."
  python3 manage.py migrate --noinput
  echo "[$(date)] Migraciones completadas."
else
  echo "[$(date)] Instancia secundaria: esperando 90s para que app-a complete migraciones..."
  sleep 90
  echo "[$(date)] Ejecutando migrate (idempotente)..."
  python3 manage.py migrate --noinput
  echo "[$(date)] Migraciones verificadas."
fi

# ── 7. Crear servicio systemd (auto-arranque en reboot) ───────────────
GUNICORN_BIN=$(which gunicorn 2>/dev/null || find /usr /home -name gunicorn 2>/dev/null | head -1)
echo "[$(date)] Gunicorn encontrado en: $GUNICORN_BIN"

cat > /etc/systemd/system/cloudynet.service <<SVCEOF
[Unit]
Description=CloudyNet FinOps - Gunicorn (app-${each.key})
After=network.target
Wants=network-online.target

[Service]
Type=exec
User=root
WorkingDirectory=$APP_DIR
EnvironmentFile=/etc/cloudynet.env
ExecStart=$GUNICORN_BIN finops_platform.wsgi:application \\
    --bind 0.0.0.0:8080 \\
    --workers 4 \\
    --timeout 120 \\
    --access-logfile /var/log/gunicorn-access.log \\
    --error-logfile /var/log/gunicorn-error.log \\
    --log-level info
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
RestartSec=5
StandardOutput=append:/var/log/gunicorn-stdout.log
StandardError=append:/var/log/gunicorn-error.log

[Install]
WantedBy=multi-user.target
SVCEOF

# ── 8. Habilitar e iniciar el servicio ───────────────────────────────
systemctl daemon-reload
systemctl enable cloudynet.service
systemctl start cloudynet.service

echo "[$(date)] Servicio cloudynet.service iniciado y habilitado para reboot."
echo "[$(date)] ===== Setup completado exitosamente para app-$INSTANCE_ID ====="
EOT

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-app-lb-${each.key}"
    Role = "application"
  })

  depends_on = [aws_instance.database]
}

# ========== TARGET GROUP ==========

resource "aws_lb_target_group" "app_group" {
  name        = "${var.project_prefix}-app-group"
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = data.aws_vpc.default.id

  load_balancing_algorithm_type = "round_robin"

  health_check {
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 30
    path                = "/api/reportes/health"
    matcher             = "200"
    protocol            = "HTTP"
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-app-group"
  })
}

# ========== APPLICATION LOAD BALANCER ==========

resource "aws_lb" "app_alb" {
  name               = "${var.project_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.traffic_lb.id]
  subnets            = data.aws_subnets.default.ids

  enable_deletion_protection = false
  enable_http2               = true
  enable_cross_zone_load_balancing = true

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-alb"
  })
}

# ========== ALB LISTENER ==========

resource "aws_lb_listener" "app_listener" {
  load_balancer_arn = aws_lb.app_alb.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app_group.arn
  }
}

# ========== TARGET GROUP ATTACHMENT ==========

resource "aws_lb_target_group_attachment" "app_attachment" {
  for_each = aws_instance.app_instances

  target_group_arn = aws_lb_target_group.app_group.arn
  target_id        = each.value.id
  port             = 8080
}

# ========== OUTPUTS ==========

output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = aws_lb.app_alb.dns_name
}

output "access_url" {
  description = "URL to access the application through the load balancer"
  value       = "http://${aws_lb.app_alb.dns_name}"
}

output "alb_arn" {
  description = "ARN of the Application Load Balancer"
  value       = aws_lb.app_alb.arn
}

output "target_group_arn" {
  description = "ARN of the Target Group"
  value       = aws_lb_target_group.app_group.arn
}

output "database_public_ip" {
  description = "Public IP address of the database instance"
  value       = aws_instance.database.public_ip
}

output "database_private_ip" {
  description = "Private IP address of the database instance"
  value       = aws_instance.database.private_ip
}

output "app_instances_public_ips" {
  description = "Public IP addresses of the application instances"
  value       = { for id, instance in aws_instance.app_instances : id => instance.public_ip }
}

output "app_instances_private_ips" {
  description = "Private IP addresses of the application instances"
  value       = { for id, instance in aws_instance.app_instances : id => instance.private_ip }
}
