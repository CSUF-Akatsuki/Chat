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

# Allow the Lambda execution role to invoke Amazon Bedrock Nova Lite
# so the Chatbot Lambda can generate AI replies.
data "aws_iam_policy_document" "lambda_bedrock" {
  statement {
    sid     = "AllowBedrockInvokeModel"
    actions = ["bedrock:InvokeModel"]
    resources = [
      "arn:aws:bedrock:*::foundation-model/amazon.nova-lite-v1:0",
    ]
  }
}

resource "aws_iam_policy" "lambda_bedrock" {
  name   = "${var.project}-lambda-bedrock"
  policy = data.aws_iam_policy_document.lambda_bedrock.json
}

resource "aws_iam_role_policy_attachment" "lambda_bedrock" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.lambda_bedrock.arn
}

# ECS task role for the WebSocket server (ECS Fargate).
# Grants lambda:InvokeFunction on the Chatbot Lambda so the WebSocket server
# can fire-and-forget invoke it when a message is addressed to the bot.
#
# The ECS task definition is not managed in this Terraform workspace.
# Set task_role_arn = aws_iam_role.ecs_task.arn on the WebSocket task definition.
data "aws_iam_policy_document" "ecs_task_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ecs_task" {
  name               = "${var.project}-ecs-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume.json
}

data "aws_iam_policy_document" "ecs_task_invoke_chatbot" {
  statement {
    sid     = "AllowInvokeChatbotLambda"
    actions = ["lambda:InvokeFunction"]
    resources = [
      aws_lambda_function.chatbot.arn,
    ]
  }
}

resource "aws_iam_policy" "ecs_task_invoke_chatbot" {
  name   = "${var.project}-ecs-invoke-chatbot"
  policy = data.aws_iam_policy_document.ecs_task_invoke_chatbot.json
}

resource "aws_iam_role_policy_attachment" "ecs_task_invoke_chatbot" {
  role       = aws_iam_role.ecs_task.name
  policy_arn = aws_iam_policy.ecs_task_invoke_chatbot.arn
}
