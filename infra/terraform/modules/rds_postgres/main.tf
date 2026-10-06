# Single-AZ PostgreSQL on db.t4g.micro for demo windows. Not publicly accessible; reachable only
# from the security groups passed in. The connection URL is published as an SSM SecureString
# (Parameter Store standard tier is free) and injected into ECS tasks as a secret.

resource "random_password" "master" {
  length  = 32
  special = false
}

resource "aws_db_subnet_group" "this" {
  name       = var.name
  subnet_ids = var.subnet_ids
  tags       = var.tags
}

resource "aws_security_group" "db" {
  name        = "${var.name}-db"
  description = "PostgreSQL, only from patchloop tasks"
  vpc_id      = var.vpc_id
  tags        = var.tags
}

resource "aws_vpc_security_group_ingress_rule" "from_clients" {
  for_each                     = toset(var.client_security_group_ids)
  security_group_id            = aws_security_group.db.id
  referenced_security_group_id = each.value
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
  description                  = "PostgreSQL from ${each.value}"
}

resource "aws_db_parameter_group" "this" {
  name   = var.name
  family = "postgres${split(".", var.engine_version)[0]}"

  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }
  parameter {
    name  = "log_min_duration_statement"
    value = "500"
  }
  tags = var.tags
}

resource "aws_db_instance" "this" {
  identifier     = var.name
  engine         = "postgres"
  engine_version = var.engine_version
  instance_class = var.instance_class

  allocated_storage = 20
  storage_type      = "gp3"
  storage_encrypted = true

  db_name  = var.db_name
  username = var.username
  password = random_password.master.result
  port     = 5432

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.db.id]
  parameter_group_name   = aws_db_parameter_group.this.name
  publicly_accessible    = false
  multi_az               = false

  iam_database_authentication_enabled = true
  auto_minor_version_upgrade          = true
  backup_retention_period             = 1
  copy_tags_to_snapshot               = true
  deletion_protection                 = false # demo env: must be destroyable in one command
  skip_final_snapshot                 = true
  apply_immediately                   = true
  performance_insights_enabled        = false
  enabled_cloudwatch_logs_exports     = ["postgresql"]

  tags = var.tags
}

resource "aws_ssm_parameter" "database_url" {
  name        = "/${var.name}/database_url"
  description = "SQLAlchemy URL for patchloop services"
  type        = "SecureString"
  value       = "postgresql+psycopg://${var.username}:${random_password.master.result}@${aws_db_instance.this.address}:5432/${var.db_name}?sslmode=require"
  tags        = var.tags
}
