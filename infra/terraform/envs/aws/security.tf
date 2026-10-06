# Security groups. No NAT, so tasks egress via public IPs; ingress is closed except the API port
# from allow-listed CIDRs. Egress is limited to HTTPS (AWS APIs, ECR, LLM API, git clone) and
# PostgreSQL inside the VPC.

resource "aws_security_group" "api" {
  name        = "${local.name}-api"
  description = "patchloop API tasks"
  vpc_id      = module.network.vpc_id
}

resource "aws_security_group" "workers" {
  name        = "${local.name}-workers"
  description = "patchloop worker tasks (no ingress)"
  vpc_id      = module.network.vpc_id
}

resource "aws_vpc_security_group_ingress_rule" "api_http" {
  for_each          = toset(var.api_allowed_cidrs)
  security_group_id = aws_security_group.api.id
  cidr_ipv4         = each.value
  ip_protocol       = "tcp"
  from_port         = 8000
  to_port           = 8000
  description       = "API from allow-listed client"
}

resource "aws_vpc_security_group_egress_rule" "https" {
  for_each          = { api = aws_security_group.api.id, workers = aws_security_group.workers.id }
  security_group_id = each.value
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  description       = "HTTPS to AWS APIs, ECR, LLM API, git hosts"
}

resource "aws_vpc_security_group_egress_rule" "postgres" {
  for_each                     = { api = aws_security_group.api.id, workers = aws_security_group.workers.id }
  security_group_id            = each.value
  referenced_security_group_id = module.database.security_group_id
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
  description                  = "PostgreSQL"
}

# DNS goes to the VPC resolver (.2 address), which needs explicit egress on UDP/TCP 53.
resource "aws_vpc_security_group_egress_rule" "dns" {
  for_each = {
    api_udp     = { sg = aws_security_group.api.id, proto = "udp" }
    api_tcp     = { sg = aws_security_group.api.id, proto = "tcp" }
    workers_udp = { sg = aws_security_group.workers.id, proto = "udp" }
    workers_tcp = { sg = aws_security_group.workers.id, proto = "tcp" }
  }
  security_group_id = each.value.sg
  cidr_ipv4         = module.network.vpc_cidr
  ip_protocol       = each.value.proto
  from_port         = 53
  to_port           = 53
  description       = "DNS to the VPC resolver"
}
