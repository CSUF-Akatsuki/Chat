data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

data "aws_vpc" "main" {
  filter {
    name   = "tag:Name"
    values = ["Room67Chat-vpc"]
  }
}

data "aws_subnets" "private_app" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.main.id]
  }
  filter {
    name   = "tag:Name"
    values = ["Room67Chat-subnet-private-app-a", "Room67Chat-subnet-private-app-b"]
  }
}

data "aws_security_group" "rds" {
  vpc_id = data.aws_vpc.main.id
  filter {
    name   = "group-name"
    values = ["Room67Chat-sg-rds"]
  }
}

data "aws_security_group" "redis" {
  vpc_id = data.aws_vpc.main.id
  filter {
    name   = "group-name"
    values = ["Room67Chat-sg-redis"]
  }
}

data "aws_secretsmanager_secret" "db" {
  name = "room67chat/db"
}

data "aws_secretsmanager_secret_version" "db" {
  secret_id = data.aws_secretsmanager_secret.db.id
}

data "aws_secretsmanager_secret" "redis" {
  name = "room67chat/redis"
}

data "aws_secretsmanager_secret_version" "redis" {
  secret_id = data.aws_secretsmanager_secret.redis.id
}

data "aws_secretsmanager_secret" "jwt" {
  name = "room67chat/jwt"
}

data "aws_secretsmanager_secret_version" "jwt" {
  secret_id = data.aws_secretsmanager_secret.jwt.id
}

data "aws_elasticache_replication_group" "redis" {
  replication_group_id = "Room67Chat-redis"
}
