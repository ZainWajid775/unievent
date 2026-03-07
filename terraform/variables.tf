variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "unievent"
}

variable "s3_bucket_name" {
  description = "Globally unique S3 bucket name"
  type        = string
  default     = "unievent-media-bucket-giki-2025"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}

variable "key_pair_name" {
  description = "Name of an existing EC2 Key Pair for SSH access"
  type        = string
  default     = "unievent-key"
}

variable "ssh_allowed_cidr" {
  description = "CIDR block allowed to SSH into EC2 instances"
  type        = string
  default     = "0.0.0.0/0"   # Restrict this in production!
}

variable "ticketmaster_api_key" {
  description = "Ticketmaster Discovery API key"
  type        = string
  sensitive   = true
  default     = ""
}
