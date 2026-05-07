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

variable "branch" {
  description = "Git branch to deploy on the app instances"
  type        = string
  default     = "ASR1Disponibilidad"
}

# ========== LOCALS ==========

locals {
  project_name = "${var.project_prefix}-arquisoft"
  repository   = "https://github.com/lgalvanbr/Arquisoft.git"
  branch       = var.branch

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

data "aws_availability_zones" "available" {
  state = "available"
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

# ========== RDS DATABASE (Multi-AZ) ==========

resource "aws_db_subnet_group" "main" {
  name       = "${var.project_prefix}-db-subnet-group"
  subnet_ids = data.aws_subnets.default.ids

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-db-subnet-group"
  })
}

resource "aws_db_instance" "database" {
  identifier             = "${var.project_prefix}-db"
  engine                 = "postgres"
  engine_version         = "16"
  instance_class         = "db.t3.micro"
  allocated_storage      = 20
  db_name                = "monitoring_db"
  username               = "report_user"
  password               = "isis2503"
  multi_az               = true
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.traffic_db.id]
  skip_final_snapshot    = true
  publicly_accessible    = false

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-db"
    Role = "database"
  })
}

# ========== EC2 APP INSTANCES ==========

resource "aws_instance" "app_instances" {
  for_each = {
    a = data.aws_availability_zones.available.names[0]
    b = data.aws_availability_zones.available.names[1]
  }

  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type_app
  associate_public_ip_address = true
  availability_zone           = each.value
  vpc_security_group_ids      = [aws_security_group.traffic_http.id, aws_security_group.traffic_ssh.id]

  user_data = <<-EOT
#!/bin/bash
# =======================================================
# CloudyNet FinOps - Auto-setup completo para app-${each.key}
# Ejecutado una sola vez en el primer arranque via cloud-init
# =======================================================
# Runs once at first boot via cloud-init
# =======================================================
exec > /var/log/cloudynet-setup.log 2>&1

INSTANCE_ID="${each.key}"
DB_HOST="${aws_db_instance.database.address}"
REPO="${local.repository}"
BRANCH="${local.branch}"
APP_DIR="/apps/Arquisoft"
VENV_DIR="/apps/venv"

echo "[$(date)] ===== CloudyNet setup iniciado (instancia: app-$INSTANCE_ID) ====="

# ── 1. Dependencias del sistema ───────────────────────────────────────
apt-get update -y -q
apt-get install -y -q python3 python3-pip python3-venv git build-essential libpq-dev python3-dev netcat-openbsd curl
echo "[$(date)] Paquetes del sistema instalados."

# ── 2. Clonar repositorio ─────────────────────────────────────────────
mkdir -p /apps
if [ ! -d "$APP_DIR/.git" ]; then
  git clone "$REPO" "$APP_DIR"
else
  cd "$APP_DIR" && git fetch origin && git reset --hard origin/$BRANCH
fi
cd "$APP_DIR"
echo "[$(date)] Repositorio listo en $APP_DIR."

# ── 3. Entorno virtual Python ─────────────────────────────────────────
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip -q
"$VENV_DIR/bin/pip" install -r "$APP_DIR/requirements.txt" -q
echo "[$(date)] Virtualenv y dependencias instaladas en $VENV_DIR."

# ── 4. Variables de entorno (nombres que usa settings.py) ─────────────
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

# Exportar para los comandos que siguen
set -a; source /etc/cloudynet.env; set +a
echo "[$(date)] Variables de entorno configuradas."

# ── 5. Esperar PostgreSQL (máx 5 min) ─────────────────────────────────
echo "[$(date)] Esperando PostgreSQL en $DB_HOST:5432..."
for i in $(seq 1 30); do
  if nc -z "$DB_HOST" 5432 2>/dev/null; then
    echo "[$(date)] PostgreSQL disponible en el intento $i."
    break
  fi
  echo "[$(date)] Intento $i/30 — esperando 10 s..."
  sleep 10
done

# ── 6. Migraciones ────────────────────────────────────────────────────
if [ "$INSTANCE_ID" = "a" ]; then
  echo "[$(date)] app-a: ejecutando migraciones..."
  cd "$APP_DIR" && "$VENV_DIR/bin/python" manage.py migrate --noinput
  echo "[$(date)] Migraciones completadas."
  echo "[$(date)] app-a: creando usuarios por defecto..."
  cd "$APP_DIR" && "$VENV_DIR/bin/python" manage.py seed_user --username admin --email admin@bite.co --password Admin1234! --empresa BITE.CO --rol admin
  cd "$APP_DIR" && "$VENV_DIR/bin/python" manage.py seed_user --username usuario1 --email usuario1@bite.co --password Usuario1234! --empresa BITE.CO --rol usuario
  echo "[$(date)] Seed usuarios completado."
else
  echo "[$(date)] app-b: esperando 90 s a que app-a migre..."
  sleep 90
  cd "$APP_DIR" && "$VENV_DIR/bin/python" manage.py migrate --noinput
  echo "[$(date)] Migraciones verificadas en app-b."
fi

# ── 7. Servicio systemd ───────────────────────────────────────────────
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
ExecStart=$GUNICORN_BIN finops_platform.wsgi:application --bind 0.0.0.0:8080 --workers 4 --timeout 120 --access-logfile /var/log/gunicorn-access.log --error-logfile /var/log/gunicorn-error.log
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
RestartSec=5
StandardOutput=append:/var/log/gunicorn-stdout.log
StandardError=append:/var/log/gunicorn-error.log

[Install]
WantedBy=multi-user.target
SVCEOF

# ── 8. Script de actualización rápida (git pull + restart) ───────────
cat > /usr/local/bin/cloudynet-update <<UPDEOF
#!/bin/bash
cd $APP_DIR
git fetch origin
git reset --hard origin/$BRANCH
$VENV_DIR/bin/pip install -r requirements.txt -q
set -a; source /etc/cloudynet.env; set +a
$VENV_DIR/bin/python manage.py migrate --noinput
systemctl restart cloudynet.service
systemctl is-active cloudynet.service
echo "Actualización completada."
UPDEOF
chmod +x /usr/local/bin/cloudynet-update

# ── 9. Habilitar e iniciar ────────────────────────────────────────────
systemctl daemon-reload
systemctl enable cloudynet.service
systemctl start cloudynet.service

echo "[$(date)] Servicio cloudynet.service activo y habilitado en reboot."
echo "[$(date)] ===== Setup completado app-$INSTANCE_ID ====="
echo "[$(date)] Para futuras actualizaciones: sudo cloudynet-update"
EOT

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-app-lb-${each.key}"
    Role = "application"
  })

  depends_on = [aws_db_instance.database]
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
    interval            = 10
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

output "database_endpoint" {
  description = "RDS endpoint address for the database"
  value       = aws_db_instance.database.address
}

output "database_port" {
  description = "RDS port for the database"
  value       = aws_db_instance.database.port
}

output "app_instances_public_ips" {
  description = "Public IP addresses of the application instances"
  value       = { for id, instance in aws_instance.app_instances : id => instance.public_ip }
}

output "app_instances_private_ips" {
  description = "Private IP addresses of the application instances"
  value       = { for id, instance in aws_instance.app_instances : id => instance.private_ip }
}
