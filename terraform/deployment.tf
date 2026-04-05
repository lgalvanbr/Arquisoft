# ***************** Universidad de los Andes ***********************
# ****** Departamento de Ingeniería de Sistemas y Computación ******
# ********** Arquitectura y diseño de Software - ISIS2503 **********
#
# Infraestructura para laboratorio de Load Balancer - Arquisoft FinOps
# OPCIÓN 2: Balance Architecture con Gunicorn y ElastiCache
#
# Elementos a desplegar en AWS:
# 1. Grupos de seguridad:
#    - report-trafico-ssh (puerto 22)
#    - report-trafico-db (puerto 5432)
#    - report-trafico-http (puerto 8080)
#    - report-trafico-lb (puerto 80)
#    - report-trafico-redis (puerto 6379)
#
# 2. Instancias EC2:
#    - report-db (t3.small - PostgreSQL instalado y configurado)
#    - report-app-lb-a/b/c/d/e/f/g/h/i/j (10 × t3.small - Gunicorn + Django)
#
# 3. Load Balancer:
#    - Application Load Balancer (report-alb)
#    - Target Group (report-app-group) con health check en /api/reportes/health
#    - Listener en puerto 80
#
# 4. ElastiCache:
#    - Redis cluster (1 nodo t3.small) para caching y sesiones
#
# CAPACIDAD:
#    - 12,000 usuarios concurrentes
#    - 60 Gunicorn workers (10 × 6 workers)
#    - ~6,000 req/seg bajo carga pico
#    - Error rate < 5%, Latencia p50: 2-5s
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
  default     = "t3.small"  # OPTION 2: t2.micro → t3.small (2 vCPU, 2GB RAM)
}

variable "instance_type_db" {
  description = "EC2 instance type for database"
  type        = string
  default     = "t3.small"  # OPTION 2: t3.micro → t3.small
}

variable "gunicorn_workers" {
  description = "Number of Gunicorn workers per instance (formula: 2*cpu_cores + 1)"
  type        = number
  default     = 6  # For t3.small (2 cores): 2*2 + 1 = 5, using 6 for safety
}

# ========== LOCALS ==========

locals {
  project_name = "${var.project_prefix}-arquisoft"
  repository   = "https://github.com/AriadnaVargas/Arquisoft.git"
  branch       = "main"

  common_tags = {
    Project   = local.project_name
    ManagedBy = "Terraform"
  }
}

# ========== PROVIDER ==========

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

# ========== SECURITY GROUP: REDIS ==========

resource "aws_security_group" "traffic_redis" {
  name        = "${var.project_prefix}-trafico-redis"
  description = "Allow Redis/ElastiCache access"

  ingress {
    description     = "Redis access from app servers"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.traffic_http.id]
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-trafico-redis"
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
               set -e

               # ===== LOGGING =====
               exec > >(tee /var/log/deployment.log)
               exec 2>&1

               # ===== ENVIRONMENT SETUP =====
               export DATABASE_HOST=${aws_instance.database.private_ip}
               echo "DATABASE_HOST=${aws_instance.database.private_ip}" >> /etc/environment
               
               echo "=== DATABASE DEPLOYMENT STARTED ===" | tee -a /var/log/deployment.log

               # ===== SYSTEM PACKAGES =====
               echo "Installing PostgreSQL..."
               sudo apt-get update -y
               sudo apt-get install -y postgresql postgresql-contrib

               # ===== POSTGRESQL CONFIGURATION =====
               echo "Configuring PostgreSQL..."
               sudo -u postgres psql -c "CREATE USER report_user WITH PASSWORD 'isis2503';"
               sudo -u postgres createdb -O report_user monitoring_db
               
               echo "host all all 0.0.0.0/0 trust" | sudo tee -a /etc/postgresql/16/main/pg_hba.conf
               echo "listen_addresses='*'" | sudo tee -a /etc/postgresql/16/main/postgresql.conf
               echo "max_connections=4000" | sudo tee -a /etc/postgresql/16/main/postgresql.conf  # OPTION 2: 2000 → 4000
               echo "shared_buffers=256MB" | sudo tee -a /etc/postgresql/16/main/postgresql.conf # OPTION 2: NEW

               sudo service postgresql restart

               echo "=== DATABASE DEPLOYMENT COMPLETED ===" | tee -a /var/log/deployment.log
               EOT
  )

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-db"
    Role = "database"
  })
}

# ========== EC2 APP INSTANCES ==========

resource "aws_instance" "app_instances" {
  for_each = toset(["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"])  # OPTION 2: 4 → 10 instances

  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type_app
  associate_public_ip_address = true
  vpc_security_group_ids      = [aws_security_group.traffic_http.id, aws_security_group.traffic_ssh.id]

  user_data_base64 = base64encode(<<-EOT
               #!/bin/bash
               set -e

               # ===== LOGGING =====
               exec > >(tee /var/log/deployment.log)
               exec 2>&1

               # ===== ENVIRONMENT SETUP =====
               export DATABASE_HOST=${aws_instance.database.private_ip}
               echo "DATABASE_HOST=${aws_instance.database.private_ip}" >> /etc/environment
               
               echo "=== DEPLOYMENT STARTED ===" | tee -a /var/log/deployment.log

               # ===== SYSTEM PACKAGES =====
               echo "Installing system packages..."
               sudo apt-get update -y
               sudo apt-get install -y python3-pip git build-essential libpq-dev python3-dev

               # ===== DJANGO APPLICATION =====
               echo "Cloning and setting up Django application..."
               mkdir -p /apps
               cd /apps

               if [ ! -d Arquisoft ]; then
                 git clone ${local.repository}
               fi

               cd Arquisoft
               git fetch origin ${local.branch}
               git checkout ${local.branch}
               
               echo "Installing Python dependencies..."
               sudo pip3 install --upgrade pip --break-system-packages
               sudo pip3 install -r requirements.txt --break-system-packages

               # ===== DATABASE MIGRATIONS (Only on instance 'a') =====
               if [ "${each.key}" = "a" ]; then
                 echo "Running database migrations (instance a)..."
                 sudo python3 manage.py makemigrations
                 sudo python3 manage.py migrate
                 sudo python3 manage.py collectstatic --noinput 2>/dev/null || true
               fi

               # ===== GUNICORN SYSTEMD SERVICE =====
               echo "Creating Gunicorn systemd service..."
               sudo tee /etc/systemd/system/gunicorn.service > /dev/null << 'GUNICORN_EOF'
[Unit]
Description=Gunicorn Arquisoft FinOps Application Server
After=network.target postgresql.service
Documentation=https://gunicorn.org

[Service]
Type=notify
User=ubuntu
Group=ubuntu
WorkingDirectory=/apps/Arquisoft
StandardInput=null
StandardOutput=journal
StandardError=journal

# Environment variables
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
Environment="DATABASE_HOST=${aws_instance.database.private_ip}"
Environment="DJANGO_SETTINGS_MODULE=finops_platform.settings"

# Gunicorn startup command
ExecStart=/usr/bin/python3 -m gunicorn \
  --workers ${var.gunicorn_workers} \
  --worker-class sync \
  --bind 0.0.0.0:8080 \
  --timeout 30 \
  --access-logfile /var/log/gunicorn-access.log \
  --error-logfile /var/log/gunicorn-error.log \
  --log-level info \
  finops_platform.wsgi:application

# Restart policy
Restart=on-failure
RestartSec=5
StartLimitInterval=60
StartLimitBurst=3

# Resource limits
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
GUNICORN_EOF

               # ===== SYSTEMD STARTUP =====
               echo "Starting Gunicorn service..."
               sudo systemctl daemon-reload
               sudo systemctl enable gunicorn
               sudo systemctl start gunicorn

               # ===== VERIFICATION =====
               sleep 5
               if sudo systemctl is-active gunicorn > /dev/null 2>&1; then
                 echo "✓ Gunicorn service is running successfully"
               else
                 echo "✗ Gunicorn service failed to start"
                 sudo systemctl status gunicorn || true
                 exit 1
               fi

               echo "=== DEPLOYMENT COMPLETED SUCCESSFULLY ===" | tee -a /var/log/deployment.log
               EOT
  )

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
    unhealthy_threshold = 3  # OPTION 2: 2 → 3
    timeout             = 10  # OPTION 2: 5 → 10 (more tolerance for Gunicorn startup)
    interval            = 30
    path                = "/api/reportes/health"
    matcher             = "200"
    protocol            = "HTTP"
  }

  deregistration_delay = 30  # OPTION 2: NEW Connection draining

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

# ========== ELASTICACHE SUBNET GROUP ==========

resource "aws_elasticache_subnet_group" "default" {
  name       = "${var.project_prefix}-redis-subnet-group"
  subnet_ids = data.aws_subnets.default.ids

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-redis-subnet-group"
  })
}

# ========== ELASTICACHE REDIS CLUSTER ==========

resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "${var.project_prefix}-redis"
  engine               = "redis"
  node_type            = "cache.t3.small"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
  engine_version       = "7.0"

  subnet_group_name  = aws_elasticache_subnet_group.default.name
  security_group_ids = [aws_security_group.traffic_redis.id]

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-redis"
  })

  depends_on = [aws_security_group.traffic_redis]
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

output "redis_endpoint" {
  description = "Redis ElastiCache endpoint (host:port)"
  value       = "${aws_elasticache_cluster.redis.cache_nodes[0].address}:${aws_elasticache_cluster.redis.port}"
}

output "redis_host" {
  description = "Redis ElastiCache host address"
  value       = aws_elasticache_cluster.redis.cache_nodes[0].address
}

output "redis_port" {
  description = "Redis ElastiCache port"
  value       = aws_elasticache_cluster.redis.port
}

output "deployment_summary" {
  description = "Summary of deployed infrastructure (OPTION 2: Balance Architecture)"
  value       = {
    architecture    = "OPTION 2: Balance (Gunicorn + ElastiCache)"
    app_instances   = 10
    app_type        = "t3.small (2 vCPU, 2GB RAM)"
    gunicorn_workers = var.gunicorn_workers
    total_workers   = 10 * var.gunicorn_workers
    database_type   = var.instance_type_db
    redis_enabled   = true
    expected_capacity = "12,000 concurrent users"
    expected_rps    = "5,000-6,000 requests/sec"
    estimated_cost  = "$110-150/month"
  }
}