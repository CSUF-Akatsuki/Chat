data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda_exec" {
  name               = "${var.project}-lambda-exec"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

data "aws_iam_policy_document" "lambda_secrets" {
  statement {
    actions = ["secretsmanager:GetSecretValue"]
    resources = [
      data.aws_secretsmanager_secret.db.arn,
      data.aws_secretsmanager_secret.redis.arn,
      data.aws_secretsmanager_secret.jwt.arn,
    ]
  }
}

resource "aws_iam_policy" "lambda_secrets" {
  name   = "${var.project}-lambda-secrets-read"
  policy = data.aws_iam_policy_document.lambda_secrets.json
}

resource "aws_iam_role_policy_attachment" "lambda_secrets" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.lambda_secrets.arn
}

# pycognito calls the user pool from the auth lambda. Server-side admin actions
# would need additional cognito-idp:* permissions; current code uses only
# unauthenticated client APIs (initiate auth / sign up / confirm), so no IAM
# is needed for those. Kept here as a placeholder for future admin actions.
data "aws_iam_policy_document" "lambda_cognito" {
  statement {
    actions = [
      "cognito-idp:AdminGetUser",
      "cognito-idp:AdminConfirmSignUp",
      "cognito-idp:AdminUpdateUserAttributes",
    ]
    resources = [aws_cognito_user_pool.main.arn]
  }
}

resource "aws_iam_policy" "lambda_cognito" {
  name   = "${var.project}-lambda-cognito"
  policy = data.aws_iam_policy_document.lambda_cognito.json
}

resource "aws_iam_role_policy_attachment" "lambda_cognito" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.lambda_cognito.arn
}
