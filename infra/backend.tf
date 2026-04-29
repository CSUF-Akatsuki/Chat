terraform {
  backend "s3" {
    bucket         = "room67chat-tfstate-311141566647"
    key            = "lambdas-cognito/terraform.tfstate"
    region         = "us-west-1"
    dynamodb_table = "room67chat-tfstate-locks"
    encrypt        = true
  }
}
