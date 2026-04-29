resource "aws_security_group" "lambda" {
  name        = "${var.project}-sg-lambda"
  description = "Lambda functions egress to RDS, ElastiCache, internet (NAT) for Cognito API"
  vpc_id      = data.aws_vpc.main.id

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project}-sg-lambda"
  }
}

resource "aws_security_group_rule" "rds_from_lambda" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = data.aws_security_group.rds.id
  source_security_group_id = aws_security_group.lambda.id
  description              = "PostgreSQL from Lambda functions"
}

resource "aws_security_group_rule" "redis_from_lambda" {
  type                     = "ingress"
  from_port                = 6379
  to_port                  = 6379
  protocol                 = "tcp"
  security_group_id        = data.aws_security_group.redis.id
  source_security_group_id = aws_security_group.lambda.id
  description              = "Redis from Lambda functions"
}
