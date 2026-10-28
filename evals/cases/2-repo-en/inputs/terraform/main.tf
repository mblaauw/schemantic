resource "aws_db_instance" "bookings" { engine = "postgres" }
resource "aws_mq_broker" "events" { engine_type = "RabbitMQ" }
resource "aws_ecs_service" "api" { name = "api" }
resource "aws_ecs_service" "notifier" { name = "notifier" }
resource "aws_ecs_service" "sync" { name = "sync" }
resource "aws_s3_bucket" "web" { bucket = "bookings-web" }
resource "aws_cloudfront_distribution" "web" {}
# TODO: decide whether sync should move to the clinics' webhooks instead of polling
